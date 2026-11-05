#!/usr/bin/env bash
module_updates() {
    local dest=$HOME/.local/share/fedora-postinstall
    mkdir -p "$dest/data" "$dest/scripts" "$HOME/.local/bin"
    install -m 755 "$ROOT/scripts/vendor-apps.py" "$dest/scripts/vendor-apps.py"
    install -m 755 "$ROOT/scripts/symbols-fonts.py" "$dest/scripts/symbols-fonts.py"
    install -m 644 "$ROOT/data/omasnap-release" "$dest/data/omasnap-release"
    install -m 644 "$ROOT/data/omasnap-pin-cleanup-test.patch" "$dest/data/omasnap-pin-cleanup-test.patch"
    install -m 755 "$ROOT/scripts/omasnap-manager" "$dest/scripts/omasnap-manager"
    install -m 755 "$ROOT/scripts/fedora-update" "$HOME/.local/bin/fedora-update"
    install -m 644 "$ROOT/data/hyprmod-revision" "$dest/data/hyprmod-revision"
    install -m 644 "$ROOT/data/flea-release" "$dest/data/flea-release"
    for helper in flea-manager flea-build.sh flea-launchers.py flea-fedora-patch.py validate-flea.py; do
        install -m 755 "$ROOT/scripts/$helper" "$dest/scripts/$helper"
    done
    install -m 755 "$ROOT/scripts/zsh-manager.py" "$dest/scripts/zsh-manager.py"
    install -m 644 "$ROOT/data/zsh-sources.json" "$dest/data/zsh-sources.json"
    install -m 644 "$ROOT/config/zsh/init.zsh" "$dest/data/zsh-init.zsh"
    for helper in recovery.py update-manager.py update-actions.sh; do
        install -m 755 "$ROOT/scripts/$helper" "$dest/scripts/$helper"
    done
    install -m 755 "$ROOT/scripts/fedora-restore" "$HOME/.local/bin/fedora-restore"
    log 'fedora-update installed into ~/.local/bin (add this directory to PATH if necessary).'
}
