#!/usr/bin/env bash
module_dms() {
    local available
    if ! rpm -q dms >/dev/null 2>&1; then
        available=$(sudo dnf5 -q repoquery --available dms) || return
        if [[ -z $available ]]; then
            source "$ROOT/modules/repositories.sh"
            log 'DMS (DankMaterialShell, now Dux Shell): review the upstream stable COPR and its runtime repository.'
            vendor_repo dms-copr "https://copr.fedorainfracloud.org/coprs/duxlabs/dms/repo/fedora-$VERSION_ID/duxlabs-dms-fedora-$VERSION_ID.repo"
        fi
    fi
    packages dms brightnessctl
    command -v dms >/dev/null || die 'The DMS executable is missing.'
    run dms version
    select_shell dms
    prepare_dms_includes
    local main=$CONFIG/hypr/hyprland.lua
    if [[ -f $main ]]; then
        python3 "$ROOT/scripts/dms-includes.py" "$main" "$ROOT/config/hyprland/hyprland.lua" "$RUN/hyprland.lua"
        if ! cmp -s "$main" "$RUN/hyprland.lua"; then
            cp -- "$main" "$RUN/hyprland-before-dms-includes.lua"
            source "$ROOT/modules/hyprland.sh"
            validate_hyprland_config
            atomic_config "$RUN/hyprland.lua" "$main"
        fi
    fi
    log 'DMS starts only through Hyprland, not a global user service. Existing DMS profiles are retained.'
    log 'DMS provides its own Polkit agent; the Hyprland selector does not start polkit-kde for DMS.'
    source "$ROOT/modules/terminal-theme.sh"
    module_terminal_theme
    source "$ROOT/modules/app-theme.sh"
    module_app_theme
}
