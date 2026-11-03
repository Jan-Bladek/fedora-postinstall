import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
source "$1/lib/core.sh"
source "$1/lib/verify.sh"
RUN=$2
MODULES=development
rpm() {
    printf '%s\n' "$*" >> "$RUN/rpm-calls"
    case "$*" in
        '-q git') return 0 ;;
        '-q --whatprovides nodejs'|'-q --whatprovides npm') [[ -f $RUN/installed ]] ;;
        *) return 1 ;;
    esac
}
run() {
    printf '%s\n' "$*" >> "$RUN/commands"
    case "$*" in
        'sudo dnf5 install nodejs npm')
            if [[ ${INSTALL_PROVIDES:-1} == 1 ]]; then touch "$RUN/installed"; fi ;;
        'sudo dnf5 check') return 0 ;;
        *) return 88 ;;
    esac
}
command() {
    # No optional GUI/mesh applications in this focused verification fixture.
    if [[ $* == '-v tailscale' ]]; then return 1; fi
    builtin command "$@"
}
'''


class RpmRequirements(unittest.TestCase):
    def invoke(self, work, body, **env):
        return subprocess.run(['bash', '-eu', '-c', FIXTURE+body, 'test', str(ROOT), str(work)],
                              env=dict(os.environ, **env), capture_output=True, text=True)

    def test_installed_versioned_node_providers_pass_install_and_final_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work/'installed').touch()
            result = self.invoke(work, '\npackages nodejs npm git\nverify\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((work/'expected-rpm').read_text(), 'nodejs\nnpm\ngit\n')
            self.assertEqual((work/'commands').read_text(), 'sudo dnf5 check\n')
            calls = (work/'rpm-calls').read_text()
            self.assertIn('-q --whatprovides nodejs', calls)
            self.assertIn('-q --whatprovides npm', calls)
            self.assertNotIn('-q --whatprovides git', calls)

    def test_missing_requirements_install_once_then_accept_their_providers(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            result = self.invoke(work, '\npackages nodejs npm\npackages nodejs npm\nverify\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((work/'commands').read_text().splitlines(),
                             ['sudo dnf5 install nodejs npm', 'sudo dnf5 check'])

    def test_successful_dnf_without_an_installed_provider_still_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            result = self.invoke(work, '\npackages nodejs npm\n', INSTALL_PROVIDES='0')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Requested RPM was not installed: nodejs', result.stderr)
            self.assertFalse((work/'expected-rpm').exists())

    def test_final_verify_rejects_a_provider_removed_after_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work/'installed').touch()
            result = self.invoke(work, '\npackages nodejs npm\nrm "$RUN/installed"\nverify\n')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Missing RPM requirement: nodejs', result.stderr)
            self.assertFalse((work/'commands').exists())
