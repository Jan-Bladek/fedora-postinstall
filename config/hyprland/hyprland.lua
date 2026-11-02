-- Hyprland >=0.55. Selected Noctalia / DMS shell. Keep this file user-owned.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.config({
    general = { gaps_in = 5, gaps_out = 10, border_size = 2, layout = "dwindle",
        col = { active_border = { colors = { "rgba(33ccffee)", "rgba(00ff99ee)" }, angle = 45 },
                inactive_border = "rgba(595959aa)" } },
    decoration = { rounding = 0, shadow = { enabled = false }, blur = { enabled = false } },
    group = { groupbar = { font_family = "JetBrains Mono" } },
    dwindle = { preserve_split = true, force_split = 2 },
    misc = { disable_hyprland_logo = true, disable_splash_rendering = true },
    input = { kb_layout = "pl", touchpad = { natural_scroll = true } },
})
hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE")
    hl.exec_cmd("$HOME/.local/share/fedora-postinstall/scripts/desktop-shell start")
end)
hl.bind("SUPER+Return", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER+B", hl.dsp.exec_cmd("brave-browser"))
hl.bind("SUPER+Space", hl.dsp.exec_cmd("$HOME/.local/share/fedora-postinstall/scripts/desktop-shell launcher"))
hl.bind("SUPER+CTRL+S", hl.dsp.exec_cmd("$HOME/.local/share/fedora-postinstall/scripts/desktop-shell panel"))
hl.bind("SUPER+comma", hl.dsp.exec_cmd("$HOME/.local/share/fedora-postinstall/scripts/desktop-shell settings"))
-- More specific monitor rules can be added through Noctalia settings.
hl.bind("SUPER+Q", hl.dsp.window.close())
hl.bind("SUPER+F", hl.dsp.window.fullscreen({ action = "toggle", mode = "fullscreen" }))
for i = 1, 10 do
    hl.bind("SUPER+code:" .. (i+9), hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER+SHIFT+code:" .. (i+9), hl.dsp.window.move({ workspace = i }))
end
for key, direction in pairs({ left = "l", right = "r", up = "u", down = "d" }) do
    hl.bind("SUPER+" .. key, hl.dsp.focus({ direction = direction }))
    hl.bind("SUPER+SHIFT+" .. key, hl.dsp.window.swap({ direction = direction }))
end
hl.bind("SUPER+mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER+mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Omarchy-style tiling and application keys, using Fedora applications.
hl.bind("SUPER+W", hl.dsp.window.close())
hl.bind("SUPER+T", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER+P", hl.dsp.window.pseudo())
hl.bind("SUPER+J", hl.dsp.layout("togglesplit"))
hl.bind("SUPER+S", hl.dsp.workspace.toggle_special("scratchpad"))
hl.bind("SUPER+ALT+S", hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }))
hl.bind("SUPER+Tab", hl.dsp.focus({ workspace = "e+1" }))
hl.bind("SUPER+SHIFT+Tab", hl.dsp.focus({ workspace = "e-1" }))
hl.bind("SUPER+CTRL+Tab", hl.dsp.focus({ workspace = "previous" }))
hl.bind("ALT+Tab", hl.dsp.window.cycle_next())
hl.bind("SUPER+SHIFT+Return", hl.dsp.exec_cmd("brave-browser"))
hl.bind("SUPER+SHIFT+B", hl.dsp.exec_cmd("brave-browser"))
hl.bind("SUPER+SHIFT+F", hl.dsp.exec_cmd("$HOME/.local/bin/flea --gui"))
hl.bind("SUPER+SHIFT+N", hl.dsp.exec_cmd("code"))
hl.bind("SUPER+mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind("SUPER+mouse_up", hl.dsp.focus({ workspace = "e-1" }))
hl.curve("easeOutQuint", { type = "bezier", points = { { 0.23, 1 }, { 0.32, 1 } } })
hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } })
hl.animation({ leaf = "windows", enabled = true, speed = 3.79, bezier = "easeOutQuint" })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.1, bezier = "easeOutQuint", style = "popin 87%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.49, bezier = "quick", style = "popin 87%" })
hl.animation({ leaf = "workspaces", enabled = false })

-- Load DMS-generated settings only for DMS. Keep this project's application binds.
local config_home = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
local selector = io.open(config_home .. "/fedora-postinstall/shell", "r")
local selected = selector and selector:read("*l") or "noctalia"
if selector then selector:close() end
if selected == "dms" then
    for _, name in ipairs({ "colors", "outputs", "layout", "cursor", "input", "windowrules" }) do
        local path = config_home .. "/hypr/dms/" .. name .. ".lua"
        local file = io.open(path, "r")
        if file then
            file:close()
            dofile(path)
        end
    end
end
