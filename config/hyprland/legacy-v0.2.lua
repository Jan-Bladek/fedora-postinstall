-- Hyprland >=0.55. Noctalia v5. Keep this file user-owned.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.config({
    general = { gaps_in = 4, gaps_out = 8, border_size = 2 },
    decoration = { rounding = 10, blur = { enabled = false } },
    input = { kb_layout = "pl", touchpad = { natural_scroll = true } },
})
hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE")
    hl.exec_cmd("noctalia")
    hl.exec_cmd("/usr/libexec/kf6/polkit-kde-authentication-agent-1")
end)
hl.bind("SUPER+Return", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER+B", hl.dsp.exec_cmd("brave-browser"))
hl.bind("SUPER+Space", hl.dsp.exec_cmd("noctalia msg panel-toggle launcher"))
hl.bind("SUPER+S", hl.dsp.exec_cmd("noctalia msg panel-toggle control-center"))
hl.bind("SUPER+comma", hl.dsp.exec_cmd("noctalia msg settings-toggle"))
-- More specific monitor rules can be added through Noctalia settings.
hl.bind("SUPER+Q", hl.dsp.window.close())
hl.bind("SUPER+F", hl.dsp.window.fullscreen({ action = "toggle", mode = "fullscreen" }))
for i = 1, 9 do
    hl.bind("SUPER+" .. i, hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER+SHIFT+" .. i, hl.dsp.window.move({ workspace = i }))
end
for _, direction in ipairs({ "left", "right", "up", "down" }) do
    hl.bind("SUPER+" .. direction, hl.dsp.focus({ direction = direction }))
end
hl.bind("SUPER+mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER+mouse:273", hl.dsp.window.resize(), { mouse = true })
