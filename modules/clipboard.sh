#!/usr/bin/env bash
module_clipboard() {
    [[ ${DESKTOP:-} != plasma ]] || die 'The clipboard shortcut requires Hyprland.'
    local main=$CONFIG/hypr/hyprland.lua module=$CONFIG/hypr/fedora-postinstall-clipboard.lua
    [[ -f $main ]] || die 'Install Hyprland before configuring clipboard history.'
    packages kitty cliphist wl-clipboard fzf
    mkdir -p "$HOME/.local/bin"
    install -m 755 "$ROOT/scripts/clipboard-history" "$HOME/.local/bin/clipboard-history"
    config_file "$ROOT/config/systemd/user/fedora-clipboard.service" "$CONFIG/systemd/user/fedora-clipboard.service"
    install_shell_selector
    cp -- "$main" "$RUN/hyprland-before-clipboard.lua"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$ROOT/config/hyprland/clipboard.lua" "$RUN/hyprland.lua" CLIPBOARD
    source "$ROOT/modules/hyprland.sh"
    validate_hyprland_config
    atomic_config "$ROOT/config/hyprland/clipboard.lua" "$module"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$module" "$RUN/hyprland.lua" CLIPBOARD
    atomic_config "$RUN/hyprland.lua" "$main"
    if systemctl --user show-environment >/dev/null 2>&1; then
        run systemctl --user daemon-reload
        if [[ -n ${WAYLAND_DISPLAY:-} ]]; then run "$HOME/.local/bin/clipboard-history" start; fi
    fi
    log 'Super+Shift+V opens clipboard history. Tab/arrows select; Enter copies; Esc cancels. Collector starts only inside Hyprland.'
}
