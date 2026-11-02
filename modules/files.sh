#!/usr/bin/env bash
flea_quickshell_ready() {
    command -v qs >/dev/null || return 1
    qs --version | python3 -c 'import re,sys; m=re.search(r"Quickshell (\d+)\.(\d+)\.(\d+)",sys.stdin.read()); sys.exit(not (m and tuple(map(int,m.groups())) >= (0,3,1)))'
}
configure_flea_binding() {
    [[ ${DESKTOP:-} != plasma ]] || return 0
    local main=$CONFIG/hypr/hyprland.lua module=$CONFIG/hypr/fedora-postinstall-flea.lua
    if [[ ! -f $main ]]; then
        log 'No Hyprland Lua config present; add Super+Shift+F for ~/.local/bin/flea --gui manually.'
        return 0
    fi
    cp -- "$main" "$RUN/hyprland-before-flea.lua"
    if [[ -e $module ]]; then cp -- "$module" "$RUN/flea-bindings-before.lua"; fi
    cp -- "$ROOT/config/hyprland/flea.lua" "$RUN/flea-proposed.lua"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$RUN/flea-proposed.lua" "$RUN/hyprland.lua" FLEA
    source "$ROOT/modules/hyprland.sh"
    validate_hyprland_config
    atomic_config "$ROOT/config/hyprland/flea.lua" "$module"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$main" "$module" "$RUN/hyprland.lua" FLEA
    atomic_config "$RUN/hyprland.lua" "$main"
}
module_files() {
    local available dest=$HOME/.local/share/fedora-postinstall
    # Fedora 44's base Quickshell is too old for this upstream UI. Reuse the
    # already-reviewed Hyprland COPR only when no suitable RPM is available.
    if ! flea_quickshell_ready; then
        available=$(sudo dnf5 -q repoquery --available --qf '%{version}\n' quickshell)
        if ! printf '%s\n' "$available" | python3 -c 'import re,sys; versions=[tuple(map(int,m.groups())) for line in sys.stdin if (m:=re.match(r"^(\d+)\.(\d+)\.(\d+)", line))]; sys.exit(not any(v >= (0,3,1) for v in versions))'; then
            source "$ROOT/modules/repositories.sh"
            vendor_repo hyprland-copr "https://copr.fedorainfracloud.org/coprs/lionheartp/Hyprland/repo/fedora-$VERSION_ID/lionheartp-Hyprland-fedora-$VERSION_ID.repo"
        fi
        if rpm -q quickshell >/dev/null 2>&1; then run sudo dnf5 upgrade quickshell; else packages quickshell; fi
        flea_quickshell_ready || die 'Flea requires Quickshell >=0.3.1; defaults and Nautilus retained.'
    fi
    packages quickshell git gcc xdg-utils desktop-file-utils python3 python3-gobject \
        qt6-qtdeclarative qt6-qtmultimedia qt6-qtpdf qt6-qtsvg qt6-qtwayland \
        kf6-kimageformats libheif fontconfig hicolor-icon-theme shared-mime-info \
        bat jq bubblewrap expect udisks2 gvfs gvfs-afc gvfs-gphoto2 gvfs-mtp gvfs-nfs gvfs-smb \
        usbmuxd util-linux wl-clipboard xdg-terminal-exec libarchive
    if ! command -v cargo >/dev/null; then packages rust cargo; fi
    mkdir -p "$dest/scripts" "$dest/data" "$HOME/.local/bin"
    install -m 644 "$ROOT/data/flea-release" "$dest/data/flea-release"
    for helper in flea-manager flea-launchers.py validate-flea.py; do
        install -m 755 "$ROOT/scripts/$helper" "$dest/scripts/$helper"
    done
    if declare -F ui_status >/dev/null; then ui_status 'Flea: kompilacja Rust, testy upstream i kontrola GUI'; fi
    run "$dest/scripts/flea-manager" install
    run "$dest/scripts/flea-manager" check
    configure_flea_binding
    run xdg-mime default com.thisisgm.flea.desktop inode/directory
    [[ $(xdg-mime query default inode/directory) == com.thisisgm.flea.desktop ]] || die 'Flea default verification failed.'
    local service=$HOME/.local/share/dbus-1/services/org.freedesktop.FileManager1.service
    if [[ -e $service ]]; then cp -- "$service" "$RUN/filemanager1-before.service"; fi
    atomic_config "$dest/apps/flea/current/share/dbus-1/services/org.freedesktop.FileManager1.service" "$service"
    log 'FileManager1 activation now targets Flea. A previous running owner is retained until logout; no file-manager process was killed.'
    # Only remove the former default after Flea's actual QML/IPC has passed.
    # Reuse exact dependency guards and recovery RPMs, without autoremove.
    source "$ROOT/modules/cleanup.sh"
    local CLEANUP_APPS=nautilus
    module_cleanup
    log 'Flea configured for folders. Omarchy-specific --default/--picker were not executed; screen-sharing portals remain unchanged.'
}
