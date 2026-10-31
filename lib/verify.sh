#!/usr/bin/env bash
verify() {
    local p type desktop
    if [[ -f $RUN/expected-rpm ]]; then
        while IFS= read -r p; do rpm -q "$p" >/dev/null || die "Missing RPM: $p"; done < "$RUN/expected-rpm"
    fi
    if [[ -f $RUN/expected-flatpak ]]; then
        while IFS= read -r p; do flatpak info --user "$p" >/dev/null || die "Missing Flatpak: $p"; done < "$RUN/expected-flatpak"
    fi
    if command -v tailscale >/dev/null; then systemctl is-active tailscaled; fi
    if [[ $MODULES =~ (^|[[:space:]])defaults($|[[:space:]]) ]]; then
        if command -v brave-browser >/dev/null; then
            for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do
                [[ $(xdg-mime query default "$type") == brave-browser.desktop ]] || die "Brave default verification failed: $type"
            done
        fi
        if command -v codium >/dev/null; then
            desktop=$(codium_desktop_id) || die 'VSCodium desktop entry verification failed.'
            [[ $(xdg-mime query default text/plain) == "$desktop" ]] || die 'VSCodium default verification failed.'
        fi
    fi
    run sudo dnf5 check
    log 'Package checks passed. Graphical session runtime checks remain pending until scripts/validate-session passes.'
}
