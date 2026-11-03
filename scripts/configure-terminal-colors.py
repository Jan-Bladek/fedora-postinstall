#!/usr/bin/env python3
"""Preserve Noctalia TOML while enabling its shipped Kitty palette template."""
from pathlib import Path
import sys


def enable_noctalia(settings, effective):
    import tomlkit
    doc = tomlkit.parse(settings)
    resolved = tomlkit.parse(effective)
    templates = doc.setdefault('theme', {}).setdefault('templates', {})
    selected = list(resolved.get('theme', {}).get('templates', {}).get('builtin_ids', []))
    if 'kitty' not in selected:
        selected.append('kitty')
    templates['enable_builtin_templates'] = True
    templates['builtin_ids'] = selected
    return tomlkit.dumps(doc)


if __name__ == '__main__':
    settings, effective, output = map(Path, sys.argv[1:])
    output.write_text(enable_noctalia(settings.read_text() if settings.exists() else '', effective.read_text()))
