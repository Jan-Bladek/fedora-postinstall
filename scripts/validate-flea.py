#!/usr/bin/env python3
"""Load the actual GUI and await upstream's ready IPC in an isolated offscreen session."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def validate(prefix):
    with tempfile.TemporaryDirectory(prefix='flea-verify-') as temporary:
        work = Path(temporary)
        env = dict(os.environ)
        for key in ('WAYLAND_DISPLAY', 'DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'DBUS_SESSION_BUS_ADDRESS'):
            env.pop(key, None)
        for key, directory in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'),
                               ('XDG_STATE_HOME', 'state'), ('XDG_CACHE_HOME', 'cache'),
                               ('XDG_DATA_HOME', 'data'), ('XDG_RUNTIME_DIR', 'runtime')]:
            path = work/directory
            path.mkdir(mode=0o700)
            env[key] = str(path)
        env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   QT_QPA_PLATFORMTHEME='generic', QSG_RHI_BACKEND='opengl',
                   FLEA_BIN=str(prefix/'libexec/flea'), FLEA_UI=str(prefix/'ui'))
        with (work/'gui.log').open('w+') as log:
            process = subprocess.Popen(['qs', '-p', str(prefix/'ui/boot')], env=env,
                                       stdout=log, stderr=log, start_new_session=True)
            try:
                deadline = time.monotonic()+45
                while time.monotonic() < deadline and process.poll() is None:
                    ipc_env = dict(env)
                    ipc_env.pop('DISPLAY', None)
                    try:
                        ready = subprocess.run(['qs', 'ipc', '-p', str(prefix/'ui/boot'), 'call', 'flea', 'ready'],
                                               env=ipc_env, text=True, capture_output=True, timeout=3)
                    except subprocess.TimeoutExpired:
                        continue
                    if ready.returncode == 0 and ready.stdout.strip() == 'true':
                        print('Flea: actual Quickshell UI loaded; upstream ready IPC passed (offscreen).')
                        return
                    time.sleep(0.25)
                log.flush()
                log.seek(0)
                raise RuntimeError('Flea GUI validation failed; previous payload/default retained:\n'+log.read())
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()


if __name__ == '__main__':
    validate(Path(sys.argv[1]).resolve())
