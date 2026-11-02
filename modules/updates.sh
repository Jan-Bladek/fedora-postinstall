#!/usr/bin/env bash
module_updates() {
    local dest=$HOME/.local/share/fedora-postinstall
    mkdir -p "$dest/data" "$dest/scripts" "$HOME/.local/bin"
    install -m 755 "$ROOT/scripts/vendor-apps.py" "$dest/scripts/vendor-apps.py"
    install -m 755 "$ROOT/scripts/symbols-fonts.py" "$dest/scripts/symbols-fonts.py"
    install -m 644 "$ROOT/data/omasnap-release" "$dest/data/omasnap-release"
    install -m 755 "$ROOT/scripts/omasnap-manager" "$dest/scripts/omasnap-manager"
    install -m 755 "$ROOT/scripts/fedora-update" "$HOME/.local/bin/fedora-update"
    log 'fedora-update installed into ~/.local/bin (add this directory to PATH if necessary).'
}
