#!/usr/bin/env python3
"""Replace only our explicitly requested setting block; keep other user lines."""
from pathlib import Path
import sys
source, patch, destination = map(Path, sys.argv[1:4])
name = sys.argv[4]
begin, end = f'# BEGIN FEDORA-POSTINSTALL {name}', f'# END FEDORA-POSTINSTALL {name}'
text = source.read_text() if source.exists() else ''
if begin in text:
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
        raise ValueError('Ambiguous managed block; refusing to overwrite')
    start, stop = text.index(begin), text.index(end)+len(end)
    text = text[:start]+text[stop:].lstrip('\n')
destination.write_text(text.rstrip()+'\n\n'+begin+'\n'+patch.read_text().rstrip()+'\n'+end+'\n')
