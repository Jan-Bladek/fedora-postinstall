import fcntl
import json
import os
from pathlib import Path
import pty
import runpy
import select
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Experience(unittest.TestCase):
    def test_cleanup_preserves_session_kernel_and_unselected_apps(self):
        planner = runpy.run_path(str(ROOT/'scripts/cleanup-plan.py'))['plan']
        installed = {'firefox', 'firefox-langpacks', 'kmail', 'kmail-libs', 'uwsm', 'kernel',
                     'plasma-workspace', 'plasma-desktop', 'polkit-kde', 'dolphin', 'okular',
                     'qt6-qtbase', 'NetworkManager', 'libreoffice-writer', 'libreoffice-core'}
        result = planner(['all'], installed)
        self.assertEqual(set(result['remove']), {'firefox', 'firefox-langpacks', 'kmail', 'kmail-libs',
                                                'libreoffice-writer', 'libreoffice-core'})
        self.assertTrue(result['hide_uuctl'])
        self.assertEqual(planner(['firefox'], installed)['remove'], ['firefox', 'firefox-langpacks'])
        with self.assertRaises(ValueError):
            planner(['kernel'], installed)

    def test_failed_cleanup_dependency_check_never_erases_or_stops_services(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            shim = work/'bin'
            shim.mkdir()
            rpm = shim/'rpm'
            rpm.write_text('#!/bin/sh\necho firefox\necho kernel\n')
            rpm.chmod(0o755)
            script = r'''
source "$1/lib/core.sh"
source "$1/modules/cleanup.sh"
ROOT=$1
RUN=$2
CONFIG=$2/config
CLEANUP_APPS=firefox
run() {
    if [[ $* == 'sudo rpm -e --test firefox' ]]; then return 45; fi
    echo FORBIDDEN_MUTATION; return 99
}
packages() { echo FORBIDDEN_MUTATION; return 99; }
module_cleanup
'''
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp],
                                    env=dict(os.environ, PATH=str(shim)+':'+os.environ['PATH']),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 45, result.stderr)
            self.assertNotIn('FORBIDDEN_MUTATION', result.stdout+result.stderr)

    def test_jsonc_merge_keeps_urls_strings_and_unrelated_settings(self):
        parser = runpy.run_path(str(ROOT/'scripts/merge-json.py'))['read_jsonc']
        value = parser('''{ // comment
          "url": "https://example.com/path//part", "text": ",}] /* literal */",
          "nested": {"keep": true,}, /* comment */ "values": [1,2,],
        }''')
        self.assertEqual(value['url'], 'https://example.com/path//part')
        self.assertEqual(value['text'], ',}] /* literal */')
        self.assertEqual(value['nested'], {'keep': True})
        self.assertEqual(value['values'], [1, 2])

    def test_kitty_merge_is_idempotent_and_retains_user_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)/'kitty.conf'
            result = Path(temp)/'result'
            config.write_text('# custom\nscrollback_lines 9000\nfont_family old-font\n')
            for _ in range(2):
                subprocess.run(['python3', str(ROOT/'scripts/merge-config-block.py'), str(config),
                                str(ROOT/'config/kitty/managed.conf'), str(result), 'KITTY'], check=True)
                config.write_text(result.read_text())
            self.assertIn('scrollback_lines 9000', config.read_text())
            self.assertEqual(config.read_text().count('# BEGIN FEDORA-POSTINSTALL KITTY'), 1)
            self.assertIn('confirm_os_window_close 0', config.read_text())
            self.assertIn('background_opacity 0.90', config.read_text())

    def test_jetbrains_launcher_repair_matches_app_id_and_keeps_user_changes(self):
        ns = runpy.run_path(str(ROOT/'scripts/vendor-apps.py'))
        repair = ns['register_launcher']
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            repair.__globals__.update(BASE=work/'apps', BIN=work/'bin', DESKTOP=work/'applications')
            app = work/'apps/rustrover'
            payload = app/'test/bin'
            payload.mkdir(parents=True)
            (payload/'rustrover.sh').write_text('#!/bin/sh\n')
            (payload/'rustrover.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            (app/'current').symlink_to('test')
            desktop = work/'applications'
            desktop.mkdir()
            legacy = desktop/'fedora-postinstall-rustrover.desktop'
            link = work/'bin/rustrover'
            legacy.write_text(f'[Desktop Entry]\nType=Application\nName=rustrover\nExec="{link}" %U\nTerminal=false\nCategories=Development;\n')
            repair('rustrover', 'bin/rustrover.sh')
            current = desktop/'jetbrains-rustrover.desktop'
            self.assertIn('StartupWMClass=jetbrains-rustrover', current.read_text())
            self.assertIn(str(app/'current/bin/rustrover.svg'), current.read_text())
            self.assertFalse(legacy.exists())
            repair('rustrover', 'bin/rustrover.sh')
            current.write_text(current.read_text().replace('Name=JetBrains RustRover', 'Name=My custom IDE'))
            repair('rustrover', 'bin/rustrover.sh')
            self.assertIn('Name=My custom IDE', current.read_text())
            self.assertTrue(current.with_name(current.name+'.fedora-postinstall-new').exists())

    def test_requested_hypr_preset_keeps_a_copy_of_custom_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            script = r''' 
source "$1/lib/core.sh"
source "$1/modules/hyprland.sh"
ROOT=$1
RUN=$2/run
CONFIG=$2/config
mkdir -p "$RUN" "$CONFIG/hypr"
printf '%s\n' '-- personal config' > "$CONFIG/hypr/hyprland.lua"
cp "$ROOT/config/hyprland/hyprland.lua" "$RUN/hyprland.lua"
APPLY_HYPR_PRESET=1
write_hyprland_config
cmp "$RUN/hyprland.lua" "$CONFIG/hypr/hyprland.lua"
grep -Fxq -- '-- personal config' "$RUN/hyprland-before-requested-preset.lua"
'''
            subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp],
                           check=True, capture_output=True, text=True)

    def test_one_consent_adds_dnf_yes_without_bypassing_destructive_confirmation(self):
        script = r'''
source "$1/lib/core.sh"
INSTALL_APPROVED=1
sudo() { printf 'EXEC %s\n' "$*"; }
run sudo dnf5 install kitty
if confirm 'Remove Plasma?' </dev/null; then exit 99; fi
consent 'Enable selected vendor repo?' </dev/null
'''
        result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('EXEC dnf5 --assumeyes install kitty', result.stdout)

    def run_terminal(self, command, keys=b''):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, __import__('struct').pack('HHHH', 32, 100, 0, 0))
        def prepare():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, preexec_fn=prepare,
                                env=dict(os.environ, TERM='xterm-256color'))
        os.close(slave)
        output = bytearray()
        sent = False
        deadline = time.monotonic()+12
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError:
                        break
                if not sent and b'FEDORA POST-INSTALL' in output:
                    os.write(master, keys)
                    sent = True
                if proc.poll() is not None:
                    break
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            return proc.returncode, output.decode(errors='replace')
        finally:
            os.close(master)

    def test_curses_desktop_selector_in_a_real_pty(self):
        status, output = self.run_terminal(['python3', str(ROOT/'scripts/tui.py'), '--title', 'Desktop',
                                            '--radiolist', 'Choose', '20', '80', '3',
                                            'noctalia', 'Noctalia', 'ON', 'dms', 'DMS', 'OFF',
                                            'plasma', 'Plasma', 'OFF'], b'j\n')
        self.assertEqual(status, 0, output)
        self.assertIn('dms', output)

    def test_progress_view_closes_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            script = r'''
source "$1/lib/ui.sh"
ROOT=$1
RUN=$2
USE_PROGRESS=1
DESKTOP=dms
whiptail() { python3 "$ROOT/scripts/tui.py" "$@"; }
ui_start
ui_status 'Test instalacji Kitty'
sleep 1
ui_finish 42
'''
            status, output = self.run_terminal(['bash', '-eu', '-c', script, 'test', str(ROOT), temp])
            self.assertEqual(status, 0, output)
            self.assertIn('kod 42', output)
