#!/usr/bin/env python3
"""Configure installed DMS templates and applications without changing Plasma env."""
import argparse
import configparser
from io import StringIO
import json
import os
from pathlib import Path
import runpy
import re
import shutil
import subprocess
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
read_jsonc = runpy.run_path(str(REPO / 'scripts/merge-json.py'))['read_jsonc']


def shell_directory():
    result = subprocess.run(['rpm', '-ql', 'dms'], text=True, capture_output=True, check=True)
    for line in result.stdout.splitlines():
        path = Path(line)
        if path.name == 'base.toml' and path.parent.name == 'configs' and path.parent.parent.name == 'matugen':
            return path.parent.parent.parent
    raise RuntimeError('Installed DMS RPM does not contain matugen/configs/base.toml')


class ThemeSetup:
    def __init__(self, config, backup, data, shell=None):
        self.config, self.backup, self.data = map(Path, (config, backup, data))
        self.shell = Path(shell) if shell is not None else None
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.data))
        bus = Path(os.environ.get('XDG_RUNTIME_DIR') or f'/run/user/{os.getuid()}') / 'bus'
        if bus.is_socket():
            self.env.setdefault('DBUS_SESSION_BUS_ADDRESS', f'unix:path={bus}')

    def save(self, path):
        path = Path(path)
        if not path.exists() and not path.is_symlink():
            return
        relative = path.relative_to(self.config)
        target = self.backup / 'dms-app-theme' / relative
        if target.exists() or target.is_symlink():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            target.symlink_to(os.readlink(path))
        elif path.is_dir():
            shutil.copytree(path, target, symlinks=True)
        else:
            shutil.copy2(path, target)

    def write(self, path, text):
        path = Path(path)
        if path.exists() and path.read_text() == text:
            return
        self.save(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.dms-theme-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as output:
                output.write(text)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def merge_json(self, path, patch):
        value = read_jsonc(path.read_text()) if path.exists() else {}
        value.update(patch)
        self.write(path, json.dumps(value, indent=2, ensure_ascii=False) + '\n')

    def run(self, *args, allowed=(0,), env=None, capture_output=False):
        result = subprocess.run(list(map(str, args)), env=dict(self.env, **(env or {})), timeout=120,
                                text=True, capture_output=capture_output)
        if result.returncode not in allowed:
            raise RuntimeError(f'Theme command failed ({result.returncode}): {args[0]}')
        return result

    def installed_shell(self):
        if self.shell is None:
            self.shell = shell_directory()
        return self.shell

    def light_mode(self):
        state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'dms/session.json'
        return read_jsonc(state.read_text()).get('isLightMode', False) if state.exists() else False

    def gtk_settings(self, name, light):
        path = self.config / name / 'settings.ini'
        settings = configparser.ConfigParser(interpolation=None)
        settings.optionxform = str
        if path.exists():
            settings.read_string(path.read_text())
        if not settings.has_section('Settings'):
            settings.add_section('Settings')
        settings['Settings']['gtk-theme-name'] = 'adw-gtk3' if light else 'adw-gtk3-dark'
        # Select light/dark through the theme name; a lingering KDE preference
        # for dark variants would otherwise keep GTK dark in DMS light mode.
        settings['Settings']['gtk-application-prefer-dark-theme'] = 'false'
        output = StringIO()
        settings.write(output)
        self.write(path, output.getvalue())

    def activate_gtk_theme(self, light):
        schema, key = 'org.gnome.desktop.interface', 'gtk-theme'
        previous = self.backup / 'dms-app-theme/gsettings-gtk-theme.txt'
        if not previous.exists():
            value = self.run('gsettings', 'get', schema, key, capture_output=True).stdout
            previous.parent.mkdir(parents=True, exist_ok=True)
            previous.write_text(value)
        self.run('gsettings', 'set', schema, key, 'adw-gtk3' if light else 'adw-gtk3-dark')

    def prepare(self):
        shell = self.installed_shell()
        script = shell / 'scripts/gtk.sh'
        if not script.is_file():
            raise RuntimeError(f'DMS GTK integration script missing: {script}')
        self.merge_json(self.config / 'dms/settings.json', {
            'runDmsMatugenTemplates': True, 'generateThemeAtStartup': True,
            'syncModeWithPortal': True,
            'matugenTemplateGtk': True, 'matugenTemplateHyprland': True,
            'matugenTemplateKitty': True, 'matugenTemplateNeovim': True,
            'matugenTemplateVscode': True,
        })
        # DMS generates and refreshes these on future wallpaper/theme changes.
        # Bootstrap only missing GTK palettes; never replace an existing palette
        # with the installer's initial fallback color.
        light = self.light_mode()
        for name in ('gtk-3.0', 'gtk-4.0'):
            self.save(self.config / name)
        missing = [name for name in ('gtk-3.0', 'gtk-4.0')
                   if not (self.config / name / 'dank-colors.css').is_file()]
        if missing:
            bootstrap = self.backup / 'dms-initial-palette/config'
            bootstrap.mkdir(parents=True, exist_ok=True)
            self.run('dms', 'matugen', 'generate', '--shell-dir', shell,
                     '--config-dir', bootstrap, '--state-dir', self.backup / 'dms-initial-palette/state',
                     '--kind', 'hex', '--value', '#6750a4', '--mode', 'light' if light else 'dark',
                     '--run-user-templates=false',
                     '--skip-templates', 'niri,hyprland,mangowc,qt5ct,qt6ct,qtengine,fcitx5,firefox,pywalfox,zenbrowser,vesktop,vencord,equibop,ghostty,kitty,foot,alacritty,wezterm,nvim,dgop,kcolorscheme,vscode,emacs,zed',
                     # DMS resolves template output paths through XDG_CONFIG_HOME;
                     # --config-dir alone only selects its input configuration.
                     env={'XDG_CONFIG_HOME': str(bootstrap)}, allowed=(0, 2))
            for name in missing:
                self.write(self.config / name / 'dank-colors.css', (bootstrap / name / 'dank-colors.css').read_text())
        # This is the installed upstream's Apply GTK colors implementation.
        self.run('bash', script, self.config, 'apply', 'true' if light else 'false')
        self.run('bash', script, self.config, 'patch', 'true' if light else 'false', allowed=(0, 2, 3))
        for name in ('gtk-3.0', 'gtk-4.0'):
            self.gtk_settings(name, light)
        # DMS refreshes only a theme it owns. Mirror its explicit Apply action
        # so an existing Breeze setting does not block subsequent mode changes.
        self.activate_gtk_theme(light)
        btop = self.config / 'btop/btop.conf'
        original = btop.read_text() if btop.exists() else ''
        lines = [line for line in original.splitlines() if not re.match(r'^\s*color_theme\s*=', line)]
        self.write(btop, '\n'.join(lines + ['color_theme = "TTY"']) + '\n')

    def vscode(self):
        if shutil.which('code') is None:
            return
        vsix = self.installed_shell() / 'matugen/dms-theme.vsix'
        with zipfile.ZipFile(vsix) as archive:
            manifest = json.loads(archive.read('extension/package.json'))
        if manifest.get('name') != 'dms-theme':
            raise RuntimeError('Unexpected theme extension in installed DMS RPM')
        themes = manifest['contributes']['themes']
        labels = {theme['label'] for theme in themes}
        default = 'Dynamic Base16 DankShell'
        if default not in labels:
            raise RuntimeError('Installed DMS extension has no Dynamic Base16 DankShell theme')
        self.run('code', '--install-extension', vsix, '--force')
        patch = {'workbench.colorTheme': default}
        if {default + ' (Dark)', default + ' (Light)'} <= labels:
            patch.update({'window.autoDetectColorScheme': True,
                          'workbench.preferredDarkColorTheme': default + ' (Dark)',
                          'workbench.preferredLightColorTheme': default + ' (Light)'})
        self.merge_json(self.config / 'Code/User/settings.json', patch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'vscode'))
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    args = parser.parse_args()
    setup = ThemeSetup(args.config, args.backup, args.data)
    getattr(setup, args.action)()


if __name__ == '__main__':
    main()
