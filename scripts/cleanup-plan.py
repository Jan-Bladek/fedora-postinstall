#!/usr/bin/env python3
"""Exact app allowlist; never infer deletion from translated application names."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def groups():
    result = {}
    for line in (ROOT/'data/cleanup.tsv').read_text().splitlines():
        if line and not line.startswith('#'):
            key, label, packages = line.split('\t')
            result[key] = (label, packages.split())
    return result


def plan(selected, installed):
    catalog = groups()
    keys = list(catalog) if selected == ['all'] else selected
    if not keys or set(keys) - catalog.keys():
        raise ValueError('Unknown or empty application selection')
    targets = set()
    for key in keys:
        for package in catalog[key][1]:
            if package == '@libreoffice':
                targets.update(p for p in installed if p == 'libreoffice' or p.startswith('libreoffice-'))
            elif not package.startswith('@') and package in installed:
                targets.add(package)
    return {'groups': keys, 'remove': sorted(targets), 'hide_uuctl': 'uuctl' in keys}


if __name__ == '__main__':
    if sys.argv[1:] == ['--catalog']:
        for key, (label, _) in groups().items():
            print(key+'\t'+label)
    else:
        installed = subprocess.check_output(['rpm', '-qa', '--qf', '%{NAME}\n'], text=True).splitlines()
        print(json.dumps(plan(sys.argv[1:], installed), indent=2))
