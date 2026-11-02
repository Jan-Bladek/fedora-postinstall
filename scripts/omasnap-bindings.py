#!/usr/bin/env python3
"""Append one last-loaded Lua module; never parse/rewrite arbitrary user Lua."""
import json
from pathlib import Path
import sys


def merge(text, module, name='OMASNAP'):
    if name not in {'OMASNAP', 'FLEA', 'CLIPBOARD'}:
        raise ValueError('Unsupported managed Lua loader')
    begin = '-- BEGIN FEDORA-POSTINSTALL '+name
    end = '-- END FEDORA-POSTINSTALL '+name
    if begin in text or end in text:
        if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
            raise ValueError(f'Ambiguous {name} block: previous configuration retained')
        start, stop = text.index(begin), text.index(end)+len(end)
        text = text[:start]+text[stop:].lstrip('\n')
    # ensure_ascii=False avoids JSON \u escapes, which Lua does not accept.
    path = json.dumps(str(module), ensure_ascii=False)
    return text.rstrip()+f'\n\n{begin}\ndofile({path})\n{end}\n'


if __name__ == '__main__':
    source, module, destination = map(Path, sys.argv[1:4])
    destination.write_text(merge(source.read_text(), module, sys.argv[4] if len(sys.argv) > 4 else 'OMASNAP'))
