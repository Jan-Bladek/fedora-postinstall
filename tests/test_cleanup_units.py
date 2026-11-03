import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CleanupUnits(unittest.TestCase):
    def test_removal_stops_all_owned_user_activation_units_before_erasing(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            shim = work/'bin'
            shim.mkdir()
            rpm = shim/'rpm'
            rpm.write_text('''#!/bin/sh
case "$1" in
 -qa) echo qt6-qtbase; if [ ! -f "$UNIT_TEST_REMOVED" ]; then echo plasma-drkonqi; fi ;;
 -ql) printf '%s\\n' /usr/lib/systemd/user/drkonqi-coredump-cleanup.service /usr/lib/systemd/user/drkonqi-coredump-cleanup.timer /usr/lib/systemd/user/drkonqi-coredump-launcher.socket /usr/lib/systemd/user/drkonqi-coredump-launcher@.service /usr/lib/systemd/user/drkonqi-coredump-watch.path /usr/lib/systemd/user/timers.target.wants/drkonqi-coredump-cleanup.timer /usr/lib/systemd/system/NetworkManager.service ;;
 -q) echo plasma-drkonqi-6.8.2-1.fc44.x86_64 ;;
 *) exit 90 ;;
esac
''')
            rpm.chmod(0o755)
            script = r'''
source "$1/lib/core.sh"
source "$1/modules/cleanup.sh"
ROOT=$1
RUN=$2
CONFIG=$2/config
CLEANUP_APPS=crash-viewer
packages() { :; }
run() {
    printf '%s\n' "$*" >> "$RUN/commands"
    if [[ $* == 'sudo rpm -e plasma-drkonqi' ]]; then touch "$UNIT_TEST_REMOVED"; fi
}
systemctl() {
    case "$*" in
        '--user is-enabled --quiet '*|'--user is-active --quiet '*|'--user show-environment') return 0 ;;
        '--user is-failed --quiet drkonqi-coredump-cleanup.timer') return 0 ;;
        *) return 1 ;;
    esac
}
command() {
    if [[ $* == '-v flatpak' ]]; then return 1; fi
    builtin command "$@"
}
module_cleanup
'''
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temp],
                                    env=dict(os.environ, PATH=str(shim)+':'+os.environ['PATH'],
                                             UNIT_TEST_REMOVED=str(work/'removed')), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            commands = (work/'commands').read_text().splitlines()
            removed = commands.index('sudo rpm -e plasma-drkonqi')
            for name in ('drkonqi-coredump-cleanup.service', 'drkonqi-coredump-cleanup.timer',
                         'drkonqi-coredump-launcher.socket', 'drkonqi-coredump-watch.path'):
                stop = 'systemctl --user stop '+name
                self.assertEqual(commands.count(stop), 1)
                self.assertLess(commands.index(stop), removed)
            reset = 'systemctl --user reset-failed drkonqi-coredump-cleanup.timer'
            self.assertGreater(commands.index(reset), removed)
            self.assertFalse(any('NetworkManager' in line for line in commands))
            self.assertFalse(any('launcher@.service' in line for line in commands))
            self.assertEqual([line for line in commands if 'reset-failed' in line], [reset])
