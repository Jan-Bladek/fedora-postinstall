import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/fedora-display'
DISPLAY = runpy.run_path(str(SCRIPT))


class DisplayProfile(unittest.TestCase):
    def test_loader_is_first_idempotent_and_reset_preserves_user_config(self):
        original = '-- User header\nrequire("dms.outputs")\nhl.config({misc={vrr=1}})\n'
        merged = DISPLAY['merge'](original, True)
        self.assertLess(merged.index('dofile('), merged.index('require("dms.outputs")'))
        self.assertEqual(DISPLAY['merge'](merged, True), merged)
        self.assertEqual(DISPLAY['merge'](merged, False), original)
        with self.assertRaises(ValueError):
            DISPLAY['merge'](DISPLAY['BEGIN'] + '\n' + original, True)

    @unittest.skipUnless(shutil.which('lua') or shutil.which('lua5.4'), 'Lua required')
    def test_profiles_keep_layout_and_user_tables_and_override_late_dms_settings(self):
        for mode in ('on', 'off'):
            # Execute real generated Lua against recording public API stand-ins.
            code = '''
local monitors, configs = {}, {}
hl = {monitor=function(t) table.insert(monitors,t) end,
      config=function(t) table.insert(configs,t) end}
''' + DISPLAY['profile'](mode) + '''
local original = {output="desc:Monitor", mode="3840x2160@144", position="-3840x0",
 scale=1.5, transform=1, mirror="DP-2", vrr=2, icc="/my profile.icc",
 sdrbrightness=1.25, reserved_area={1,2,3,4}, cm="hdr", bitdepth=10, supports_hdr=0}
hl.monitor(original)
local result = monitors[1]
for key,value in pairs(original) do
 if key~="cm" and key~="bitdepth" and key~="supports_hdr" then assert(result[key]==value,key) end
end
assert(original.cm=="hdr" and original.bitdepth==10 and original.supports_hdr==0)
local original_config={render={cm_auto_hdr=2,send_content_type=true,cm_enabled=true},misc={vrr=2}}
hl.config(original_config)
assert(original_config.render.cm_auto_hdr==2)
assert(configs[2].misc==original_config.misc and configs[2].render.cm_enabled==true)
''' + ('''
assert(result.cm=="auto" and result.bitdepth==10 and result.supports_hdr==0)
assert(configs[2].render.cm_auto_hdr==1 and configs[2].render.send_content_type==true)
''' if mode == 'on' else '''
assert(result.cm=="srgb" and result.bitdepth==8 and result.supports_hdr==-1)
assert(configs[2].render.cm_auto_hdr==0 and configs[2].render.send_content_type==false)
''')
            result = subprocess.run([shutil.which('lua') or shutil.which('lua5.4'), '-'],
                                    input=code, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def fixture(self, temp):
        home = Path(temp)
        config = home / 'config'
        (config / 'hypr').mkdir(parents=True)
        original = 'hl.monitor({output="DP-1",mode="3840x2160@144",scale=1.5})\n'
        (config / 'hypr/hyprland.lua').write_text(original)
        binary = home / 'bin'
        binary.mkdir()
        hyprland = binary / 'Hyprland'
        hyprland.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
assert 'HYPRLAND_INSTANCE_SIGNATURE' not in os.environ
assert 'WAYLAND_DISPLAY' not in os.environ
assert Path(os.environ['XDG_CONFIG_HOME']) != Path(os.environ['REAL_CONFIG'])
assert sys.argv[1:3] == ['--verify-config','--config']
if os.environ.get('VERIFY_FAIL'): sys.exit(1)
print('config ok')
''')
        hyprland.chmod(0o755)
        hyprctl = binary / 'hyprctl'
        hyprctl.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
if sys.argv[1]=='reload':
 path=Path(os.environ['HOME'])/'reload-count'
 n=int(path.read_text())+1 if path.exists() else 1
 path.write_text(str(n))
 print('ok')
elif sys.argv[1]=='configerrors':
 path=Path(os.environ['HOME'])/'reload-count'
 if os.environ.get('RELOAD_FAIL') and path.exists() and path.read_text()=='1':
  print('rejected new settings')
''')
        hyprctl.chmod(0o755)
        env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(config), REAL_CONFIG=str(config),
                   XDG_STATE_HOME=str(home / 'state'), PATH=str(binary) + ':' + os.environ['PATH'])
        env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
        return home, config, original, env

    def invoke(self, action, env):
        return subprocess.run(['python3', str(SCRIPT), action], env=env, capture_output=True, text=True)

    @unittest.skipIf(os.geteuid() == 0, 'desktop command intentionally rejects root')
    def test_standalone_install_off_toggle_and_reset_without_system_installer(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, original, env = self.fixture(temp)
            for action, expected in [('install', None), ('off', 'off'), ('toggle', 'on'),
                                     ('toggle', 'off'), ('reset', 'reset')]:
                result = self.invoke(action, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                if expected:
                    self.assertEqual(DISPLAY['selected'](config), expected)
            self.assertEqual((config / 'hypr/hyprland.lua').read_text(), original)
            self.assertFalse((config / 'fedora-postinstall/display-profile.lua').exists())
            self.assertTrue(os.access(home / '.local/bin/fedora-display', os.X_OK))

    @unittest.skipIf(os.geteuid() == 0, 'desktop command intentionally rejects root')
    def test_invalid_proposal_does_not_modify_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            _, config, original, env = self.fixture(temp)
            result = self.invoke('off', dict(env, VERIFY_FAIL='1'))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((config / 'hypr/hyprland.lua').read_text(), original)
            self.assertFalse((config / 'fedora-postinstall/display-profile.lua').exists())

    @unittest.skipIf(os.geteuid() == 0, 'desktop command intentionally rejects root')
    def test_reload_failure_restores_previous_profile_and_original_config(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, original, env = self.fixture(temp)
            result = self.invoke('off', dict(env, HYPRLAND_INSTANCE_SIGNATURE='fixture', RELOAD_FAIL='1'))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((config / 'hypr/hyprland.lua').read_text(), original)
            self.assertFalse((config / 'fedora-postinstall/display-profile.lua').exists())
            self.assertEqual((home / 'reload-count').read_text(), '2')
            # Also preserve an existing HDR profile when a switch back fails.
            self.assertEqual(self.invoke('on', env).returncode, 0)
            before = (config / 'fedora-postinstall/display-profile.lua').read_bytes()
            (home / 'reload-count').unlink()
            result = self.invoke('off', dict(env, HYPRLAND_INSTANCE_SIGNATURE='fixture', RELOAD_FAIL='1'))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((config / 'fedora-postinstall/display-profile.lua').read_bytes(), before)

    @unittest.skipIf(os.geteuid() == 0, 'desktop command intentionally rejects root')
    def test_symlink_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, original, env = self.fixture(temp)
            main = config / 'hypr/hyprland.lua'
            external = home / 'original.lua'
            main.rename(external)
            main.symlink_to(external)
            result = self.invoke('off', env)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(main.is_symlink())
            self.assertEqual(external.read_text(), original)


if __name__ == '__main__':
    unittest.main()
