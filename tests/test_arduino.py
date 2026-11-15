import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ArduinoIntegration(unittest.TestCase):
    def fixture(self, temp):
        root = Path(temp)
        ns = runpy.run_path(str(ROOT / 'scripts/vendor-apps.py'))
        register = ns['register_launcher']
        register.__globals__.update(BASE=root/'apps', BIN=root/'bin', DESKTOP=root/'applications')
        app = root/'apps/arduino-ide'
        (app/'version').mkdir(parents=True)
        payload = app/'version/arduino-ide'
        payload.write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        payload.chmod(0o755)
        (app/'current').symlink_to('version')
        with patch.object(shutil, 'which', return_value=None):
            register('arduino-ide', 'arduino-ide')
        return root, app, payload, register

    def test_wayland_wrapper_preserves_binary_and_argument_boundaries(self):
        with tempfile.TemporaryDirectory(prefix='arduino test ') as temp:
            root, app, payload, register = self.fixture(temp)
            # Migrate the direct AppImage link used by earlier installations.
            (root/'bin/arduino-ide').unlink()
            (root/'bin/arduino-ide').symlink_to(app/'current/arduino-ide')
            with patch.object(shutil, 'which', return_value=None):
                register('arduino-ide', 'arduino-ide')
            binary = payload.read_bytes()
            result = subprocess.run([str(root/'bin/arduino-ide'), '/tmp/my sketch.ino'],
                                    env=dict(os.environ, WAYLAND_DISPLAY='fixture', FEDORA_ARDUINO_PLATFORM='auto'),
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), ['--ozone-platform=wayland', '/tmp/my sketch.ino'])
            self.assertEqual(payload.read_bytes(), binary)
            self.assertEqual((root/'bin/arduino-ide').readlink(), app/'launcher')
            self.assertNotIn('--no-sandbox', (app/'launcher').read_text())
            self.assertNotIn('force-device-scale-factor', (app/'launcher').read_text())

    def test_x11_session_override_and_explicit_backend_are_respected(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _, _, _ = self.fixture(temp)
            for display, platform, args, expected in [
                ('', 'auto', [], []),
                ('fixture', 'x11', [], ['--ozone-platform=x11']),
                ('fixture', 'auto', ['--ozone-platform=x11'], ['--ozone-platform=x11']),
                ('fixture', 'auto', ['--ozone-platform', 'x11'], ['--ozone-platform', 'x11']),
            ]:
                result = subprocess.run([str(root/'bin/arduino-ide'), *args],
                                        env=dict(os.environ, WAYLAND_DISPLAY=display, FEDORA_ARDUINO_PLATFORM=platform),
                                        capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_custom_wrapper_and_custom_desktop_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root, app, _, register = self.fixture(temp)
            desktop = root/'applications/fedora-postinstall-arduino-ide.desktop'
            desktop.write_text(desktop.read_text().replace('Name=Arduino IDE', 'Name=My Arduino'))
            with patch.object(shutil, 'which', return_value=None):
                register('arduino-ide', 'arduino-ide')
            self.assertIn('Name=My Arduino', desktop.read_text())
            self.assertTrue(desktop.with_name(desktop.name+'.fedora-postinstall-new').is_file())
            (app/'launcher').write_text('#!/bin/sh\necho custom\n')
            with self.assertRaisesRegex(ValueError, 'Custom Arduino launcher'):
                register('arduino-ide', 'arduino-ide')
            self.assertIn('echo custom', (app/'launcher').read_text())

    @unittest.skipIf(os.geteuid() == 0, 'vendor CLI intentionally rejects root')
    def test_repair_includes_existing_arduino_without_a_download(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp)/'.local/share/fedora-postinstall/apps/arduino-ide'
            (app/'version').mkdir(parents=True)
            (app/'version/arduino-ide').write_text('fixture')
            (app/'current').symlink_to('version')
            with patch.dict(os.environ, HOME=temp), patch.object(sys, 'argv', ['vendor-apps.py', 'repair']), \
                    patch('urllib.request.urlopen', side_effect=AssertionError('repair must not download')), \
                    patch.object(shutil, 'which', return_value=None):
                runpy.run_path(str(ROOT/'scripts/vendor-apps.py'), run_name='__main__')
            self.assertTrue((app/'launcher').is_file())
            self.assertEqual((Path(temp)/'.local/bin/arduino-ide').readlink(), app/'launcher')

    def usb_script(self):
        return r'''
set -Eeuo pipefail
ROOT=$1
RUN=$HOME/run
mkdir -p "$RUN"
source "$ROOT/lib/core.sh"
source "$ROOT/modules/arduino-usb.sh"
packages() { printf 'packages %s\n' "$*" >> "$RUN/commands"; }
getent() { [[ ${NO_DIALOUT:-0} != 1 ]]; }
id() {
 if [[ $1 == -un ]]; then echo fixture-user
 elif [[ -f $RUN/member ]]; then echo 'users dialout'
 else echo users; fi
}
udevadm() { [[ $1 == verify ]]; printf 'verify\n' >> "$RUN/commands"; }
sudo() {
 printf 'sudo %s\n' "$*" >> "$RUN/commands"
 case $1 in
  install) [[ $* == *'/etc/udev/rules.d/60-fedora-postinstall-arduino.rules' ]] ;;
  udevadm) [[ $* == 'udevadm control --reload-rules' ]] ;;
  usermod) [[ $* == 'usermod -aG dialout fixture-user' ]]; touch "$RUN/member" ;;
  cat) /usr/bin/cat "$2" ;;
  *) return 99 ;;
 esac
}
module_arduino_usb
module_arduino_usb
'''

    def test_usb_access_adds_serial_group_once_and_scoped_rules_before_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(['bash', '-c', self.usb_script(), 'test', str(ROOT)],
                                    env=dict(os.environ, HOME=temp), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            commands = (Path(temp)/'run/commands').read_text()
            self.assertEqual(commands.count('sudo usermod -aG dialout fixture-user'), 1)
            self.assertLess(commands.index('verify'), commands.index('sudo install'))
            self.assertLess(commands.index('sudo install'), commands.index('sudo udevadm control --reload-rules'))
            rules = (ROOT/'config/udev/60-fedora-postinstall-arduino.rules').read_text()
            self.assertNotIn('0666', rules)
            self.assertIn('ttyACM[0-9]*|ttyUSB[0-9]*', rules)
            self.assertIn('ATTR{idVendor}=="2341|2a03"', rules)

    def test_missing_dialout_group_aborts_without_changing_system_devices(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(['bash', '-c', self.usb_script(), 'test', str(ROOT)],
                                    env=dict(os.environ, HOME=temp, NO_DIALOUT='1'), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('sudo ', (Path(temp)/'run/commands').read_text())

    @unittest.skipUnless(shutil.which('lua') or shutil.which('lua5.4'), 'Lua required')
    def test_file_manager_bind_keeps_super_f_fullscreen(self):
        code = '''
local binds={['SUPER+F']='fullscreen'}
local function normalize(key) return key:gsub(' ','') end
hl={unbind=function(key) binds[normalize(key)]=nil end,
 bind=function(key,cmd) binds[normalize(key)]=cmd end,
 dsp={exec_cmd=function(cmd) return cmd end}}
dofile(arg[1])
assert(binds['SUPER+F']=='fullscreen')
assert(binds['SUPER+CTRL+F']=='xdg-open "$HOME"')
assert(binds['SUPER+SHIFT+F']=='xdg-open "$HOME"')
'''
        result = subprocess.run([shutil.which('lua') or shutil.which('lua5.4'), '-',
                                 str(ROOT/'config/hyprland/flea.lua')], input=code, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
