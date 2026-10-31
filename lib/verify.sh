#!/usr/bin/env bash
verify() {
    local p
    if [[ -f $RUN/expected-rpm ]]; then
        while IFS= read -r p; do rpm -q "$p" >/dev/null || die "Missing RPM: $p"; done < "$RUN/expected-rpm"
    fi
    if [[ -f $RUN/expected-flatpak ]]; then
        while IFS= read -r p; do flatpak info --user "$p" >/dev/null || die "Missing Flatpak: $p"; done < "$RUN/expected-flatpak"
    fi
    if command -v tailscale >/dev/null; then systemctl is-active tailscaled; fi
    if command -v brave-browser >/dev/null && [[ " $MODULES " == *' defaults '* ]]; then
        [[ $(xdg-mime query default x-scheme-handler/https) == brave-browser.desktop ]] || die 'Brave default verification failed.'
    fi
    run sudo dnf5 check
    log 'Package checks passed. Graphical session runtime checks remain pending until scripts/validate-session passes.'
}
