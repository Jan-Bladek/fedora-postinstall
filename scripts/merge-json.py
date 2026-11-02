#!/usr/bin/env python3
"""Merge requested settings, accepting JSONC without interpreting any code."""
import json
from pathlib import Path
import re
import sys


def read_jsonc(text):
    token = r'("(?:[^"\\]|\\.)*")'
    text = re.sub(token+r'|//[^\n]*|/\*[\s\S]*?\*/', lambda m: m.group(1) or '', text)
    text = re.sub(token+r'|,(?=\s*[}\]])', lambda m: m.group(1) or '', text)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError('Settings must be a JSON object')
    return value


if __name__ == '__main__':
    source, patch, destination = map(Path, sys.argv[1:])
    value = read_jsonc(source.read_text()) if source.exists() else {}
    value.update(json.loads(patch.read_text()))
    destination.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
