#!/usr/bin/env python3
"""Generate local launchers without invoking upstream's Omarchy-specific --default."""
from pathlib import Path
import sys

repair = sys.argv[1] == '--repair'
prefix, current = map(Path, sys.argv[2:] if repair else sys.argv[1:])
environment = '''#!/usr/bin/env bash
set -Eeuo pipefail
prefix=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
export FLEA_UI="$prefix/ui" FLEA_BIN="$prefix/libexec/flea"
export FLEA_GIO_AUTH="$prefix/libexec/flea-gio-auth" FLEA_MPRIS="$prefix/libexec/flea-mpris" FLEA_UDISKS="$prefix/libexec/flea-udisks"
'''


def desktop_quote(path):
    value = str(path)
    if '\n' in value or '\r' in value:
        raise ValueError('Invalid desktop path')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\'+char)
    return '"'+value.replace('%', '%%')+'"'


entry = prefix/'share/applications/com.thisisgm.flea.desktop'
legacy = f'Exec={desktop_quote(current/"bin/flea")} --gui %f\n'
desktop_command = f'Exec=/usr/bin/env {desktop_quote(current/"bin/flea")} --gui %f\n'
if repair:
    text = entry.read_text()
    if text.count(legacy) == 1:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', dir=entry.parent, delete=False) as pending:
            pending.write(text.replace(legacy, desktop_command))
        Path(pending.name).replace(entry)
    raise SystemExit(0)

for name, command in [('flea', '"$prefix/libexec/flea"'),
                      ('flea-filemanager1', 'python3 "$prefix/libexec/flea-filemanager1"')]:
    target = prefix/'bin'/name
    target.write_text(environment+'exec '+command+' "$@"\n')
    target.chmod(0o755)


(prefix/'share/applications/com.thisisgm.flea.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=Flea\nGenericName=File Manager\n'
    f'{desktop_command}'
    f'Icon={current}/share/applications/flea.svg\nTerminal=false\n'
    'Categories=System;FileTools;FileManager;\nMimeType=inode/directory;\nStartupWMClass=com.thisisgm.flea\n')

service = prefix/'share/dbus-1/services/org.freedesktop.FileManager1.service'
service.parent.mkdir(parents=True, exist_ok=True)
service.write_text('# Fedora Post-Install: managed Flea FileManager1\n[D-BUS Service]\n'
                   'Name=org.freedesktop.FileManager1\n'
                   f'Exec={desktop_quote(current/"bin/flea-filemanager1")}\n')
