import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FedoraReleases(unittest.TestCase):
    def test_release_allowlist_is_exact(self):
        for release in ('43', '44', '45', '46', 'rawhide', '45.1', ''):
            result = subprocess.run(['bash', '-eu', '-c',
                                     'source "$1/lib/core.sh"; supported_fedora_release "$2"',
                                     'test', str(ROOT), release], capture_output=True)
            self.assertEqual(result.returncode == 0, release in ('44', '45'))

    @unittest.skipIf(os.geteuid() == 0, 'preflight intentionally rejects root')
    def test_preflight_accepts_44_and_45_and_rejects_other_targets(self):
        cases = [('fedora', '44', True), ('fedora', '45', True), ('fedora', '43', False),
                 ('fedora', '46', False), ('fedora', 'rawhide', False), ('ubuntu', '45', False)]
        for distro, release, accepted in cases:
            result = self.preflight(distro, release)
            self.assertEqual(result.returncode == 0, accepted, result.stderr)

    @unittest.skipIf(os.geteuid() == 0, 'preflight intentionally rejects root')
    def test_45_still_requires_x86_64_and_enforcing_selinux(self):
        for environment, message in [({'FIXTURE_ARCH': 'aarch64'}, 'x86_64'),
                                     ({'FIXTURE_SELINUX': 'Permissive'}, 'SELinux Enforcing')]:
            result = self.preflight('fedora', '45', **environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stderr)

    def preflight(self, distro, release, **extra):
        script = r'''
source "$1/lib/core.sh"
source() {
    if [[ $1 == /etc/os-release ]]; then ID=$FIXTURE_ID; VERSION_ID=$FIXTURE_VERSION;
    else builtin source "$@"; fi
}
uname() { echo "${FIXTURE_ARCH:-x86_64}"; }
getenforce() { echo "${FIXTURE_SELINUX:-Enforcing}"; }
command() { [[ $* == '-v dnf5' || $* == '-v sudo' ]]; }
DRY_RUN=0
DESKTOP=dms
preflight
'''
        return subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                              env=dict(os.environ, FIXTURE_ID=distro, FIXTURE_VERSION=release, **extra),
                              capture_output=True, text=True)

    def test_copr_urls_use_the_selected_fedora_release(self):
        script = r'''
ROOT=$1
source "$ROOT/lib/core.sh"
source "$ROOT/modules/$2.sh"
source() {
    if [[ $1 == "$ROOT/modules/repositories.sh" ]]; then return 0;
    else builtin source "$@"; fi
}
rpm() { return 1; }
sudo() { return 0; }
vendor_repo() { printf '%s\n' "$2"; }
packages() { exit 0; }
flea_quickshell_ready() { return 1; }
VERSION_ID=$3
DESKTOP=dms
FILE_MANAGER=flea
module_${2//-/_}
'''
        with tempfile.TemporaryDirectory() as home:
            for release in ('44', '45'):
                for module, project in [('hyprland', 'lionheartp/Hyprland'), ('files', 'lionheartp/Hyprland'),
                                        ('dms', 'duxlabs/dms')]:
                    result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), module, release],
                                            env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config'),
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f'/coprs/{project}/repo/fedora-{release}/', result.stdout)


if __name__ == '__main__':
    unittest.main()
