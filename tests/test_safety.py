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

    def test_language_tools_preserve_rust_distribution(self):
        script = r"""
source "$1/modules/development.sh"
packages() { printf 'PACKAGES %s\n' "$*"; }
run() { printf 'RUN %s\n' "$*"; }
command() {
    if [[ $* == '-v rustup' ]]; then return "$RUSTUP_MISSING"; fi
    builtin command "$@"
}
install_language_tools
"""
        for missing in ('0', '1'):
            env = dict(os.environ, RUSTUP_MISSING=missing)
            r = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                               env=env, capture_output=True, text=True, check=True)
            self.assertIn('python3-pip python3-devel gcc gcc-c++', r.stdout)
            if missing == '0':
                self.assertIn('RUN rustup toolchain install stable', r.stdout)
                self.assertNotIn('PACKAGES rust cargo', r.stdout)
                self.assertNotIn('rustup default', r.stdout)
            else:
                self.assertIn('PACKAGES rust cargo clippy rustfmt rust-src', r.stdout)
                self.assertNotIn('RUN rustup', r.stdout)

    def test_update_does_not_install_unselected_vendor_apps(self):
        with tempfile.TemporaryDirectory() as home:
            script = r"""
import runpy
import sys
import urllib.request
from pathlib import Path

def forbidden(*args, **kwargs):
    raise AssertionError('Update must not fetch unselected applications')
urllib.request.urlopen = forbidden
# The test runner may be root in CI/container environments; simulate a desktop user.
import os
os.geteuid = lambda: 1000
home = Path(sys.argv[1])
Path.home = classmethod(lambda cls: home)
sys.argv = ['vendor-apps.py', 'update']
runpy.run_path(str(Path.cwd() / 'scripts/vendor-apps.py'), run_name='__main__')
"""
            subprocess.run(['python3', '-c', script, home], cwd=ROOT, check=True,
                           capture_output=True, text=True)

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
