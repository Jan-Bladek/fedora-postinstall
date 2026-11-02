import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Flea(unittest.TestCase):
    def test_launcher_uses_private_qml_and_preserves_directory_arguments(self):
        with tempfile.TemporaryDirectory(prefix='flea space ') as temporary:
            work = Path(temporary)
            prefix = work/'payload'
            (prefix/'bin').mkdir(parents=True)
            (prefix/'libexec').mkdir()
            (prefix/'share/applications').mkdir(parents=True)
            current = work/'current'
            current.symlink_to('payload')
            subprocess.run(['python3', str(ROOT/'scripts/flea-launchers.py'), str(prefix), str(current)], check=True)
            backend = prefix/'libexec/flea'
            backend.write_text('#!/usr/bin/env python3\nimport json, os, sys\nprint(json.dumps([sys.argv[1:], os.environ["FLEA_UI"], os.environ["FLEA_BIN"]]))\n')
            backend.chmod(0o755)
            result = subprocess.run([str(current/'bin/flea'), '--gui', '/tmp/folder with spaces'],
                                    capture_output=True, text=True, check=True)
            args, ui, binary = json.loads(result.stdout)
            self.assertEqual(args, ['--gui', '/tmp/folder with spaces'])
            self.assertEqual(ui, str(prefix/'ui'))
            self.assertEqual(binary, str(backend))
            desktop = (prefix/'share/applications/com.thisisgm.flea.desktop').read_text()
            self.assertIn('--gui %f', desktop)
            self.assertIn('MimeType=inode/directory;', desktop)
            self.assertNotIn('omarchy', desktop)

    def test_source_fetch_failure_keeps_payload_and_previous_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            app = work/'.local/share/fedora-postinstall/apps/flea'
            (app/'old').mkdir(parents=True)
            (app/'current').symlink_to('old')
            (work/'.config').mkdir()
            defaults = work/'.config/mimeapps.list'
            defaults.write_text('[Default Applications]\ninode/directory=old.desktop\n')
            shim = work/'bin'
            shim.mkdir()
            git = shim/'git'
            git.write_text('#!/bin/sh\nexit 42\n')
            git.chmod(0o755)
            result = subprocess.run([str(ROOT/'scripts/flea-manager'), 'install'],
                                    env=dict(os.environ, HOME=temporary, PATH=str(shim)+':'+os.environ['PATH']),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertEqual(os.readlink(app/'current'), 'old')
            self.assertIn('inode/directory=old.desktop', defaults.read_text())
            self.assertEqual(list(app.glob('.build.*')), [])

    def test_files_does_not_remove_nautilus_when_flea_installation_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = r'''source "$1/lib/core.sh"
source "$1/modules/files.sh"
ROOT=$1
RUN=$2
CONFIG=$2/config
flea_quickshell_ready() { return 0; }
packages() { :; }
run() {
    if [[ $* == *'flea-manager install' ]]; then return 42; fi
    if [[ $* == *xdg-mime* || $* == *'rpm -e'* ]]; then echo FORBIDDEN_MUTATION; exit 99; fi
}
module_files
'''
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), temporary],
                                    env=dict(os.environ, HOME=temporary), text=True, capture_output=True)
            self.assertEqual(result.returncode, 42, result.stdout+result.stderr)
            self.assertNotIn('FORBIDDEN_MUTATION', result.stdout+result.stderr)

    def test_update_never_fetches_an_unselected_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([str(ROOT/'scripts/flea-manager'), 'update'],
                                    env=dict(os.environ, HOME=temporary), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_optional_ci_token_is_api_only_and_is_not_forwarded_on_redirect(self):
        import runpy
        from unittest.mock import patch
        from urllib.request import HTTPRedirectHandler
        fetch = runpy.run_path(str(ROOT/'scripts/vendor-apps.py'))['fetch']
        captured = []
        class Response:
            def __init__(self, request):
                self.url = request.full_url
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{}'
        def open_fixture(request, timeout):
            captured.append(request)
            return Response(request)
        fetch.__globals__['urlopen'] = open_fixture
        with patch.dict(os.environ, FEDORA_POSTINSTALL_GITHUB_TOKEN='fake-ci-token'):
            fetch('https://api.github.com/repos/owner/repo/releases/latest')
            fetch('https://github.com/owner/repo/releases/download/v1/file.zip')
        self.assertEqual(captured[0].get_header('Authorization'), 'Bearer fake-ci-token')
        self.assertIsNone(captured[1].get_header('Authorization'))
        redirected = HTTPRedirectHandler().redirect_request(captured[0], None, 302, 'Found', {},
                                                             'https://github.com/owner/repo')
        self.assertIsNone(redirected.get_header('Authorization'))

    def test_legacy_launcher_repair_keeps_custom_fields_and_wrapper(self):
        with tempfile.TemporaryDirectory(prefix='flea repair ') as temporary:
            prefix = Path(temporary)
            (prefix/'bin').mkdir()
            (prefix/'share/applications').mkdir(parents=True)
            generator = ROOT/'scripts/flea-launchers.py'
            subprocess.run(['python3', str(generator), str(prefix), str(prefix)], check=True)
            entry = prefix/'share/applications/com.thisisgm.flea.desktop'
            entry.write_text(entry.read_text().replace('Exec=/usr/bin/env ', 'Exec=').replace('Name=Flea\n', 'Name=My Flea\n'))
            wrapper = (prefix/'bin/flea').read_bytes()
            for _ in range(2):
                subprocess.run(['python3', str(generator), '--repair', str(prefix), str(prefix)], check=True)
            self.assertIn('Name=My Flea\n', entry.read_text())
            self.assertIn('Exec=/usr/bin/env ', entry.read_text())
            self.assertEqual((prefix/'bin/flea').read_bytes(), wrapper)

    def test_real_generic_xdg_mime_reads_the_flea_default_with_spaces_in_home(self):
        import shutil
        if not shutil.which('xdg-mime'):
            self.skipTest('xdg-mime is unavailable')
        with tempfile.TemporaryDirectory(prefix='flea home ') as temporary:
            home = Path(temporary)
            (home/'.config').mkdir()
            prefix = home/'payload'
            (prefix/'bin').mkdir(parents=True)
            (prefix/'share/applications').mkdir(parents=True)
            applications = home/'.local/share/applications'
            applications.mkdir(parents=True)
            subprocess.run(['python3', str(ROOT/'scripts/flea-launchers.py'), str(prefix), str(prefix)], check=True)
            (applications/'com.thisisgm.flea.desktop').symlink_to(prefix/'share/applications/com.thisisgm.flea.desktop')
            env = dict(os.environ, HOME=temporary, XDG_CONFIG_HOME=str(home/'.config'),
                       XDG_DATA_HOME=str(home/'.local/share'), XDG_DATA_DIRS='/usr/local/share:/usr/share',
                       XDG_CURRENT_DESKTOP='', DESKTOP_SESSION='', XDG_SESSION_TYPE='tty', DE='generic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'KDE_FULL_SESSION', 'GNOME_DESKTOP_SESSION_ID'):
                env.pop(key, None)
            subprocess.run(['xdg-mime', 'default', 'com.thisisgm.flea.desktop', 'inode/directory'],
                           env=env, capture_output=True, text=True, check=True)
            result = subprocess.run(['xdg-mime', 'query', 'default', 'inode/directory'],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), 'com.thisisgm.flea.desktop', result.stderr)

    def test_fedora_patch_changes_only_lib64_and_refuses_unknown_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root/'src/backend/sandbox.rs'
            target.parent.mkdir(parents=True)
            original = 'const FLAGS = &[\n    "--unshare-all",\n    "--symlink",\n    "usr/lib",\n    "/lib64",\n    "--ro-bind",\n    "/usr",\n];\n'
            original += 'let a = Path::new("/etc/hostname");\nlet b = Path::new("/etc/hostname");\n'
            target.write_text(original)
            subprocess.run(['python3', str(ROOT/'scripts/flea-fedora-patch.py'), temporary],
                           capture_output=True, text=True, check=True)
            expected = original.replace('"usr/lib"', '"usr/lib64"').replace('/etc/hostname', '/etc/passwd')
            self.assertEqual(target.read_text(), expected)
            refusal = subprocess.run(['python3', str(ROOT/'scripts/flea-fedora-patch.py'), temporary],
                                     capture_output=True, text=True)
            self.assertNotEqual(refusal.returncode, 0)
            self.assertEqual(target.read_text(), expected)
