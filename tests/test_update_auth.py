import contextlib
import importlib.util
import io
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch
import fcntl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('update_auth_manager', ROOT / 'scripts/update-manager.py')
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdateAuthentication(unittest.TestCase):
    def result(self, code=0, password=''):
        return subprocess.CompletedProcess([], code, '', password)

    def test_cached_authentication_needs_no_password_dialog(self):
        with patch.object(update.subprocess, 'run', return_value=self.result()) as command, \
                patch('builtins.open') as terminal:
            update.authenticate()
        terminal.assert_not_called()
        self.assertEqual(command.call_args.args[0], ['sudo', '-n', '-v'])

    def test_password_dialog_uses_pipe_and_never_prints_secret(self):
        secret = 'test-only password with spaces '
        output = io.StringIO()
        with patch.dict(os.environ, TERM='xterm'), \
                patch.object(update.shutil, 'which', return_value='/bin/whiptail'), \
                patch('builtins.open', return_value=contextlib.nullcontext(object())), \
                patch.object(update.subprocess, 'run', side_effect=[self.result(1), self.result(password=secret), self.result()]) as command, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            update.authenticate()
        self.assertNotIn(secret, output.getvalue())
        calls = command.call_args_list
        self.assertIn('--passwordbox', calls[1].args[0])
        self.assertEqual(calls[2].args[0], ['sudo', '-S', '-p', '', '-v'])
        self.assertEqual(calls[2].kwargs['input'], secret + '\n')
        self.assertTrue(all(secret not in arg for call in calls for arg in call.args[0]))

    def test_cancel_stops_before_checkpoint_or_update(self):
        with patch.dict(os.environ, TERM='xterm'), \
                patch.object(update.shutil, 'which', return_value='/bin/whiptail'), \
                patch('builtins.open', return_value=contextlib.nullcontext(object())), \
                patch.object(update.subprocess, 'run', side_effect=[self.result(1), self.result(1)]) as command, \
                patch.object(update.recovery, 'Lock', return_value=contextlib.nullcontext()), \
                patch.object(update.recovery, 'create') as checkpoint, \
                patch.object(update.subprocess, 'Popen') as engine:
            with self.assertRaisesRegex(RuntimeError, 'Anulowano'):
                update.execute()
        self.assertEqual(command.call_count, 2)
        checkpoint.assert_not_called()
        engine.assert_not_called()

    def test_no_terminal_has_clear_error_and_does_not_read_stdin(self):
        with patch.object(update.subprocess, 'run', return_value=self.result(1)) as command, \
                patch('builtins.open', side_effect=OSError('no tty')):
            with self.assertRaisesRegex(RuntimeError, 'Otwórz terminal'):
                update.authenticate()
        self.assertEqual(command.call_count, 1)

    def test_missing_whiptail_uses_native_sudo_on_the_terminal(self):
        terminal = contextlib.nullcontext()
        with patch.object(update.shutil, 'which', return_value=None), \
                patch('builtins.open', return_value=terminal), \
                patch.object(update.subprocess, 'run', side_effect=[self.result(1), self.result()]) as command, \
                contextlib.redirect_stdout(io.StringIO()):
            update.authenticate()
        self.assertEqual(command.call_args.args[0], ['sudo', '-v'])
        self.assertIs(command.call_args.kwargs['stdin'], terminal)
        self.assertIs(command.call_args.kwargs['stderr'], terminal)

    def test_wrong_password_is_limited_to_three_dialogs(self):
        results = [self.result(1)]
        for _ in range(3):
            results.extend([self.result(password='wrong-test-password'), self.result(1)])
        with patch.dict(os.environ, TERM='xterm'), \
                patch.object(update.shutil, 'which', return_value='/bin/whiptail'), \
                patch('builtins.open', return_value=contextlib.nullcontext()), \
                patch.object(update.subprocess, 'run', side_effect=results) as command:
            with self.assertRaisesRegex(RuntimeError, 'Nie potwierdzono'):
                update.authenticate()
        self.assertEqual(command.call_count, 7)

    def run_pty(self, code, env, send_on=None, keys=b''):
        pid, fd = pty.fork()
        if pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            os.execve(sys.executable, [sys.executable, '-c', code], env)
        output = b''
        sent = False
        status = None
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if select.select([fd], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                    if send_on and send_on in output and not sent:
                        os.write(fd, keys)
                        sent = True
                waited, child_status = os.waitpid(pid, os.WNOHANG)
                if waited:
                    status = child_status
                    break
            else:
                self.fail('PTY test timed out')
            if status is None:
                _, status = os.waitpid(pid, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0, output.decode(errors='replace'))
            return output
        finally:
            os.close(fd)
            if status is None:
                try:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(shutil.which('whiptail'), 'real password dialog requires whiptail')
    def test_real_password_box_in_pty_hides_input_and_authenticates(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / 'sudo'
            binary.write_text('''#!/usr/bin/env python3
import sys
if sys.argv[1:]==['-n','-v']: sys.exit(1)
assert sys.argv[1:]==['-S','-p','','-v']
assert sys.stdin.readline()=='fixture-secret-8271\\n'
''')
            binary.chmod(0o755)
            code = f'import runpy; m=runpy.run_path({str(ROOT / "scripts/update-manager.py")!r}); m["authenticate"](); print("AUTH_OK")'
            output = self.run_pty(code, dict(os.environ, TERM='xterm', PATH=temp + ':' + os.environ['PATH'],
                                           PYTHONPATH=str(ROOT / 'scripts')),
                                  send_on=b'Podaj has', keys=b'fixture-secret-8271\r')
            self.assertIn(b'AUTH_OK', output)
            self.assertNotIn(b'fixture-secret-8271', output)

    def test_real_update_child_keeps_controlling_terminal_and_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(ROOT / 'scripts/update-manager.py', root / 'update-manager.py')
            (root / 'update-actions.sh').write_text('''#!/bin/bash
python3 - <<'PY'
import os
with open('/dev/tty','rb',buffering=0): pass
assert os.getsid(0)==int(os.environ['EXPECTED_UPDATE_SESSION'])
assert os.getpgrp()!=int(os.environ['EXPECTED_UPDATE_PGRP'])
print('::fedora-stage::[1/1] controlling terminal retained')
PY
''')
            code = f'''
import os, runpy
os.environ['EXPECTED_UPDATE_SESSION']=str(os.getsid(0))
os.environ['EXPECTED_UPDATE_PGRP']=str(os.getpgrp())
m=runpy.run_path({str(root / 'update-manager.py')!r})
g=m['execute'].__globals__
g['authenticate']=lambda: None
g['rpm_inventory']=lambda: {{}}
g['snapshot']=lambda: None
g['reboot_status']=lambda: 'unknown'
m['execute']()
print('UPDATE_TTY_OK')
'''
            output = self.run_pty(code, dict(os.environ, HOME=temp, TERM='xterm',
                                           PYTHONPATH=str(ROOT / 'scripts'), XDG_CONFIG_HOME=temp+'/config',
                                           XDG_STATE_HOME=temp+'/state', XDG_DATA_HOME=temp+'/data'))
            self.assertIn(b'UPDATE_TTY_OK', output)
            self.assertIn(b'controlling terminal retained', output)


if __name__ == '__main__':
    unittest.main()
