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
    log 'DMS starts only through Hyprland, not a global user service. Existing DMS profiles are retained.'
    log 'DMS provides its own Polkit agent; the Hyprland selector does not start polkit-kde for DMS.'
}
