#!/usr/bin/env bash
module_terminal() {
    packages kitty bash
    config_file "$ROOT/config/kitty/kitty.conf" "$CONFIG/kitty/kitty.conf"
    mkdir -p "$CONFIG/environment.d"
    config_file "$ROOT/config/environment.conf" "$CONFIG/environment.d/60-fedora-postinstall.conf"
    if [[ $(getent passwd "$USER" | cut -d: -f7) != /bin/bash ]]; then run chsh -s /bin/bash; fi
}
