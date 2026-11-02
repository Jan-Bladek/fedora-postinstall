#!/usr/bin/env python3
"""Adapt upstream's Arch library symlink inside bubblewrap to Fedora's layout."""
from pathlib import Path
import sys

source = Path(sys.argv[1])/'src/backend/sandbox.rs'
text = source.read_text()
before = '    "usr/lib",\n    "/lib64",'
after = '    "usr/lib64",\n    "/lib64",'
if text.count(before) != 1:
    raise ValueError('Unknown upstream sandbox layout; refusing an unreviewed patch')
probe = 'Path::new("/etc/hostname")'
if text.count(probe) != 2:
    raise ValueError('Unknown upstream sandbox probe fixtures; review before patching')
# Static hostnames are optional on Fedora. Keep the same read-only bind and all
# resource assertions, using an existing regular file already covered by /etc.
source.write_text(text.replace(before, after).replace(probe, 'Path::new("/etc/passwd")'))
print('Fedora adaptation: /lib64 -> usr/lib64 inside the existing bubblewrap sandbox.')
