#!/usr/bin/env bash
verify() {
    local p type desktop
    if [[ ${DESKTOP:-} == plasma ]]; then
        rpm -q plasma-desktop plasma-workspace >/dev/null || die 'KDE Plasma preservation check failed.'
    fi
    if [[ -f $RUN/expected-rpm ]]; then
        while IFS= read -r p; do rpm -q "$p" >/dev/null || die "Missing RPM: $p"; done < "$RUN/expected-rpm"
    fi
    if [[ -f $RUN/expected-flatpak ]]; then
        while IFS= read -r p; do flatpak info --user "$p" >/dev/null || die "Missing Flatpak: $p"; done < "$RUN/expected-flatpak"
    fi
    if command -v tailscale >/dev/null; then systemctl is-active tailscaled; fi
    if [[ $MODULES =~ (^|[[:space:]])omasnap($|[[:space:]]) ]]; then
        run "$HOME/.local/share/fedora-postinstall/scripts/omasnap-manager" check
    fi
    if [[ $MODULES =~ (^|[[:space:]])defaults($|[[:space:]]) ]]; then
        if [[ -x $HOME/.local/bin/flea ]]; then
            [[ $(xdg-mime query default inode/directory) == com.thisisgm.flea.desktop ]] || die 'Flea default verification failed.'
        fi
        if command -v brave-browser >/dev/null; then
            for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do
                [[ $(xdg-mime query default "$type") == brave-browser.desktop ]] || die "Brave default verification failed: $type"
            done
        fi
        if command -v code >/dev/null; then
            desktop=$(code_desktop_id) || die 'VS Code desktop entry verification failed.'
            [[ $(xdg-mime query default text/plain) == "$desktop" ]] || die 'VS Code default verification failed.'
        fi
    fi
    run sudo dnf5 check
    log 'Package checks passed. Graphical session runtime checks remain pending until scripts/validate-session passes.'
}
