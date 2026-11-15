#!/usr/bin/env bash
module_laptop_keys() {
    [[ ${DESKTOP:-} != plasma ]] || die 'Laptop keys in this module require Hyprland.'
    local main=$CONFIG/hypr/hyprland.lua module=$CONFIG/hypr/fedora-postinstall-laptop-keys.lua
    local previous_module=$RUN/laptop-keys-before.lua
    [[ -f $main && ! -L $main && ! -L $module ]] || die 'Expected regular Hyprland configuration files.'
    packages brightnessctl wireplumber util-linux qalculate-gtk
    for tool in brightnessctl wpctl rfkill qalculate-gtk; do
        command -v "$tool" >/dev/null || die "Missing laptop-key tool: $tool"
    done
    install_shell_selector
    mkdir -p "$HOME/.local/bin"
    install -m 755 "$ROOT/scripts/fedora-laptop" "$HOME/.local/bin/fedora-laptop"
    cp -- "$main" "$RUN/hyprland-before-laptop-keys.lua"
    if [[ -f $module ]]; then cp -- "$module" "$previous_module"; fi
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$ROOT/config/hyprland/laptop-keys.lua" "$RUN/hyprland.lua" LAPTOP-KEYS
    source "$ROOT/modules/hyprland.sh"
    validate_hyprland_config
    atomic_config "$ROOT/config/hyprland/laptop-keys.lua" "$module"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$module" "$RUN/hyprland.lua" LAPTOP-KEYS
    atomic_config "$RUN/hyprland.lua" "$main"
    if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
        local errors
        if ! run hyprctl reload || ! errors=$(hyprctl configerrors) || [[ -n $errors ]]; then
            atomic_config "$RUN/hyprland-before-laptop-keys.lua" "$main"
            if [[ -f $previous_module ]]; then atomic_config "$previous_module" "$module"; fi
            run hyprctl reload || log 'Reload of restored configuration failed; check hyprctl configerrors.'
            run hyprctl configerrors || log 'Cannot query the restored session configuration.'
            die "Laptop-key configuration rejected; previous main configuration restored. ${errors:-}"
        fi
    fi
    log 'Laptop brightness/audio/microphone/radio/lock/calculator keys installed. Super+L also locks the selected shell.'
}
