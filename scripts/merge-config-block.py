#!/usr/bin/env python3
"""Replace only our explicitly requested setting block; keep other user lines."""
from pathlib import Path
import sys
import re
source, patch, destination = map(Path, sys.argv[1:4])
name = sys.argv[4]
begin, end = f'# BEGIN FEDORA-POSTINSTALL {name}', f'# END FEDORA-POSTINSTALL {name}'
text = source.read_text() if source.exists() else ''
if begin in text:
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
        raise ValueError('Ambiguous managed block; refusing to overwrite')
    start, stop = text.index(begin), text.index(end)+len(end)
    text = text[:start]+text[stop:].lstrip('\n')
if '--replace-keys' in sys.argv[5:]:
    keys = {re.match(r'\s*([A-Za-z_][A-Za-z_0-9]*)', line)[1]
            for line in patch.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')}
    text = ''.join(line for line in text.splitlines(keepends=True)
                   if not (match := re.match(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*=', line)) or match[1] not in keys)
destination.write_text(text.rstrip()+'\n\n'+begin+'\n'+patch.read_text().rstrip()+'\n'+end+'\n')
