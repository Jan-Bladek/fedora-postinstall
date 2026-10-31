#!/usr/bin/env bash
module_hyprland() {
    local available version
    if ! rpm -q hyprland >/dev/null 2>&1; then
        # Reuse the system package cache populated by the dependencies module.
        # A failed query aborts; only a successful empty result offers COPR.
        available=$(sudo dnf5 -q repoquery --available hyprland)
        if [[ -z $available ]]; then
            source "$ROOT/modules/repositories.sh"
            log 'Native Hyprland unavailable. Noctalia docs list this community COPR; review required.'
            vendor_repo hyprland-copr "https://copr.fedorainfracloud.org/coprs/lionheartp/Hyprland/repo/fedora-$VERSION_ID/lionheartp-Hyprland-fedora-$VERSION_ID.repo"
        fi
    fi
    # No implicit allowerasing or distribution synchronization.
    packages hyprland xorg-x11-server-Xwayland xdg-desktop-portal-hyprland xdg-desktop-portal-gtk pipewire pipewire-pulseaudio wireplumber polkit-kde NetworkManager bluez sddm mesa-dri-drivers mesa-vulkan-drivers
    [[ -x /usr/libexec/kf6/polkit-kde-authentication-agent-1 ]] || die 'Fedora KDE Polkit agent executable is missing.'
    version=$(Hyprland --version)
    version=${version%%$'\n'*}
    log "$version"
    [[ $version =~ 0\.([0-9]+) && ${BASH_REMATCH[1]} -ge 55 ]] || die 'Lua config requires Hyprland >=0.55; no configuration was replaced.'
    config_file "$ROOT/config/hyprland/hyprland.lua" "$CONFIG/hypr/hyprland.lua"
    config_file "$ROOT/config/portals.conf" "$CONFIG/xdg-desktop-portal/hyprland-portals.conf"
    run sudo systemctl enable --now NetworkManager bluetooth
    if ! systemctl is-enabled display-manager.service >/dev/null 2>&1; then run sudo systemctl enable sddm; fi
    log 'Existing display manager retained. Select Hyprland at next login.'
}
