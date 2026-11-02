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
