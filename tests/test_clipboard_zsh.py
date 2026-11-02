import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

import test_experience

ROOT = Path(__file__).resolve().parents[1]


class ClipboardZsh(unittest.TestCase):
    @unittest.skipUnless(shutil.which('fzf'), 'fzf is required for the real keyboard test')
    def test_real_fzf_tab_and_arrows_copy_selected_bytes_without_execution(self):
        for key in (b'\t', b'\x1b[A', b'\x1b[B'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                shim = work/'bin'
                shim.mkdir()
                scripts = {
                    'cliphist': '#!/bin/sh\ncase $1 in\nlist) printf "2\\tnew\\n1\\told\\n" ;;\ndecode) IFS= read -r item; case $item in 1*) ;; *) printf new; exit 0 ;; esac; printf \'old\\n$(touch SHOULD_NOT_EXIST)\\n\' ;;\nesac\n',
                    'wl-copy': '#!/bin/sh\ncat > "$COPY_RESULT"\n',
                }
                for name, content in scripts.items():
                    file = shim/name
                    file.write_text(content)
                    file.chmod(0o755)
                command = ['env', 'PATH='+str(shim)+':'+os.environ['PATH'], 'COPY_RESULT='+str(work/'copied'),
                           'bash', str(ROOT/'scripts/clipboard-history'), 'pick']
                status, output = test_experience.Experience().run_terminal(command, key+b'\r',
                                                                           ready=b'Schowek', rows=24, columns=100)
                self.assertEqual(status, 0, output)
                self.assertEqual((work/'copied').read_bytes(), b'old\n$(touch SHOULD_NOT_EXIST)\n')
                self.assertFalse((ROOT/'SHOULD_NOT_EXIST').exists())

    def test_empty_or_failed_history_never_changes_clipboard(self):
        for status in (0, 33):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                shim = Path(temp)
                (shim/'cliphist').write_text(f'#!/bin/sh\nexit {status}\n')
                (shim/'cliphist').chmod(0o755)
                (shim/'wl-copy').write_text('#!/bin/sh\necho FORBIDDEN; exit 99\n')
                (shim/'wl-copy').chmod(0o755)
                result = subprocess.run(['bash', str(ROOT/'scripts/clipboard-history'), 'pick'],
                                        env=dict(os.environ, PATH=str(shim)+':'+os.environ['PATH']),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertNotIn('FORBIDDEN', result.stdout)

    def test_clipboard_binding_merge_keeps_other_bindings_and_is_idempotent(self):
        merge = runpy.run_path(str(ROOT/'scripts/omasnap-bindings.py'))['merge']
        text = '-- custom Super+V\n'
        module = Path('/tmp/clipboard.lua')
        first = merge(text, module, 'CLIPBOARD')
        self.assertEqual(merge(first, module, 'CLIPBOARD'), first)
        self.assertTrue(first.startswith(text))
        self.assertEqual(first.count('dofile('), 1)

    def test_zsh_update_does_not_download_an_uninstalled_shell(self):
        script = r'''
import os, runpy, sys, urllib.request
from pathlib import Path
ns = runpy.run_path(sys.argv[1])
ns['install'].__globals__['Path'].home = classmethod(lambda cls: Path(sys.argv[2]))
urllib.request.urlopen = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('Unselected download'))
ns['install']('update')
'''
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(['python3', '-B', '-c', script, str(ROOT/'scripts/zsh-manager.py'), temp], check=True)
