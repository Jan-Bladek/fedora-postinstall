#!/usr/bin/env python3
"""Apply only the installer's tiling policy to an existing Lua configuration."""
import argparse
import fcntl
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '-- BEGIN FEDORA-POSTINSTALL TILING'
END = '-- END FEDORA-POSTINSTALL TILING'


def merge(text, template):
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise ValueError('Niejednoznaczny blok TILING; konfiguracja pozostaje bez zmian.')
        start, stop = text.index(BEGIN), text.index(END) + len(END)
        text = text[:start] + text[stop:].lstrip('\n')
    block = template[template.index(BEGIN):template.index(END) + len(END)]
    return text.rstrip() + '\n\n' + block + '\n'


def apply():
    if os.geteuid() == 0:
        raise ValueError('Uruchom jako użytkownik pulpitu, bez sudo.')
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    main = config / 'hypr/hyprland.lua'
    if main.is_symlink() or not main.is_file():
        raise ValueError('Wymagany zwykły plik hypr/hyprland.lua; dowiązania nie są zastępowane.')
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'fedora-postinstall'
    state.mkdir(parents=True, exist_ok=True)
    helpers = runpy.run_path(str(ROOT / 'scripts/fedora-display'))
    # Serialize with HDR profile changes, which also edit the same Lua file.
    with (state / 'display.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old = main.read_bytes()
        mode = main.stat().st_mode & 0o777
        proposed = merge(old.decode(), (ROOT / 'config/hyprland/hyprland.lua').read_text())
        profile = config / 'fedora-postinstall/display-profile.lua'
        active = bool(os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'))
        if active and helpers['run']('hyprctl', 'configerrors'):
            raise RuntimeError('Najpierw napraw istniejące błędy hyprctl configerrors.')
        helpers['verify'](config, proposed, profile.read_text() if profile.is_file() else None)
        backup = Path(tempfile.mkdtemp(prefix='tiling-', dir=state)) / 'hyprland.lua'
        backup.write_bytes(old)
        try:
            helpers['atomic_write'](main, proposed.encode(), mode)
            if active:
                helpers['reload_config']()
        except Exception:
            helpers['atomic_write'](main, old, mode)
            if active:
                try:
                    helpers['reload_config']()
                except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                    print(f'Ponowne wczytanie przywróconej konfiguracji: {error}', file=sys.stderr)
            raise
    print('Dwindle aktywne: Super+Enter = terminal; Super+F = fullscreen; Super+Ctrl+F = menedżer plików.')
    print(f'Kopia poprzedniej konfiguracji: {backup}')
    if not active:
        print('Ustawienie zadziała przy następnym logowaniu do Hyprlanda.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        apply()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'configure-tiling: {error}', file=sys.stderr)
        sys.exit(1)
