import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SessionHealth(unittest.TestCase):
    def test_monitor_and_ipc_failures_cannot_pass_optimized_python(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            shim = work / 'bin'
            shim.mkdir()
            scripts = {
                'hyprctl': 'if [ "$1" = -j ]; then cat "$MONITOR_FIXTURE"; fi\n',
                'pgrep': 'exit 0\n',
                'systemctl': 'exit 0\n',
                'kitty': 'exit 0\n',
                'noctalia': 'echo PRIVATE_SESSION_STATUS; exit "$IPC_EXIT"\n',
            }
            for name, body in scripts.items():
                executable = shim / name
                executable.write_text('#!/bin/sh\n' + body)
                executable.chmod(0o755)
            fixture = work / 'monitors.json'
            display = work / 'wayland-test'
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(display))
                active = {'width': 1280, 'height': 800, 'dpmsStatus': True}
                cases = [([], '0', False), ([None], '0', False),
                         ([dict(active, disabled=True)], '0', False),
                         ([dict(active, dpmsStatus=False)], '0', False),
                         ([dict(active, width=0)], '0', False),
                         ([active], '44', False), ([active], '0', True)]
                for optimized in ('0', '1'):
                    for monitors, ipc_exit, expected in cases:
                        with self.subTest(optimized=optimized, monitors=monitors, ipc=ipc_exit):
                            fixture.write_text(json.dumps(monitors))
                            env = dict(os.environ, PATH=str(shim)+':'+os.environ['PATH'],
                                       XDG_RUNTIME_DIR=str(work), WAYLAND_DISPLAY=str(display),
                                       HYPRLAND_INSTANCE_SIGNATURE='fixture', PYTHONOPTIMIZE=optimized,
                                       MONITOR_FIXTURE=str(fixture), IPC_EXIT=ipc_exit)
                            result = subprocess.run([str(ROOT/'scripts/validate-session'), '--check-only'],
                                                    env=env, text=True, capture_output=True)
                            self.assertEqual(result.returncode == 0, expected, result.stderr)
                            self.assertNotIn('PRIVATE_SESSION_STATUS', result.stdout+result.stderr)
                            self.assertNotIn('manual session acceptance passed', result.stdout)
