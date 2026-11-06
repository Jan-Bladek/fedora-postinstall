import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FileManagerChoice(unittest.TestCase):
    def test_cli_saved_choice_override_and_invalid_input_are_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            config = home / '.config/fedora-postinstall'
            config.mkdir(parents=True)
            (config / 'file-manager').write_text('nautilus')
            env = dict(os.environ, HOME=folder, XDG_CONFIG_HOME=str(home / '.config'))
            for arguments, expected in [([], 'nautilus'), (['--file-manager', 'flea'], 'flea')]:
                result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--dry-run', '--modules', 'files', *arguments],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('file manager: ' + expected, result.stdout.splitlines()[0])
                self.assertEqual((config / 'file-manager').read_text(), 'nautilus')
            for value in ('bad', '$(touch NEVER_EXECUTE)'):
                result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--dry-run', '--file-manager', value],
                                        env=env, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Unknown file manager', result.stderr)
            self.assertFalse((ROOT / 'NEVER_EXECUTE').exists())

    def test_switch_changes_mime_dbus_and_saved_choice_preserving_original_service(self):
        script = r'''
ROOT=$1
source "$ROOT/lib/core.sh"
source "$ROOT/lib/files.sh"
source "$ROOT/modules/files.sh"
RUN=$HOME/run
CONFIG=$HOME/.config
mkdir -p "$RUN" "$HOME/.local/share/dbus-1/services" "$HOME/.local/share/fedora-postinstall/apps/flea/current/share/dbus-1/services"
printf 'original service\n' > "$HOME/.local/share/dbus-1/services/org.freedesktop.FileManager1.service"
printf '[D-BUS Service]\nName=org.freedesktop.FileManager1\nExec=flea-filemanager1\n' > "$HOME/.local/share/fedora-postinstall/apps/flea/current/share/dbus-1/services/org.freedesktop.FileManager1.service"
configure_flea_binding() { :; }
xdg-mime() {
    if [[ $1 == default ]]; then echo "$2" > "$RUN/mime"; else cat "$RUN/mime"; fi
}
for FILE_MANAGER in flea nautilus flea nautilus; do
    configure_file_manager "$FILE_MANAGER"
    [[ $(cat "$CONFIG/fedora-postinstall/file-manager") == "$FILE_MANAGER" ]]
    [[ $(cat "$RUN/mime") == "$(file_manager_desktop)" ]]
done
grep -q '^Exec=/usr/bin/nautilus --gapplication-service$' "$HOME/.local/share/dbus-1/services/org.freedesktop.FileManager1.service"
grep -q '^original service$' "$RUN/filemanager1-before.service"
'''
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                                    env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/.config'),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cleanup_keeps_selected_nautilus_for_all_and_explicit_selection(self):
        plan = runpy.run_path(str(ROOT / 'scripts/cleanup-plan.py'))['plan']
        installed = ['nautilus', 'dolphin', 'firefox', 'qt6-qtbase']
        for selection in (['all'], ['nautilus']):
            self.assertNotIn('nautilus', plan(selection, installed, file_manager='nautilus')['remove'])
        self.assertIn('nautilus', plan(['all'], installed, file_manager='flea')['remove'])
        with tempfile.TemporaryDirectory() as home:
            config = Path(home) / '.config/fedora-postinstall'
            config.mkdir(parents=True)
            (config / 'file-manager').write_text('nautilus\n')
            shim = Path(home) / 'bin'; shim.mkdir()
            (shim / 'rpm').write_text('#!/bin/sh\nprintf "nautilus\\ndolphin\\n"\n')
            (shim / 'rpm').chmod(0o755)
            result = subprocess.run(['python3', str(ROOT / 'scripts/cleanup-plan.py'), 'all'],
                                    env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config',
                                             PATH=str(shim)+':'+os.environ['PATH']), capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['remove'], ['dolphin'])

    def test_existing_flea_does_not_override_the_saved_nautilus_handler(self):
        script = r'''
source "$1/lib/core.sh"
source "$1/lib/files.sh"
mkdir -p "$HOME/.config/fedora-postinstall" "$HOME/.local/bin"
printf 'nautilus\n' > "$HOME/.config/fedora-postinstall/file-manager"
touch "$HOME/.local/bin/flea"; chmod +x "$HOME/.local/bin/flea"
[[ $(file_manager_desktop) == org.gnome.Nautilus.desktop ]]
'''
        with tempfile.TemporaryDirectory() as home:
            subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                           env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config'), check=True)

    def test_menu_selection_is_returned_before_any_installation(self):
        script = r'''
source "$1/lib/core.sh"
source "$1/lib/files.sh"
source "$1/lib/ui.sh"
whiptail() { printf 'nautilus\n' >&2; }
ui_file_manager_choice
[[ $FILE_MANAGER == nautilus ]]
'''
        with tempfile.TemporaryDirectory() as home:
            subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                           env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config'), check=True)


if __name__ == '__main__':
    unittest.main()
