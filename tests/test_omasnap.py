import os
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Omasnap(unittest.TestCase):
    def test_binding_merge_preserves_custom_code_and_is_idempotent(self):
        merge = runpy.run_path(str(ROOT/'scripts/omasnap-bindings.py'))['merge']
        custom = '-- my private bindings\nhl.bind("PRINT", custom_action)\n'
        module = Path('/tmp/path with spaces/omasnap.lua')
        result = merge(custom, module)
        self.assertTrue(result.startswith(custom))
        self.assertEqual(merge(result, module), result)
        self.assertEqual(result.count('dofile('), 1)
        with self.assertRaises(ValueError):
            merge('-- END FEDORA-POSTINSTALL OMASNAP\n'+custom, module)

    def test_only_two_conflicting_keys_are_overridden_after_user_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/'.local/bin/omasnap'
            binary.parent.mkdir(parents=True)
            binary.write_text('fixture')
            code = '''
local binds = { PRINT = "old screenshot", ["SUPER + SHIFT + S"] = "old edit", ["SUPER + T"] = "personal" }
local events = {}
hl = {
    unbind = function(key) binds[key] = nil; events[#events+1] = "unbind:" .. key end,
    bind = function(key, command) assert(binds[key] == nil); binds[key] = command; events[#events+1] = "bind:" .. key end,
    layer_rule = function(rule) assert(rule.match.namespace == "^omasnap$"); assert(rule.no_screen_share == nil) end,
    dsp = { exec_cmd = function(command) return command end },
}
dofile(arg[1])
assert(binds["SUPER + T"] == "personal")
assert(binds.PRINT:find("/.local/bin/omasnap", 1, true))
assert(binds["SUPER + SHIFT + S"]:find("--capture-region --editor overlay", 1, true))
assert(events[1] == "unbind:PRINT" and events[2] == "unbind:SUPER + SHIFT + S")
'''
            subprocess.run(['lua', '-', str(ROOT/'config/hyprland/omasnap.lua')], input=code,
                           text=True, capture_output=True, check=True, env=dict(os.environ, HOME=temp))

    def test_failed_source_fetch_keeps_previous_working_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            app = work/'.local/share/fedora-postinstall/apps/omasnap'
            (app/'old/bin').mkdir(parents=True)
            (app/'old/revision').write_text('previous revision\n')
            (app/'old/bin/omasnap').write_text('#!/bin/sh\nexit 0\n')
            (app/'old/bin/omasnap').chmod(0o755)
            (app/'current').symlink_to('old')
            shim = work/'shim'
            shim.mkdir()
            (shim/'git').write_text('#!/bin/sh\nexit 42\n')
            (shim/'git').chmod(0o755)
            result = subprocess.run([str(ROOT/'scripts/omasnap-manager'), 'install'],
                                    env=dict(os.environ, HOME=temp, PATH=str(shim)+':'+os.environ['PATH']),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertEqual(os.readlink(app/'current'), 'old')
            self.assertTrue((app/'old/bin/omasnap').exists())
            self.assertEqual(list(app.glob('.build.*')), [])

    def test_failed_upstream_tests_keep_payload_and_full_diagnostic_log(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            app = work/'.local/share/fedora-postinstall/apps/omasnap'
            (app/'old/bin').mkdir(parents=True)
            (app/'old/revision').write_text('previous revision\n')
            (app/'current').symlink_to('old')
            shim = work/'shim'
            shim.mkdir()
            revision = (ROOT/'data/omasnap-release').read_text().split()[1]
            (shim/'git').write_text(
                '#!/usr/bin/env python3\nimport pathlib,sys\n'
                'if sys.argv[1] == "init": pathlib.Path(sys.argv[-1]).mkdir(parents=True)\n'
                f'if "rev-parse" in sys.argv: print({revision!r})\n')
            (shim/'cmake').write_text('#!/bin/sh\nexit 0\n')
            (shim/'ctest').write_text('#!/bin/sh\necho "fixture: pin cleanup failed" >&2\nexit 8\n')
            for path in shim.iterdir():
                path.chmod(0o755)
            result = subprocess.run([str(ROOT/'scripts/omasnap-manager'), 'install'],
                                    env=dict(os.environ, HOME=temp, PATH=str(shim)+':'+os.environ['PATH']),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 8, result.stdout+result.stderr)
            self.assertEqual(os.readlink(app/'current'), 'old')
            logs = list((app/'test-logs').glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('fixture: pin cleanup failed', logs[0].read_text())
            self.assertIn(str(logs[0]), result.stderr)
            self.assertEqual(list(app.glob('.build.*')), [])

    def test_btop_deduplicates_only_the_requested_setting(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            config, patch, result = (work/name for name in ('btop.conf', 'patch', 'result'))
            config.write_text('# preserve comment\ntheme_background = True\nupdate_ms = 1500\n')
            patch.write_text('theme_background = False\n')
            for _ in range(2):
                subprocess.run(['python3', str(ROOT/'scripts/merge-config-block.py'), str(config),
                                str(patch), str(result), 'BTOP', '--replace-keys'], check=True)
                shutil.copyfile(result, config)
            self.assertIn('update_ms = 1500', config.read_text())
            self.assertIn('# preserve comment', config.read_text())
            self.assertEqual(config.read_text().count('theme_background ='), 1)
            self.assertIn('theme_background = False', config.read_text())

    def test_code_profile_never_downloads_jetbrains_or_arduino(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work/'lib').mkdir()
            shutil.copyfile(ROOT/'lib/development.sh', work/'lib/development.sh')
            (work/'modules').mkdir()
            (work/'modules/repositories.sh').write_text('# fixture\n')
            (work/'modules/vscode.sh').write_text('module_vscode() { echo CODE; }\n')
            script = '''source "$1/modules/development.sh"
ROOT=$2
DEV_PROFILE=$3
install_language_tools() { echo LANGUAGES; }
packages() { echo "PACKAGES $*"; }
run() { echo "VENDOR $*"; }
log() { :; }
module_development
'''
            for profile in ('code', 'full'):
                result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp, profile],
                                        text=True, capture_output=True, check=True)
                self.assertIn('CODE', result.stdout)
                self.assertEqual('VENDOR' in result.stdout, profile == 'full')

    def test_runtime_bind_check_accepts_lua_dispatcher_ids_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            manager = work/'.local/share/fedora-postinstall/scripts/omasnap-manager'
            manager.parent.mkdir(parents=True)
            manager.write_text('#!/bin/sh\nexit 0\n')
            manager.chmod(0o755)
            shim = work/'bin'
            shim.mkdir()
            hyprctl = shim/'hyprctl'
            hyprctl.write_text('#!/bin/sh\ncat "$BINDS_FIXTURE"\n')
            hyprctl.chmod(0o755)
            fixture = work/'binds.json'
            binds = [dict(key='PRINT', modmask=0, submap='', dispatcher='HL.Dispatcher(exec_cmd)',
                          arg='36', description='Omasnap: capture'),
                     dict(key='s', modmask=65, submap='', dispatcher='HL.Dispatcher(exec_cmd)',
                          arg='37', description='Omasnap: edit region')]
            env = dict(os.environ, HOME=temp, PATH=str(shim)+':'+os.environ['PATH'],
                       HYPRLAND_INSTANCE_SIGNATURE='test', WAYLAND_DISPLAY='test', BINDS_FIXTURE=str(fixture))
            for duplicate in (False, True):
                fixture.write_text(json.dumps(binds+[binds[0]] if duplicate else binds))
                result = subprocess.run([str(ROOT/'scripts/validate-omasnap')], env=env,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 1 if duplicate else 0, result.stdout+result.stderr)
