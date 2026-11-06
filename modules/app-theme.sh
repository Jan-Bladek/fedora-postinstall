#!/usr/bin/env bash
configure_dms_lazyvim_theme() {
    [[ ${DESKTOP:-} == dms ]] || return 0
    local destination=$CONFIG/nvim/lua/plugins/fedora-dms-theme.lua
    [[ -f $CONFIG/nvim/.fedora-postinstall-lazyvim ]] || return 0
    mkdir -p "$(dirname "$destination")"
    if [[ -f $destination ]]; then cp -- "$destination" "$RUN/lazyvim-before-dms-theme.lua"; fi
    config_file "$ROOT/config/nvim/dms-theme.lua" "$destination"
}

module_app_theme() {
    [[ ${DESKTOP:-} == dms ]] || return 0
    packages matugen adw-gtk3-theme qt5-qtbase-gui qt6-qtbase-gui
    run python3 "$ROOT/scripts/dms-app-theme.py" prepare --config "$CONFIG" --backup "$RUN" \
        --data "${XDG_DATA_HOME:-$HOME/.local/share}"
    # Qt5 and Qt6 both use DMS's GTK colors; no global environment.d override
    # is written, so Plasma keeps its native platform theme.
    local main=$CONFIG/hypr/hyprland.lua
    if [[ -f $main ]]; then
        cp -- "$main" "$RUN/hyprland-before-dms-app-theme.lua"
        python3 "$ROOT/scripts/dms-theme-includes.py" "$main" > "$RUN/hyprland.lua"
        if ! cmp -s "$main" "$RUN/hyprland.lua"; then
            source "$ROOT/modules/hyprland.sh"
            validate_hyprland_config
            atomic_config "$RUN/hyprland.lua" "$main"
        fi
    fi
    if [[ -f $CONFIG/nvim/.fedora-postinstall-lazyvim ]]; then
        configure_dms_lazyvim_theme
        run timeout 600 nvim --headless '+Lazy! sync' '+lua require("lazyvim.config")' +qa
    fi
    run python3 "$ROOT/scripts/dms-app-theme.py" vscode --config "$CONFIG" --backup "$RUN" \
        --data "${XDG_DATA_HOME:-$HOME/.local/share}"
    log 'DMS application theming: GTK, Qt through GTK, managed LazyVim, VS Code and btop terminal colors. Log out and back into Hyprland to apply Qt environment.'
}
