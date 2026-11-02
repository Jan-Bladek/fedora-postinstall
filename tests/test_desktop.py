import os
from pathlib import Path
import pty
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DesktopChoice(unittest.TestCase):
    def test_presets_and_conflicts_have_no_system_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            home = work/'home'
            home.mkdir()
            shim = work/'bin'
            shim.mkdir()
            for command in ('rpm', 'sudo', 'dnf5', 'curl', 'flatpak', 'systemctl'):
                executable = shim/command
                executable.write_text('#!/bin/sh\necho FORBIDDEN >&2; exit 99\n')
                executable.chmod(0o755)
            env = dict(os.environ, HOME=str(home), PATH=str(shim)+':'+os.environ['PATH'])
            for desktop in ('noctalia', 'dms', 'plasma'):
                result = subprocess.run(['bash', str(ROOT/'install.sh'), '--dry-run', '--desktop', desktop],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = result.stdout.splitlines()[0].split('modules: ')[1].split()
                self.assertNotIn('kde-removal', plan)
                if desktop == 'plasma':
                    self.assertTrue(set(plan).isdisjoint({'hyprland', 'noctalia', 'dms'}))
                else:
                    self.assertIn('hyprland', plan)
                    self.assertIn(desktop, plan)
                    self.assertNotIn('dms' if desktop == 'noctalia' else 'noctalia', plan)
                self.assertNotIn('FORBIDDEN', result.stdout+result.stderr)
            for desktop, modules in [('plasma', 'kde-removal'), ('plasma', 'hyprland'),
                                     ('plasma', 'dms'), ('dms', 'noctalia'),
                                     ('noctalia', 'dms'), ('invalid', 'terminal')]:
                result = subprocess.run(['bash', str(ROOT/'install.sh'), '--dry-run', '--desktop', desktop,
                                         '--modules', modules], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('FORBIDDEN', result.stdout+result.stderr)
            self.assertEqual(list(home.iterdir()), [])

    def test_dms_repo_rejects_an_unrelated_copr_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)/'dms.repo'
            for project, accepted in [('duxlabs/dms', True), ('duxlabs/dux-repo', True),
                                      ('someone/another-shell', False)]:
                repo.write_text('[dms]\ngpgcheck=1\nbaseurl=https://download.copr.fedorainfracloud.org/results/'+project+
                                '/fedora-44-x86_64/\ngpgkey=https://download.copr.fedorainfracloud.org/results/'+project+'/pubkey.gpg\n')
                result = subprocess.run(['python3', str(ROOT/'scripts/check-repo.py'), 'dms-copr', str(repo)],
                                        capture_output=True)
                self.assertEqual(result.returncode == 0, accepted)

    def test_shell_ipc_routes_only_to_selected_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            config = work/'config/fedora-postinstall'
            config.mkdir(parents=True)
            shim = work/'bin'
            shim.mkdir()
            for command in ('noctalia', 'dms', 'pgrep'):
                script = shim/command
                script.write_text('#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*"\n')
                script.chmod(0o755)
            env = dict(os.environ, XDG_CONFIG_HOME=str(work/'config'), PATH=str(shim)+':'+os.environ['PATH'])
            for shell, expected in [('noctalia', ['noctalia msg panel-toggle launcher',
                                                 'noctalia msg panel-toggle control-center',
                                                 'noctalia msg settings-toggle', 'noctalia msg status']),
                                    ('dms', ['dms ipc call spotlight toggle', 'dms ipc call control-center toggle',
                                             'dms ipc call settings toggle', 'dms ipc call lock isLocked'])]:
                (config/'shell').write_text(shell+'\n')
                for action, command in zip(('launcher', 'panel', 'settings', 'health'), expected):
                    result = subprocess.run([str(ROOT/'scripts/desktop-shell'), action], env=env,
                                            text=True, capture_output=True, check=True)
                    self.assertIn(command, result.stdout)
                    self.assertNotIn('noctalia' if shell == 'dms' else 'dms', result.stdout)
            (config/'shell').write_text('$(touch NEVER_EXECUTE)\n')
            result = subprocess.run([str(ROOT/'scripts/desktop-shell'), 'health'], env=env, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((ROOT/'NEVER_EXECUTE').exists())

    def test_tui_desktop_then_debloat_then_development_with_ide_checklist(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            shim = work/'bin'
            shim.mkdir()
            executable = shim/'whiptail'
            executable.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$MENU_LOG"
case " $* " in
 *" --radiolist "*" noctalia "*) echo plasma >&2 ;;
 *) exit 1 ;;
esac
''')
            executable.chmod(0o755)
            env = dict(os.environ, MENU_LOG=str(work/'menu'), PATH=str(shim)+':'+os.environ['PATH'])
            master, slave = pty.openpty()
            try:
                result = subprocess.run(['bash', str(ROOT/'install.sh')], stdin=slave,
                                        env=env, capture_output=True, text=True, timeout=10)
            finally:
                os.close(master)
                os.close(slave)
            self.assertEqual(result.returncode, 0, result.stderr)
            menus = (work/'menu').read_text().splitlines()
            self.assertEqual(len(menus), 3)
            self.assertIn('Fedora Post-Install', menus[0])
            self.assertIn('Debloat Plasma', menus[1])
            self.assertIn('Zestaw programistyczny', menus[2])
            self.assertIn('--checklist', menus[2])

    def test_lua_loads_generated_settings_only_for_dms(self):
        runner = """
local proxy = {}
setmetatable(proxy, { __index = function() return proxy end,
                     __call = function() return function() end end })
hl = proxy
package.path = os.getenv("XDG_CONFIG_HOME") .. "/hypr/?.lua;" .. package.path
dofile(arg[1])
"""
        for shell in ('noctalia', 'dms'):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                (work/'fedora-postinstall').mkdir()
                (work/'fedora-postinstall/shell').write_text(shell+'\n')
                settings = work/'hypr/dms'
                settings.mkdir(parents=True)
                for name in ('outputs', 'layout', 'colors', 'cursor', 'input', 'windowrules'):
                    (settings/(name+'.lua')).write_text('local f = assert(io.open(os.getenv("TRACE"), "a")); f:write("'+name+'\\n"); f:close()\n')
                trace = work/'loaded'
                env = dict(os.environ, XDG_CONFIG_HOME=str(work), TRACE=str(trace))
                result = subprocess.run(['lua', '-', str(ROOT/'config/hyprland/hyprland.lua')], input=runner,
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                if shell == 'dms':
                    self.assertEqual(set(trace.read_text().splitlines()), {'outputs', 'layout', 'colors', 'cursor', 'input', 'windowrules'})
                else:
                    self.assertFalse(trace.exists())

    def test_only_unmodified_legacy_config_migrates(self):
        script = r'''
source "$1/lib/core.sh"
source "$1/modules/hyprland.sh"
ROOT=$1
RUN=$2/run
CONFIG=$2/config
mkdir -p "$RUN" "$CONFIG/hypr"
cp "$ROOT/config/hyprland/legacy-v0.2.lua" "$CONFIG/hypr/hyprland.lua"
if [[ $3 == custom ]]; then echo '-- user change' >> "$CONFIG/hypr/hyprland.lua"; fi
before=$(sha256sum "$CONFIG/hypr/hyprland.lua")
systemd-detect-virt() { return "$VIRT_STATUS"; }
if [[ $VIRT_STATUS == 0 ]]; then
    printf '\n-- Hyprland 0.57.0 VM compatibility: retain EGL alpha formats for VirGL clients.\nhl.config({ quirks = { skip_non_kms_dmabuf_formats = false } })\n' >> "$CONFIG/hypr/hyprland.lua"
    before=$(sha256sum "$CONFIG/hypr/hyprland.lua")
fi
prepare_hyprland_config 0.57.0
write_hyprland_config
if [[ $3 == custom ]]; then
    [[ $(sha256sum "$CONFIG/hypr/hyprland.lua") == "$before" ]]
    cmp "$RUN/hyprland.lua" "$CONFIG/hypr/hyprland.lua.fedora-postinstall-new"
else
    cmp "$RUN/hyprland.lua" "$CONFIG/hypr/hyprland.lua"
    test -s "$RUN/hyprland-before-shell-selector.lua"
fi
'''
        for kind in ('legacy', 'custom'):
            for virtual in ('0', '1'):
                with self.subTest(kind=kind, virtual=virtual), tempfile.TemporaryDirectory() as temp:
                    subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp, kind],
                                   env=dict(os.environ, VIRT_STATUS=virtual), text=True, capture_output=True, check=True)
