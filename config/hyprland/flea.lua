-- Override only the selected file-manager shortcut; preserve all other user binds.
hl.unbind("SUPER + SHIFT + F")
hl.unbind("SHIFT + SUPER + F")
hl.unbind("SUPER + SHIFT + code:41")
hl.unbind("SHIFT + SUPER + code:41")
hl.bind("SUPER + SHIFT + F", hl.dsp.exec_cmd("$HOME/.local/bin/flea --gui"), { description = "Flea: file manager" })
