import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Safety(unittest.TestCase):
    def test_dry_run_no_writes_or_external_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            home.mkdir()
            shim = Path(temp) / 'bin'
            shim.mkdir()
            for cmd in ('sudo', 'dnf5', 'rpm', 'curl', 'flatpak', 'systemctl'):
                f = shim / cmd
                f.write_text('#!/bin/sh\necho FORBIDDEN >&2; exit 99\n')
                f.chmod(0o755)
            env = dict(os.environ, HOME=str(home), PATH=str(shim)+':'+os.environ['PATH'])
            result = subprocess.run(['bash', str(ROOT/'install.sh'), '--dry-run'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('FORBIDDEN', result.stderr)
            self.assertFalse(list(home.iterdir()))

    def test_invalid_module(self):
        r = subprocess.run(['bash', str(ROOT/'install.sh'), '--dry-run', '--modules', '../lib/core'], capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_repository_rejects_unsafe_inputs(self):
        for body in ('baseurl=https://evil.example/rpm\ngpgkey=https://evil.example/key\ngpgcheck=1',
                     'baseurl=https://repo.vscodium.dev/rpm\ngpgkey=https://repo.vscodium.dev/key\ngpgcheck=0'):
            with tempfile.NamedTemporaryFile(mode='w') as f:
                f.write('[vendor]\n'+body+'\n')
                f.flush()
                r = subprocess.run(['python3', str(ROOT/'scripts/check-repo.py'), 'vscodium', f.name], capture_output=True)
                self.assertNotEqual(r.returncode, 0)

    def test_repo_valid(self):
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write('[vscodium]\nbaseurl=https://repo.vscodium.dev/rpms/\ngpgkey=https://repo.vscodium.dev/vscodium.gpg\ngpgcheck=1\n')
            f.flush()
            subprocess.run(['python3', str(ROOT/'scripts/check-repo.py'), 'vscodium', f.name], check=True, capture_output=True)

if __name__ == '__main__':
    unittest.main()
