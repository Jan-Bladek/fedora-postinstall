import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LAPTOP = runpy.run_path(str(ROOT / 'scripts/fedora-laptop'))


class LaptopKeys(unittest.TestCase):
    def test_volume_microphone_and_brightness_target_the_right_devices(self):
        expected = {
            'volume-up': ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '5%+'],
            'volume-down': ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '5%-'],
            'mute': ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'],
            'mic-mute': ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@', 'toggle'],
            'brightness-up': ['brightnessctl', '--class=backlight', '--min-value=1', 'set', '+5%'],
            'brightness-down': ['brightnessctl', '--class=backlight', '--min-value=1', 'set', '5%-'],
        }
        with patch.object(subprocess, 'run') as command:
            for action, args in expected.items():
                LAPTOP['dispatch'](action)
                self.assertEqual(command.call_args.args[0], args)
                self.assertTrue(command.call_args.kwargs['check'])

    def test_airplane_has_one_state_even_when_wifi_and_bluetooth_differ(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp):
            for states, operation in [(['unblocked', 'blocked'], 'block'), (['blocked', 'blocked'], 'unblock')]:
                result = subprocess.CompletedProcess([], 0, json.dumps({'rfkilldevices': [
                    {'soft': state, 'hard': 'unblocked'} for state in states]}), '')
                with patch.object(subprocess, 'run', side_effect=[result, subprocess.CompletedProcess([], 0)]) as command:
                    LAPTOP['dispatch']('airplane')
                self.assertEqual(command.call_args.args[0], ['rfkill', operation, 'all'])

    def test_invalid_radio_inventory_does_not_change_radios(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp):
            for devices in ([], [{'soft': 'unexpected'}]):
                result = subprocess.CompletedProcess([], 0, json.dumps({'rfkilldevices': devices}), '')
                with patch.object(subprocess, 'run', return_value=result) as command:
                    with self.assertRaises(RuntimeError):
                        LAPTOP['dispatch']('airplane')
                self.assertEqual(command.call_count, 1)

    def test_calculator_is_launched_without_a_shell(self):
        with patch.object(shutil, 'which', side_effect=lambda name: '/bin/kcalc' if name == 'kcalc' else None), \
                patch.object(subprocess, 'Popen') as command:
            LAPTOP['dispatch']('calculator')
        self.assertEqual(command.call_args.args[0], ['/bin/kcalc'])
        self.assertFalse(command.call_args.kwargs.get('shell', False))

    def test_lock_routes_to_the_selected_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'fedora-postinstall').mkdir()
            binary = root / 'bin'
            binary.mkdir()
            for tool in ('dms', 'noctalia'):
                path = binary / tool
                path.write_text('#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*"\n')
                path.chmod(0o755)
            for selected, expected in [('dms', 'dms ipc call lock lock'), ('noctalia', 'noctalia msg session lock')]:
                (root / 'fedora-postinstall/shell').write_text(selected + '\n')
                result = subprocess.run(['bash', str(ROOT / 'scripts/desktop-shell'), 'lock'],
                                        env=dict(os.environ, XDG_CONFIG_HOME=temp,
                                                 PATH=str(binary) + ':' + os.environ['PATH']),
                                        text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.strip(), expected)

    @unittest.skipUnless(shutil.which('lua') or shutil.which('lua5.4'), 'Lua required')
    def test_keys_are_unique_repeat_only_continuous_controls_and_do_not_change_tiling(self):
        code = '''
local bindings={['SUPER+Return']='my-terminal',['XF86AudioMute']='old-mute'}
hl={dsp={exec_cmd=function(cmd) return cmd end},
 unbind=function(key) bindings[key]=nil end,
 bind=function(key,cmd,flags) assert(not bindings[key]); bindings[key]={cmd=cmd,flags=flags} end}
dofile(arg[1])
assert(bindings['SUPER+Return']=='my-terminal')
for _,key in ipairs({'XF86AudioRaiseVolume','XF86AudioLowerVolume','XF86MonBrightnessUp','XF86MonBrightnessDown'}) do
 assert(bindings[key].flags.repeating and bindings[key].flags.locked,key)
end
for _,key in ipairs({'XF86AudioMute','XF86AudioMicMute','XF86RFKill','XF86WLAN','XF86ScreenSaver','SUPER+L','XF86Calculator'}) do
 assert(bindings[key] and not bindings[key].flags.repeating,key)
end
assert(not bindings.XF86Calculator.flags.locked)
assert(not bindings.XF86RFKill.flags.locked)
assert(bindings.XF86AudioMicMute.cmd:match('mic%-mute$'))
local count=0;for _ in pairs(bindings) do count=count+1 end;assert(count==12)
'''
        result = subprocess.run([shutil.which('lua') or shutil.which('lua5.4'), '-',
                                 str(ROOT / 'config/hyprland/laptop-keys.lua')],
                                input=code, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def module_fixture(self, temp):
        root = Path(temp)
        (root / 'config/hypr').mkdir(parents=True)
        (root / 'run').mkdir()
        (root / 'bin').mkdir()
        original = '-- my HDR and tiling settings\ndofile(os.getenv("XDG_CONFIG_HOME").."/fedora-postinstall/display-profile.lua")\nhl.config({general={layout="dwindle"}})\n'
        (root / 'config/hypr/hyprland.lua').write_text(original)
        (root / 'config/fedora-postinstall').mkdir()
        (root / 'config/fedora-postinstall/display-profile.lua').write_text('-- HDR off fixture\n')
        for name in ('brightnessctl', 'wpctl', 'rfkill', 'qalculate-gtk'):
            path = root / 'bin' / name
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        path = root / 'bin/Hyprland'
        path.write_text('#!/bin/sh\ntest -f "$XDG_CONFIG_HOME/fedora-postinstall/display-profile.lua" || exit 1\necho "config ok"\n')
        path.chmod(0o755)
        path = root / 'bin/hyprctl'
        path.write_text('''#!/bin/sh
if [ "$1" = reload ] && [ "${FAIL_RELOAD:-}" = 1 ] && [ ! -f "$HOME/reload-failed" ]; then
 touch "$HOME/reload-failed"; exit 1
fi
exit 0
''')
        path.chmod(0o755)
        env = dict(os.environ, HOME=temp, XDG_CONFIG_HOME=str(root / 'config'),
                   PATH=str(root / 'bin') + ':' + os.environ['PATH'], HYPRLAND_INSTANCE_SIGNATURE='fixture')
        script = '''
set -Eeuo pipefail
ROOT=$1
RUN=$HOME/run
CONFIG=$XDG_CONFIG_HOME
DESKTOP=dms
source "$ROOT/lib/core.sh"
source "$ROOT/lib/desktop.sh"
source "$ROOT/modules/laptop-keys.sh"
packages() { printf '%s\\n' "$*" > "$RUN/packages"; }
module_laptop_keys
'''
        return root, original, env, script

    def test_module_repeats_without_losing_custom_code_and_installs_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            root, original, env, script = self.module_fixture(temp)
            for _ in range(2):
                result = subprocess.run(['bash', '-c', script, 'test', str(ROOT)], env=env,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            main = (root / 'config/hypr/hyprland.lua').read_text()
            self.assertTrue(main.startswith(original))
            self.assertEqual(main.count('-- BEGIN FEDORA-POSTINSTALL LAPTOP-KEYS'), 1)
            self.assertEqual((root / 'run/packages').read_text().strip(), 'brightnessctl wireplumber util-linux qalculate-gtk')
            self.assertTrue(os.access(root / '.local/bin/fedora-laptop', os.X_OK))
            self.assertIn('lock)', (root / '.local/share/fedora-postinstall/scripts/desktop-shell').read_text())

    def test_failed_reload_restores_main_and_previous_keys_module(self):
        with tempfile.TemporaryDirectory() as temp:
            root, original, env, script = self.module_fixture(temp)
            module = root / 'config/hypr/fedora-postinstall-laptop-keys.lua'
            module.write_text('-- old key bindings\n')
            result = subprocess.run(['bash', '-c', script, 'test', str(ROOT)], env=dict(env, FAIL_RELOAD='1'),
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / 'config/hypr/hyprland.lua').read_text(), original)
            self.assertEqual(module.read_text(), '-- old key bindings\n')


if __name__ == '__main__':
    unittest.main()
