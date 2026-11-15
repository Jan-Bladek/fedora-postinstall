-- Laptop keys only: preserve application shortcuts, tiling and display profiles.
local command = '"$HOME/.local/bin/fedora-laptop" '
local function bind(key, action, description, repeat_key, locked)
    hl.unbind(key)
    hl.bind(key, hl.dsp.exec_cmd(command .. action), {
        description = description,
        repeating = repeat_key or false,
        locked = locked or false,
    })
end
bind("XF86AudioRaiseVolume", "volume-up", "Laptop: volume up", true, true)
bind("XF86AudioLowerVolume", "volume-down", "Laptop: volume down", true, true)
bind("XF86AudioMute", "mute", "Laptop: mute audio", false, true)
bind("XF86AudioMicMute", "mic-mute", "Laptop: mute microphone", false, true)
bind("XF86MonBrightnessUp", "brightness-up", "Laptop: brightness up", true, true)
bind("XF86MonBrightnessDown", "brightness-down", "Laptop: brightness down", true, true)
bind("XF86RFKill", "airplane", "Laptop: airplane mode")
bind("XF86WLAN", "airplane", "Laptop: airplane mode")
bind("XF86ScreenSaver", "lock", "Laptop: lock screen")
bind("SUPER+L", "lock", "Laptop: lock screen")
bind("XF86Calculator", "calculator", "Laptop: calculator")
