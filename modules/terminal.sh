#!/usr/bin/env bash
module_terminal() {
    packages nano btop kitty bash shadow-utils jetbrains-mono-fonts fontconfig
    if [[ ! -e $CONFIG/kitty/kitty.conf && ! -L $CONFIG/kitty/kitty.conf ]]; then
        config_file "$ROOT/config/kitty/kitty.conf" "$CONFIG/kitty/kitty.conf"
    fi
    local kitty_config=$CONFIG/kitty/kitty.conf env_config=$CONFIG/environment.d/60-fedora-postinstall.conf
    cp -- "$kitty_config" "$RUN/kitty-before-requested-settings.conf"
    python3 "$ROOT/scripts/merge-config-block.py" "$kitty_config" "$ROOT/config/kitty/managed.conf" "$RUN/kitty-merged.conf" KITTY
    atomic_config "$RUN/kitty-merged.conf" "$kitty_config"
    mkdir -p "$CONFIG/environment.d"
    python3 "$ROOT/scripts/merge-config-block.py" "$env_config" "$ROOT/config/environment.conf" "$RUN/environment-merged.conf" DEFAULTS
    atomic_config "$RUN/environment-merged.conf" "$env_config"
    config_file "$ROOT/config/fontconfig/60-jetbrains-mono.conf" "$CONFIG/fontconfig/conf.d/60-jetbrains-mono.conf"
    run python3 "$ROOT/scripts/symbols-fonts.py" install
    run fc-cache -f
    if command -v kwriteconfig6 >/dev/null; then
        run kwriteconfig6 --file kdeglobals --group General --key font 'JetBrains Mono,11,-1,5,50,0,0,0,0,0'
        run kwriteconfig6 --file kdeglobals --group General --key fixed 'JetBrains Mono,11,-1,5,50,0,0,0,0,0'
    fi
    if [[ ${DESKTOP:-} == dms ]]; then
        printf '%s\n' '{"fontFamily":"JetBrains Mono","monoFontFamily":"JetBrains Mono","hyprlandLayoutGapsOverride":5,"hyprlandLayoutGapsOutOverride":10,"hyprlandLayoutBorderSize":2,"hyprlandLayoutRadiusOverride":0}' > "$RUN/dms-font.json"
        python3 "$ROOT/scripts/merge-json.py" "$CONFIG/dms/settings.json" "$RUN/dms-font.json" "$RUN/dms-settings.json"
        mkdir -p "$CONFIG/dms"
        atomic_config "$RUN/dms-settings.json" "$CONFIG/dms/settings.json"
    fi
    mkdir -p "$CONFIG/btop"
    if [[ -e $CONFIG/btop/btop.conf ]]; then cp -- "$CONFIG/btop/btop.conf" "$RUN/btop-before.conf"; fi
    printf 'theme_background = False\n' > "$RUN/btop-patch.conf"
    python3 "$ROOT/scripts/merge-config-block.py" "$CONFIG/btop/btop.conf" "$RUN/btop-patch.conf" "$RUN/btop-merged.conf" BTOP --replace-keys
    atomic_config "$RUN/btop-merged.conf" "$CONFIG/btop/btop.conf"
    if [[ $(getent passwd "$USER" | cut -d: -f7) != /bin/bash ]]; then run sudo usermod --shell /bin/bash "$USER"; fi
}
