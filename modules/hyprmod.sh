#!/usr/bin/env bash
module_hyprmod() {
    [[ ${DESKTOP:-} != plasma ]] || die 'Hyprmod requires the Hyprland desktop.'
    packages uv git gtk4 libadwaita python3-devel gcc pkgconf-pkg-config cairo-devel cairo-gobject-devel gobject-introspection-devel
    local revision dest=$HOME/.local/share/fedora-postinstall
    revision=$(cat "$ROOT/data/hyprmod-revision")
    [[ $revision =~ ^[0-9a-f]{40}$ ]] || die 'Invalid Hyprmod revision.'
    run uv tool install --python /usr/bin/python3 "git+https://github.com/BlueManCZ/hyprmod.git@$revision"
    run "$HOME/.local/bin/hyprmod" --install
    mkdir -p "$STATE/managed" "$dest/data"
    printf '%s\n' "$revision" > "$STATE/managed/hyprmod"
    install -m 644 "$ROOT/data/hyprmod-revision" "$dest/data/hyprmod-revision"
    log 'Hyprmod installed from a reviewed upstream revision; no remote shell installer executed.'
}
