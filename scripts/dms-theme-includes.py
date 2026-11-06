#!/usr/bin/env python3
"""Append a DMS-only Qt platform setup to an existing Hyprland Lua config."""
from pathlib import Path
import sys

BEGIN = '-- BEGIN FEDORA-POSTINSTALL DMS-APP-THEME'
END = '-- END FEDORA-POSTINSTALL DMS-APP-THEME'
BLOCK = '''-- BEGIN FEDORA-POSTINSTALL DMS-APP-THEME
do
    local config_home = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
    local file = io.open(config_home .. "/fedora-postinstall/shell", "r")
    local selected = file and file:read("*l") or "noctalia"
    if file then file:close() end
    if selected == "dms" then
        hl.env("QT_QPA_PLATFORMTHEME", "gtk3")
        hl.env("QT_QPA_PLATFORMTHEME_QT6", "gtk3")
    end
end
-- END FEDORA-POSTINSTALL DMS-APP-THEME
'''


def merge(text):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Invalid DMS application theme markers')
    if BEGIN in text:
        start, end = text.index(BEGIN), text.index(END) + len(END)
        if end < start:
            raise ValueError('Reversed DMS application theme markers')
        text = text[:start] + text[end:].lstrip('\n')
    return text.rstrip() + '\n\n' + BLOCK


if __name__ == '__main__':
    print(merge(Path(sys.argv[1]).read_text()), end='')
