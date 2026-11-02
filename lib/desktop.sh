#!/usr/bin/env bash
# Parse desktop choices before preflight, including dry runs on non-Fedora hosts.
default_modules() {
    case $DESKTOP in
        noctalia|dms) echo "snapshots dependencies hyprland $DESKTOP terminal lazyvim development browsers multimedia utilities defaults optimization updates" ;;
        plasma) echo 'snapshots dependencies terminal lazyvim development browsers multimedia utilities defaults optimization updates' ;;
        *) die "Unknown desktop: $DESKTOP (choose noctalia, dms or plasma)" ;;
    esac
}
validate_desktop_modules() {
    local module
    case $DESKTOP in noctalia|dms|plasma) ;; *) die "Unknown desktop: $DESKTOP" ;; esac
    for module in $MODULES; do
        case $module in
            noctalia|dms) [[ $module == "$DESKTOP" ]] || die "Module $module conflicts with desktop $DESKTOP." ;;
            hyprland|kde-removal) [[ $DESKTOP != plasma ]] || die "Plasma preservation conflicts with module $module." ;;
        esac
    done
}
install_shell_selector() {
    local dest=$HOME/.local/share/fedora-postinstall/scripts
    mkdir -p "$dest" "$CONFIG/fedora-postinstall"
    install -m 755 "$ROOT/scripts/desktop-shell" "$dest/desktop-shell"
}
select_shell() {
    install_shell_selector
    # This is the installer's explicit selection, not an upstream shell profile.
    local selection=$CONFIG/fedora-postinstall/shell
    [[ ! -L $selection ]] || die 'Refusing to replace a symlink at the shell selection file.'
    printf '%s\n' "$1" > "$RUN/shell-selection"
    install -m 600 "$RUN/shell-selection" "$selection"
    log "Selected $1 for the next Hyprland session. Log out before changing shells."
}
