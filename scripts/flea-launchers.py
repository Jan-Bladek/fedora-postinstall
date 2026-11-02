#!/usr/bin/env python3
"""Generate local launchers without invoking upstream's Omarchy-specific --default."""
from pathlib import Path
import sys

prefix, current = map(Path, sys.argv[1:])
environment = '''#!/usr/bin/env bash
set -Eeuo pipefail
prefix=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
export FLEA_UI="$prefix/ui" FLEA_BIN="$prefix/libexec/flea"
export FLEA_GIO_AUTH="$prefix/libexec/flea-gio-auth" FLEA_MPRIS="$prefix/libexec/flea-mpris" FLEA_UDISKS="$prefix/libexec/flea-udisks"
'''
for name, command in [('flea', '"$prefix/libexec/flea"'),
                      ('flea-filemanager1', 'python3 "$prefix/libexec/flea-filemanager1"')]:
    target = prefix/'bin'/name
    target.write_text(environment+'exec '+command+' "$@"\n')
    target.chmod(0o755)


def desktop_quote(path):
    value = str(path)
    if '\n' in value or '\r' in value:
        raise ValueError('Invalid desktop path')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\'+char)
    return '"'+value.replace('%', '%%')+'"'


(prefix/'share/applications/com.thisisgm.flea.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=Flea\nGenericName=File Manager\n'
    f'Exec={desktop_quote(current/"bin/flea")} --gui %f\n'
    f'Icon={current}/share/applications/flea.svg\nTerminal=false\n'
    'Categories=System;FileTools;FileManager;\nMimeType=inode/directory;\nStartupWMClass=com.thisisgm.flea\n')

service = prefix/'share/dbus-1/services/org.freedesktop.FileManager1.service'
service.parent.mkdir(parents=True, exist_ok=True)
service.write_text('# Fedora Post-Install: managed Flea FileManager1\n[D-BUS Service]\n'
                   'Name=org.freedesktop.FileManager1\n'
                   f'Exec={desktop_quote(current/"bin/flea-filemanager1")}\n')
