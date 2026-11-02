#!/usr/bin/env bash
module_utilities() {
    flatpak_app md.obsidian.Obsidian
    flatpak_app org.localsend.localsend_app
    source "$ROOT/modules/repositories.sh"
    vendor_repo tailscale https://pkgs.tailscale.com/stable/fedora/tailscale.repo
    packages tailscale
    run sudo systemctl enable --now tailscaled
}
