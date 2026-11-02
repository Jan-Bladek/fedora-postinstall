#!/usr/bin/env bash
code_desktop_id() {
    local candidate path
    for candidate in com.microsoft.VSCode.desktop code.desktop; do
        path=/usr/share/applications/$candidate
        if [[ -f $path ]] && [[ $(rpm -qf --qf '%{NAME}' "$path" 2>/dev/null) == code ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    return 1
}

module_defaults() {
    local type desktop handler path
    if [[ -x $HOME/.local/bin/flea ]]; then
        run xdg-mime default com.thisisgm.flea.desktop inode/directory
    fi
    if command -v brave-browser >/dev/null; then
        run xdg-settings set default-web-browser brave-browser.desktop
        for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do run xdg-mime default brave-browser.desktop "$type"; done
    fi
    if command -v code >/dev/null; then
        desktop=$(code_desktop_id) || die 'No supported desktop entry owned by the code RPM was found.'
        run xdg-mime default "$desktop" text/plain
        for handler in "${desktop%.desktop}.UrlHandler.desktop" code-url-handler.desktop; do
            path=/usr/share/applications/$handler
            if [[ -f $path ]] && [[ $(rpm -qf --qf '%{NAME}' "$path" 2>/dev/null) == code ]] &&
                grep -q '^MimeType=.*x-scheme-handler/vscode' "$path"; then
                run xdg-mime default "$handler" x-scheme-handler/vscode
                break
            fi
        done
    fi
    if command -v kitty >/dev/null; then run xdg-mime default kitty.desktop x-scheme-handler/terminal; fi
}
