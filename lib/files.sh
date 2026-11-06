#!/usr/bin/env bash
selected_file_manager() {
    local selection=${FILE_MANAGER:-} saved=${XDG_CONFIG_HOME:-$HOME/.config}/fedora-postinstall/file-manager
    if [[ -z $selection && -f $saved ]]; then selection=$(< "$saved"); fi
    selection=${selection:-flea}
    case $selection in flea|nautilus) printf '%s\n' "$selection" ;; *) die "Unknown file manager: $selection (choose flea or nautilus)" ;; esac
}
file_manager_desktop() {
    local manager
    manager=$(selected_file_manager) || return
    case $manager in
        flea) echo com.thisisgm.flea.desktop ;;
        nautilus) echo org.gnome.Nautilus.desktop ;;
    esac
}
file_manager_installed() {
    local manager
    manager=$(selected_file_manager) || return
    case $manager in
        flea) [[ -x $HOME/.local/bin/flea ]] ;;
        nautilus) command -v nautilus >/dev/null && [[ -f /usr/share/applications/org.gnome.Nautilus.desktop ]] ;;
    esac
}
