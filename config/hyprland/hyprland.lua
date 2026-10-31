-- Hyprland >=0.55. Noctalia v5. Keep this file user-owned.
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
-- Monitor auto-detection and scale retain compositor defaults. Configure in Noctalia.
hl.bind("SUPER+Q", hl.dsp.exec_cmd("hyprctl dispatch killactive"))
hl.bind("SUPER+F", hl.dsp.exec_cmd("hyprctl dispatch fullscreen 0"))
for i = 1, 9 do
    hl.bind("SUPER+" .. i, hl.dsp.exec_cmd("hyprctl dispatch workspace " .. i))
    hl.bind("SUPER+SHIFT+" .. i, hl.dsp.exec_cmd("hyprctl dispatch movetoworkspace " .. i))
end
