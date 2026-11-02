#!/usr/bin/env python3
"""Hide one launcher entry without removing the uwsm session manager."""
from pathlib import Path
import os
import sys
config = Path(sys.argv[1])
source = Path('/usr/share/applications/uuctl.desktop')
dest = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'applications/uuctl.desktop'
if source.exists():
    text = source.read_text()
    lines = [line for line in text.splitlines() if not line.startswith('NoDisplay=')]
    lines.insert(lines.index('[Desktop Entry]')+1, 'NoDisplay=true')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and 'X-Fedora-Postinstall-Hidden=true' not in dest.read_text():
        dest = dest.with_name(dest.name+'.fedora-postinstall-new')
    dest.write_text('\n'.join(lines)+'\nX-Fedora-Postinstall-Hidden=true\n')
