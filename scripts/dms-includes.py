#!/usr/bin/env python3
"""Migrate only the installer's known DMS include block; preserve user settings."""
from pathlib import Path
import sys

OLD = '''if selected == "dms" then
    for _, name in ipairs({ "colors", "outputs", "layout", "cursor", "input", "windowrules" }) do
        local path = config_home .. "/hypr/dms/" .. name .. ".lua"
        local file = io.open(path, "r")
        if file then
            file:close()
            dofile(path)
        end
    end
end'''


def migrate(text, template):
    new = template[template.index('if selected == "dms" then'):].rstrip()
    if text.count(OLD) == 1:
        return text.replace(OLD, new)
    return text


if __name__ == '__main__':
    source, template, target = map(Path, sys.argv[1:])
    target.write_text(migrate(source.read_text(), template.read_text()))
