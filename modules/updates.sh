#!/usr/bin/env bash
module_updates() {
    local dest=$HOME/.local/share/fedora-postinstall
    mkdir -p "$dest/data" "$dest/scripts" "$HOME/.local/bin"
    install -m 755 "$ROOT/scripts/vendor-apps.py" "$dest/scripts/vendor-apps.py"
    install -m 755 "$ROOT/scripts/symbols-fonts.py" "$dest/scripts/symbols-fonts.py"
    install -m 644 "$ROOT/data/omasnap-release" "$dest/data/omasnap-release"
    install -m 755 "$ROOT/scripts/omasnap-manager" "$dest/scripts/omasnap-manager"
    install -m 755 "$ROOT/scripts/fedora-update" "$HOME/.local/bin/fedora-update"
    install -m 644 "$ROOT/data/hyprmod-revision" "$dest/data/hyprmod-revision"
    install -m 644 "$ROOT/data/flea-release" "$dest/data/flea-release"
    for helper in flea-manager flea-build.sh flea-launchers.py flea-fedora-patch.py validate-flea.py; do
        install -m 755 "$ROOT/scripts/$helper" "$dest/scripts/$helper"
    done
    log 'fedora-update installed into ~/.local/bin (add this directory to PATH if necessary).'
}
