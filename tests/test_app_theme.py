import configparser
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ThemeSetup = runpy.run_path(str(ROOT / 'scripts/dms-app-theme.py'))['ThemeSetup']
merge = runpy.run_path(str(ROOT / 'scripts/dms-theme-includes.py'))['merge']


class AppTheme(unittest.TestCase):
    def test_module_does_not_change_other_desktops(self):
        code = '''source "$1/modules/app-theme.sh"
DESKTOP=$2
packages() { exit 99; }
run() { exit 98; }
module_app_theme
'''
        for desktop in ('plasma', 'noctalia'):
            subprocess.run(['bash', '-eu', '-c', code, 'test', str(ROOT), desktop], check=True)

    def test_preparation_keeps_preferences_backups_and_existing_palettes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            config, backup, data, shell = [base / name for name in ('config', 'backup', 'data', 'shell')]
            (config / 'dms').mkdir(parents=True)
            settings = '// my source color\n{"currentThemeName":"custom", "runUserMatugenTemplates":false}'
            (config / 'dms/settings.json').write_text(settings)
            (config / 'gtk-3.0').mkdir()
            (config / 'gtk-3.0/settings.ini').write_text('[Settings]\ngtk-font-name=Personal 12\n')
            (config / 'btop').mkdir()
            (config / 'btop/btop.conf').write_text('update_ms = 1500\ncolor_theme="custom"\n')
            (shell / 'scripts').mkdir(parents=True)
            (shell / 'scripts/gtk.sh').write_text('# fixture')
            state = base / 'state/dms'
            state.mkdir(parents=True)
            (state / 'session.json').write_text('{"isLightMode":true}')
            setup = ThemeSetup(config, backup, data, shell)
            calls = []

            def run(*args, **kwargs):
                calls.append(args)
                if args[0] == 'dms':
                    self.assertIn('--run-user-templates=false', args)
                    self.assertEqual(args[args.index('--mode') + 1], 'light')
                    output = Path(args[args.index('--config-dir') + 1])
                    for name in ('gtk-3.0', 'gtk-4.0'):
                        (output / name).mkdir(exist_ok=True)
                        (output / name / 'dank-colors.css').write_text('/* palette */')

            with patch.dict(os.environ, XDG_STATE_HOME=str(base / 'state')), patch.object(setup, 'run', side_effect=run):
                setup.prepare()
                setup.prepare()
                self.assertEqual(sum(call[0] == 'dms' for call in calls), 1)
                (config / 'gtk-3.0/dank-colors.css').write_text('/* personal palette */')
                (config / 'gtk-4.0/dank-colors.css').unlink()
                setup.prepare()
                self.assertEqual((config / 'gtk-3.0/dank-colors.css').read_text(), '/* personal palette */')
            self.assertEqual((backup / 'dms-app-theme/dms/settings.json').read_text(), settings)
            values = json.loads((config / 'dms/settings.json').read_text())
            self.assertEqual(values['currentThemeName'], 'custom')
            self.assertFalse(values['runUserMatugenTemplates'])
            self.assertTrue(values['matugenTemplateGtk'])
            self.assertTrue(values['matugenTemplateNeovim'])
            ini = configparser.ConfigParser()
            ini.read(config / 'gtk-3.0/settings.ini')
            self.assertEqual(ini['Settings']['gtk-font-name'], 'Personal 12')
            self.assertEqual(ini['Settings']['gtk-theme-name'], 'adw-gtk3')
            self.assertIn('update_ms = 1500', (config / 'btop/btop.conf').read_text())
            self.assertEqual((config / 'btop/btop.conf').read_text().count('color_theme'), 1)
            self.assertTrue(all(call[-1] == 'true' for call in calls if call[0] == 'bash'))

    def test_vscode_uses_packaged_extension_and_preserves_jsonc_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            config, backup, data, shell = [base / name for name in ('config', 'backup', 'data', 'shell')]
            (config / 'Code/User').mkdir(parents=True)
            original = '// my editor\n{"editor.fontSize":18,"workbench.colorTheme":"old"}'
            (config / 'Code/User/settings.json').write_text(original)
            (shell / 'matugen').mkdir(parents=True)
            labels = ['Dynamic Base16 DankShell', 'Dynamic Base16 DankShell (Dark)', 'Dynamic Base16 DankShell (Light)']
            vsix = shell / 'matugen/dms-theme.vsix'
            with zipfile.ZipFile(vsix, 'w') as archive:
                archive.writestr('extension/package.json', json.dumps({
                    'name': 'dms-theme', 'contributes': {'themes': [{'label': label} for label in labels]}}))
            setup = ThemeSetup(config, backup, data, shell)
            with patch('shutil.which', return_value='/usr/bin/code'), patch.object(setup, 'run') as run:
                setup.vscode()
            run.assert_called_once_with('code', '--install-extension', vsix, '--force')
            result = json.loads((config / 'Code/User/settings.json').read_text())
            self.assertEqual(result['editor.fontSize'], 18)
            self.assertEqual(result['workbench.colorTheme'], labels[0])
            self.assertEqual((backup / 'dms-app-theme/Code/User/settings.json').read_text(), original)

    def test_qt_environment_is_dms_only_and_merge_keeps_custom_lua(self):
        original = '-- personal config\npersonal = 42\n'
        result = merge(original)
        self.assertTrue(result.startswith(original))
        self.assertEqual(merge(result), result)
        for selected in ('dms', 'noctalia', 'plasma'):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                (base / 'fedora-postinstall').mkdir()
                (base / 'fedora-postinstall/shell').write_text(selected)
                script = base / 'main.lua'
                script.write_text(result)
                code = '''local count=0
hl={env=function(name,value) assert(value=="gtk3"); count=count+1 end}
dofile(arg[1])
assert(personal==42)
assert(count==tonumber(arg[2]))
'''
                subprocess.run(['lua', '-', str(script), '2' if selected == 'dms' else '0'],
                               input=code, text=True, check=True,
                               env=dict(os.environ, XDG_CONFIG_HOME=str(base)))
        with self.assertRaises(ValueError):
            merge('-- END FEDORA-POSTINSTALL DMS-APP-THEME\n')

    def test_lazyvim_spec_is_inactive_outside_dms_and_has_first_start_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)
            (config / 'fedora-postinstall').mkdir()
            code = '''vim={env={XDG_CONFIG_HOME=arg[2], HOME=arg[2]}}
local spec=dofile(arg[1]); assert(#spec==tonumber(arg[3]))
if #spec>0 then
 local selected
 vim.fn={filereadable=function() return 0 end}
 vim.cmd={colorscheme=function(name) selected=name end}
 spec[2].opts.colorscheme(); assert(selected=="habamax")
 vim.fn.filereadable=function() return 1 end
 spec[2].opts.colorscheme(); assert(selected=="dms")
end
'''
            for selected in ('dms', 'noctalia'):
                (config / 'fedora-postinstall/shell').write_text(selected)
                subprocess.run(['lua', '-', str(ROOT / 'config/nvim/dms-theme.lua'), str(config),
                                '2' if selected == 'dms' else '0'], input=code, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
