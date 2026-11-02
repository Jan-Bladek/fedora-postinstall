-- Loaded LAST: override only the two screenshot shortcuts, preserving other binds.
-- Do not exclude this layer from screen sharing: it breaks scrolling capture.
local binary = os.getenv("HOME") .. "/.local/bin/omasnap"
local file = io.open(binary, "rb")
if file then
    file:close()
    hl.unbind("PRINT")
    hl.unbind("SUPER + SHIFT + S")
    hl.unbind("SHIFT + SUPER + S")
    hl.unbind("code:107") -- physical Print (evdev SysRq + 8)
    hl.unbind("SUPER + SHIFT + code:39") -- physical S on the shipped PL layout
    hl.unbind("SHIFT + SUPER + code:39")
    hl.bind("PRINT", hl.dsp.exec_cmd('"' .. binary .. '"'), { description = "Omasnap: capture" })
    hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd('"' .. binary .. '" --capture-region --editor overlay'), { description = "Omasnap: edit region" })
    hl.layer_rule({ match = { namespace = "^omasnap$" }, no_anim = true, animation = "none" })
end
