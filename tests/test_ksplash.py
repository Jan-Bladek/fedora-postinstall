import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = '[D-BUS Service]\nName=org.kde.KSplash\nExec=/usr/bin/plasma_waitforname org.kde.KSplash\n'
FIXTURE = r'''
source "$1/lib/core.sh"
source "$1/modules/session-services.sh"
ROOT=$1
RUN=$2/run
CONFIG=$2/config
DESKTOP=$3
export XDG_DATA_HOME=$2/data
mkdir -p "$RUN" "$CONFIG"
run() { printf '%s\n' "$*" >> "$RUN/commands"; }
systemctl() {
    case "$*" in
        '--user show-environment') echo XDG_CURRENT_DESKTOP=Hyprland ;;
        '--user is-active --quiet fedora-ksplash-activation.service'|'--user is-failed --quiet fedora-ksplash-activation.service') return 1 ;;
        '--user list-units --failed --all --plain --no-legend '*)
            echo 'dbus-:1.2-org.kde.KSplash@2.service loaded failed failed Splash'
            echo 'app-imsettings-start.service loaded failed failed Other' ;;
        *) return 88 ;;
    esac
}
journalctl() { echo 'recorded old KSplash timeout'; }
configure_ksplash_activation "$2/vendor.service"
'''


class KSplash(unittest.TestCase):
    def run_guard(self, work, desktop='dms'):
        return subprocess.run(['bash', '-eu', '-c', FIXTURE, 'test', str(ROOT), str(work), desktop],
                              env=dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE='', WAYLAND_DISPLAY=''),
                              capture_output=True, text=True)

    def test_activation_is_guarded_and_only_previous_ksplash_failures_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work/'vendor.service').write_text(VENDOR)
            for _ in range(2):
                result = self.run_guard(work)
                self.assertEqual(result.returncode, 0, result.stderr)
            target = work/'data/dbus-1/services/org.kde.KSplash.service'
            self.assertIn('SystemdService=fedora-ksplash-activation.service', target.read_text())
            unit = (work/'config/systemd/user/fedora-ksplash-activation.service').read_text()
            self.assertIn('ExecCondition=/usr/bin/test "${XDG_CURRENT_DESKTOP}" != Hyprland', unit)
            self.assertIn('ExecStart=/usr/bin/plasma_waitforname org.kde.KSplash', unit)
            commands = (work/'run/commands').read_text().splitlines()
            resets = [c for c in commands if 'reset-failed' in c]
            self.assertEqual(resets, ['systemctl --user reset-failed dbus-:1.2-org.kde.KSplash@2.service']*2)
            self.assertNotIn('imsettings', '\n'.join(commands))
            self.assertEqual((work/'run/dbus-:1.2-org.kde.KSplash@2.service.journal').read_text(),
                             'recorded old KSplash timeout\n')

    def test_custom_user_activation_is_preserved_without_resetting_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work/'vendor.service').write_text(VENDOR)
            target = work/'data/dbus-1/services/org.kde.KSplash.service'
            target.parent.mkdir(parents=True)
            target.write_text('# user custom activation\n')
            result = self.run_guard(work)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(), '# user custom activation\n')
            self.assertTrue(target.with_name(target.name+'.fedora-postinstall-new').exists())
            self.assertFalse((work/'run/commands').exists())

    def test_plasma_profile_and_different_vendor_activation_are_untouched(self):
        for desktop, vendor in [('plasma', VENDOR), ('dms', VENDOR.replace('plasma_waitforname', 'some-new-helper'))]:
            with self.subTest(desktop=desktop), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                (work/'vendor.service').write_text(vendor)
                result = self.run_guard(work, desktop)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((work/'data').exists())
                self.assertFalse((work/'run/commands').exists())
