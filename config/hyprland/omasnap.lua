-- Loaded LAST: override only the two screenshot shortcuts, preserving other binds.
-- Do not exclude this layer from screen sharing: it breaks scrolling capture.
local binary = os.getenv("HOME") .. "/.local/bin/omasnap"
local file = io.open(binary, "rb")
if file then
    file:close()
    hl.unbind("PRINT")
    hl.unbind("SUPER + SHIFT + S")
    hl.bind("PRINT", hl.dsp.exec_cmd('"' .. binary .. '"'))
    hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd('"' .. binary .. '" --capture-region --editor overlay'))
    hl.layer_rule({ match = { namespace = "^omasnap$" }, no_anim = true, animation = "none" })
end
