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
source "$1/lib/development.sh"
source "$1/modules/development.sh"
DEV_APPS="rustrover clion"
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
            self.assertIn('PACKAGES gcc gcc-c++', r.stdout)
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

    def test_failed_transaction_does_not_poison_verification(self):
        script = r"""
source "$1/lib/core.sh"
RUN=$2
rpm() { return 1; }
run() { return 42; }
packages nonexistent-package
"""
        with tempfile.TemporaryDirectory() as run:
            r = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), run],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 42)
            self.assertFalse((Path(run) / 'expected-rpm').exists())

    def test_wrong_editor_default_is_rejected_for_whitespace_module_lists(self):
        script = r"""
source "$1/lib/core.sh"
source "$1/lib/verify.sh"
ROOT=$1
RUN=$2
MODULES=$'terminal\tdefaults\nupdates'
HOME=$2
command() { [[ $* == '-v code' ]]; }
code_desktop_id() { echo code.desktop; }
xdg-mime() { echo another-editor.desktop; }
run() { echo UNEXPECTED_PACKAGE_CHECK; return 77; }
verify
"""
        with tempfile.TemporaryDirectory() as run:
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), run],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('VS Code default verification failed', result.stderr)
            self.assertNotIn('UNEXPECTED_PACKAGE_CHECK', result.stdout)

    def test_egl_workaround_is_limited_to_0570_virtual_machines(self):
        script = r"""
source "$1/modules/hyprland.sh"
ROOT=$1
RUN=$2
log() { :; }
systemd-detect-virt() { return "$VIRT_STATUS"; }
prepare_hyprland_config "$TEST_VERSION"
"""
        for version, status, expected in [('0.57.0', '0', True), ('0.57.0', '1', False),
                                          ('0.56.2', '0', False), ('0.57.1', '0', False)]:
            with self.subTest(version=version, status=status), tempfile.TemporaryDirectory() as temp:
                subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp], check=True,
                               env=dict(os.environ, VIRT_STATUS=status, TEST_VERSION=version))
                config = (Path(temp) / 'hyprland.lua').read_text()
                self.assertEqual('skip_non_kms_dmabuf_formats = false' in config, expected)

    def test_plasma_targets_keep_apps_and_fail_on_unreadable_rpm_database(self):
        script = r"""
source "$1/modules/kde-removal.sh"
rpm() {
    if [[ $RPM_FAILURE == 1 ]]; then return 42; fi
    printf '%s\n' plasma-desktop plasma-workspace kwin dolphin kate qt6-qtbase NetworkManager
}
plasma_removal_targets
"""
        for failure in ('0', '1'):
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                                    env=dict(os.environ, RPM_FAILURE=failure), capture_output=True, text=True)
            if failure == '1':
                self.assertEqual(result.returncode, 42)
                self.assertEqual(result.stdout, '')
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(set(result.stdout.splitlines()), {'plasma-desktop', 'plasma-workspace', 'kwin'})

    def test_invalid_module(self):
        r = subprocess.run(['bash', str(ROOT/'install.sh'), '--dry-run', '--modules', '../lib/core'], capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_codec_swap_refuses_placeholder_specific_consumers(self):
        script = r"""
source "$1/lib/core.sh"
source "$1/modules/multimedia.sh"
rpm() {
    case "$*" in
        '-q openh264') return 1 ;;
        '-q noopenh264') return 0 ;;
        *) printf 'custom-sdk\tnoopenh264(x86-64) glibc\n' ;;
    esac
}
packages() { echo UNEXPECTED_MUTATION; return 88; }
sudo() { echo UNEXPECTED_MUTATION; return 88; }
configure_obs_codecs
"""
        result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('custom-sdk', result.stderr)
        self.assertNotIn('UNEXPECTED_MUTATION', result.stdout)

    def test_repository_rejects_unsafe_inputs(self):
        for body in ('baseurl=https://evil.example/rpm\ngpgkey=https://evil.example/key\ngpgcheck=1',
                     'baseurl=https://repo.vscodium.dev/rpm\ngpgkey=https://repo.vscodium.dev/key\ngpgcheck=0'):
            with tempfile.NamedTemporaryFile(mode='w') as f:
                f.write('[vendor]\n'+body+'\n')
                f.flush()
                for optimized in ('0', '1'):
                    r = subprocess.run(['python3', str(ROOT/'scripts/check-repo.py'), 'vscodium', f.name],
                                       env=dict(os.environ, PYTHONOPTIMIZE=optimized), capture_output=True)
                    self.assertNotEqual(r.returncode, 0)

    def test_repo_valid(self):
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write('[vscodium]\nbaseurl=https://repo.vscodium.dev/rpms/\ngpgkey=https://repo.vscodium.dev/vscodium.gpg\ngpgcheck=1\n')
            f.flush()
            subprocess.run(['python3', str(ROOT/'scripts/check-repo.py'), 'vscodium', f.name], check=True, capture_output=True)

if __name__ == '__main__':
    unittest.main()
