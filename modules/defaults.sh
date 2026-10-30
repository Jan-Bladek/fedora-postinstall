#!/usr/bin/env bash
module_defaults() {
    local type
    if command -v brave-browser >/dev/null; then
        run xdg-settings set default-web-browser brave-browser.desktop
        for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do run xdg-mime default brave-browser.desktop "$type"; done
    fi
    if command -v codium >/dev/null; then
        run xdg-mime default codium.desktop text/plain
        run xdg-mime default codium.desktop x-scheme-handler/vscode
    fi
    if command -v kitty >/dev/null; then run xdg-mime default kitty.desktop x-scheme-handler/terminal; fi
}
