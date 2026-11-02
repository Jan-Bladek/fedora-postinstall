#!/usr/bin/env bash
# Parse desktop choices before preflight, including dry runs on non-Fedora hosts.
default_modules() {
    case $DESKTOP in
        noctalia|dms) echo "snapshots dependencies hyprland $DESKTOP terminal files hyprmod omasnap lazyvim development browsers multimedia utilities defaults optimization updates" ;;
        plasma) echo 'snapshots dependencies terminal files lazyvim development browsers multimedia utilities defaults optimization updates' ;;
        *) die "Unknown desktop: $DESKTOP (choose noctalia, dms or plasma)" ;;
    esac
}
validate_desktop_modules() {
    local module
    case $DESKTOP in noctalia|dms|plasma) ;; *) die "Unknown desktop: $DESKTOP" ;; esac
    for module in $MODULES; do
        case $module in
            noctalia|dms) [[ $module == "$DESKTOP" ]] || die "Module $module conflicts with desktop $DESKTOP." ;;
            hyprland|hyprmod|omasnap|kde-removal) [[ $DESKTOP != plasma ]] || die "Plasma preservation conflicts with module $module." ;;
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
    atomic_config "$RUN/shell-selection" "$selection"
    log "Selected $1 for the next Hyprland session. Log out before changing shells."
}

prepare_dms_includes() {
    local name
    mkdir -p "$CONFIG/hypr/dms"
    for name in colors outputs layout cursor input windowrules; do
        # Empty initial files must exist before require; never truncate DMS output.
        if [[ ! -e $CONFIG/hypr/dms/$name.lua ]]; then
            (set -o noclobber; : > "$CONFIG/hypr/dms/$name.lua")
        fi
    done
}
