import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TerminalColors(unittest.TestCase):
    def test_noctalia_enable_keeps_comments_other_templates_and_settings(self):
        enable = runpy.run_path(str(ROOT/'scripts/configure-terminal-colors.py'))['enable_noctalia']
        original = '''# my settings
[theme]
mode = "light" # keep this preference
[theme.templates]
builtin_ids = ["gtk"]
enable_community_templates = false
[bar]
name = "custom"
'''
        effective = '[theme.templates]\nbuiltin_ids = ["gtk", "btop"]\n'
        result = enable(original, effective)
        data = tomllib.loads(result)
        self.assertEqual(data['theme']['templates']['builtin_ids'], ['gtk', 'btop', 'kitty'])
        self.assertTrue(data['theme']['templates']['enable_builtin_templates'])
        self.assertFalse(data['theme']['templates']['enable_community_templates'])
        self.assertEqual(data['theme']['mode'], 'light')
        self.assertEqual(data['bar']['name'], 'custom')
        self.assertIn('# my settings', result)
        self.assertIn('# keep this preference', result)
        self.assertEqual(enable(result, result), result)

    def test_selected_shell_controls_includes_and_only_auto_theme_files_move(self):
        for desktop, expected, absent in [('noctalia', 'themes/noctalia.conf', 'globinclude dank-theme.conf'),
                                           ('dms', 'dank-theme.conf', 'globinclude themes/noctalia.conf')]:
            with self.subTest(desktop=desktop), tempfile.TemporaryDirectory(prefix='kitty colors % ') as temp:
                work = Path(temp)
                config = work/'config'
                (config/'kitty').mkdir(parents=True)
                (config/'dms').mkdir()
                (config/'dms/settings.json').write_text('{"keep":42,"matugenTemplateKitty":false}')
                (config/'kitty/kitty.conf').write_text('# custom\nfont_size 13\n')
                (config/'kitty/dark-theme.auto.conf').write_text('foreground #112233\n')
                (config/'kitty/my-theme.conf').write_text('foreground #445566\n')
                shim = work/'bin'
                shim.mkdir()
                noctalia = shim/'noctalia'
                noctalia.write_text('#!/bin/sh\nprintf \'[theme.templates]\\nbuiltin_ids = ["gtk"]\\n\'\n')
                noctalia.chmod(0o755)
                script = r'''
source "$1/lib/core.sh"
source "$1/modules/terminal-theme.sh"
ROOT=$1
CONFIG=$2/config
RUN=$2/run
DESKTOP=$3
mkdir -p "$RUN"
packages() { :; }
systemctl() { return 1; }
module_terminal_theme
module_terminal_theme
'''
                result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), str(work), desktop],
                                        env=dict(os.environ, PATH=str(shim)+':'+os.environ['PATH']), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                kitty = (config/'kitty/kitty.conf').read_text()
                self.assertIn('globinclude '+expected, kitty)
                self.assertNotIn(absent, kitty)
                self.assertIn('font_size 13', kitty)
                self.assertEqual(kitty.count('# BEGIN FEDORA-POSTINSTALL SYSTEM-COLORS'), 1)
                self.assertEqual((work/'run/kitty-dark-theme.auto.conf').read_text(), 'foreground #112233\n')
                self.assertFalse((config/'kitty/dark-theme.auto.conf').exists())
                self.assertTrue((config/'kitty/my-theme.conf').exists())
                unit = (config/'systemd/user/fedora-kitty-theme.path').read_text()
                self.assertIn('PathChanged='+str(config).replace('%', '%%')+'/kitty/'+expected, unit)
                if desktop == 'dms':
                    import json
                    data = json.loads((config/'dms/settings.json').read_text())
                    self.assertEqual(data['keep'], 42)
                    self.assertTrue(data['matugenTemplateKitty'])
                    self.assertTrue(data['runDmsMatugenTemplates'])

    def test_plasma_does_not_enable_a_hyprland_shell_theme(self):
        script = r'''
source "$1/modules/terminal-theme.sh"
DESKTOP=plasma
packages() { echo FORBIDDEN; exit 99; }
module_terminal_theme
'''
        result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('FORBIDDEN', result.stdout)
