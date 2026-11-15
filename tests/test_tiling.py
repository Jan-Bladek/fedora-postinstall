import contextlib
import io
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TILING = runpy.run_path(str(ROOT / 'scripts/configure-tiling.py'))
TEMPLATE = (ROOT / 'config/hyprland/hyprland.lua').read_text()
DISPLAY = runpy.run_path(str(ROOT / 'scripts/fedora-display'))


class TilingPolicy(unittest.TestCase):
    def test_last_loaded_block_is_idempotent_and_keeps_custom_code(self):
        original = '-- My settings\nrequire("dms.layout")\nhl.config({misc={vrr=2}})\n'
        original = DISPLAY['merge'](original, True)
        merged = TILING['merge'](original, TEMPLATE)
        self.assertTrue(merged.startswith(original.rstrip()))
        self.assertGreater(merged.index(TILING['BEGIN']), merged.index('require("dms.layout")'))
        self.assertEqual(TILING['merge'](merged, TEMPLATE), merged)
        with self.assertRaises(ValueError):
            TILING['merge'](original + TILING['END'], TEMPLATE)

    def test_dms_include_migration_does_not_duplicate_existing_tiling_policy(self):
        dms = runpy.run_path(str(ROOT / 'scripts/dms-includes.py'))
        original = TILING['merge']('-- Custom\n' + dms['OLD'], TEMPLATE)
        migrated = dms['migrate'](original, TEMPLATE)
        self.assertEqual(migrated.count(TILING['BEGIN']), 1)
        self.assertIn('require("dms.layout")', migrated)

    @unittest.skipUnless(shutil.which('lua') or shutil.which('lua5.4'), 'Lua required')
    def test_dms_cannot_leave_monocle_or_fullscreen_takeover_and_binds_are_unique(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            (config / 'fedora-postinstall').mkdir()
            (config / 'fedora-postinstall/shell').write_text('dms\n')
            (config / 'hypr/dms').mkdir(parents=True)
            for name in ('colors', 'outputs', 'layout', 'cursor', 'input', 'windowrules'):
                (config / f'hypr/dms/{name}.lua').write_text('')
            (config / 'hypr/dms/layout.lua').write_text('hl.config({general={layout="monocle"},misc={on_focus_under_fullscreen=1}})')
            code = '''
local config, binds, rules = {}, {}, {}
local function no_op() end
hl = {
 monitor=no_op, on=no_op, curve=no_op, animation=no_op,
 config=function(t) for k,v in pairs(t) do
  config[k]=config[k] or {}; for a,b in pairs(v) do config[k][a]=b end
 end end,
 bind=function(key,action) assert(not binds[key],key); binds[key]=action end,
 unbind=function(key) binds[key]=nil end,
 window_rule=function(t) rules[t.name]=t end,
}
local dsp={}
setmetatable(dsp,{__index=function(t,k)
 return setmetatable({}, {__index=function(_,name) return function(args) return {name=name,args=args} end end,
                         __call=function(_,args) return {name=k,args=args} end})
end})
hl.dsp=dsp
package.path=os.getenv('XDG_CONFIG_HOME')..'/hypr/?.lua;'..package.path
dofile(arg[1])
assert(config.general.layout=='dwindle')
assert(config.misc.on_focus_under_fullscreen==2)
assert(config.misc.exit_window_retains_fullscreen==0)
assert(binds['SUPER+Return'].args=='kitty --start-as=normal')
assert(binds['SUPER+F'].name=='fullscreen')
assert(binds['SUPER+F'].args.action=='toggle' and binds['SUPER+F'].args.mode=='fullscreen')
assert(binds['SUPER+CTRL+F'].args=='xdg-open "$HOME"')
local rule=rules['fedora-postinstall-kitty-tiled']
assert(rule.match.class=='^kitty$' and rule.tile==true)
assert(rule.fullscreen_state=='0 0' and rule.suppress_event=='maximize fullscreen')
'''
            result = subprocess.run([shutil.which('lua') or shutil.which('lua5.4'), '-',
                                     str(ROOT / 'config/hyprland/hyprland.lua')], input=code,
                                    env=dict(os.environ, XDG_CONFIG_HOME=temp), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipIf(os.geteuid() == 0, 'desktop configuration intentionally rejects root')
    def test_existing_installation_keeps_hdr_profile_and_backs_up_main(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            config = home / 'config'
            (config / 'hypr').mkdir(parents=True)
            (config / 'fedora-postinstall').mkdir()
            original = DISPLAY['merge']('-- Custom\nhl.config({misc={vrr=2}})\n', True)
            main = config / 'hypr/hyprland.lua'
            main.write_text(original)
            profile = DISPLAY['profile']('off')
            (config / 'fedora-postinstall/display-profile.lua').write_text(profile)
            checks = []
            def verify(root, text, selected_profile):
                self.assertEqual(root, config)
                self.assertEqual(selected_profile, profile)
                self.assertIn('-- Custom', text)
                checks.append(text)
            helpers = dict(DISPLAY, verify=verify)
            with patch.dict(os.environ, HOME=temp, XDG_CONFIG_HOME=str(config),
                            XDG_STATE_HOME=str(home / 'state'), HYPRLAND_INSTANCE_SIGNATURE=''), \
                    patch.object(runpy, 'run_path', return_value=helpers), contextlib.redirect_stdout(io.StringIO()):
                TILING['apply']()
                TILING['apply']()
            self.assertEqual(checks[0], checks[1])
            self.assertEqual((config / 'fedora-postinstall/display-profile.lua').read_text(), profile)
            backups = list((home / 'state/fedora-postinstall').glob('tiling-*/hyprland.lua'))
            self.assertTrue(any(path.read_text() == original for path in backups))

    @unittest.skipIf(os.geteuid() == 0, 'desktop configuration intentionally rejects root')
    def test_live_reload_failure_restores_exact_previous_config(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / 'hypr').mkdir()
            main = home / 'hypr/hyprland.lua'
            original = '-- Custom\nhl.config({misc={vrr=2}})\n'
            main.write_text(original)
            helpers = dict(DISPLAY, verify=lambda *args: None, run=lambda *args: '')
            with patch.dict(os.environ, HOME=temp, XDG_CONFIG_HOME=temp,
                            XDG_STATE_HOME=str(home / 'state'), HYPRLAND_INSTANCE_SIGNATURE='fixture'), \
                    patch.object(runpy, 'run_path', return_value=helpers), \
                    patch.dict(helpers, reload_config=unittest.mock.Mock(side_effect=[RuntimeError('rejected'), None])):
                with self.assertRaisesRegex(RuntimeError, 'rejected'):
                    TILING['apply']()
            self.assertEqual(main.read_text(), original)


if __name__ == '__main__':
    unittest.main()
