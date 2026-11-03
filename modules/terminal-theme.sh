#!/usr/bin/env bash
module_terminal_theme() {
    [[ ${DESKTOP:-} == noctalia || ${DESKTOP:-} == dms ]] || return 0
    local kitty_config=$CONFIG/kitty/kitty.conf theme_path settings auto_name
    [[ -f $kitty_config ]] || return 0
    cp -- "$kitty_config" "$RUN/kitty-before-system-colors.conf"
    if [[ $DESKTOP == noctalia ]]; then
        command -v noctalia >/dev/null || { log 'Install Noctalia before enabling its terminal palette.'; return 0; }
        packages python3-tomlkit
        settings=$CONFIG/noctalia/settings.toml
        env XDG_CONFIG_HOME="$CONFIG" noctalia config export > "$RUN/noctalia-effective.toml"
        python3 "$ROOT/scripts/configure-terminal-colors.py" "$settings" "$RUN/noctalia-effective.toml" "$RUN/noctalia-terminal-colors.toml"
        if [[ -f $settings ]]; then cp -- "$settings" "$RUN/noctalia-before-terminal-colors.toml"; fi
        atomic_config "$RUN/noctalia-terminal-colors.toml" "$settings"
        printf '%s\n' 'globinclude themes/noctalia.conf' > "$RUN/kitty-system-colors.conf"
        theme_path=themes/noctalia.conf
    else
        settings=$CONFIG/dms/settings.json
        printf '%s\n' '{"runDmsMatugenTemplates":true,"matugenTemplateKitty":true}' > "$RUN/dms-terminal-colors-patch.json"
        python3 "$ROOT/scripts/merge-json.py" "$settings" "$RUN/dms-terminal-colors-patch.json" "$RUN/dms-terminal-colors.json"
        if [[ -f $settings ]]; then cp -- "$settings" "$RUN/dms-before-terminal-colors.json"; fi
        atomic_config "$RUN/dms-terminal-colors.json" "$settings"
        printf '%s\n' 'globinclude dank-tabs.conf' 'globinclude dank-theme.conf' > "$RUN/kitty-system-colors.conf"
        theme_path=dank-theme.conf
    fi
    # Kitty's automatic themes override ordinary includes; keep recoverable copies.
    for auto_name in dark-theme.auto.conf light-theme.auto.conf no-preference-theme.auto.conf; do
        if [[ -e $CONFIG/kitty/$auto_name || -L $CONFIG/kitty/$auto_name ]]; then
            mv -- "$CONFIG/kitty/$auto_name" "$RUN/kitty-$auto_name"
            log "Backed up $auto_name to enable the selected system palette."
        fi
    done
    python3 "$ROOT/scripts/merge-config-block.py" "$kitty_config" "$RUN/kitty-system-colors.conf" "$RUN/kitty-with-system-colors.conf" SYSTEM-COLORS
    atomic_config "$RUN/kitty-with-system-colors.conf" "$kitty_config"
    config_file "$ROOT/config/systemd/user/fedora-kitty-theme.service" "$CONFIG/systemd/user/fedora-kitty-theme.service"
    # PathChanged notices both atomic replacement and close-after-write; no polling.
    python3 - "$CONFIG" "$theme_path" > "$RUN/fedora-kitty-theme.path" <<'PY_PATH'
import sys
from pathlib import Path
path = str(Path(sys.argv[1]) / 'kitty' / sys.argv[2]).replace('%', '%%')
print('[Unit]\nDescription=Watch the selected system palette for Kitty\n\n[Path]')
if any(char in path for char in ('\n', '\r', '\0')):
    raise ValueError('Invalid configuration path')
print('PathChanged=' + path)
print('Unit=fedora-kitty-theme.service\n\n[Install]\nWantedBy=default.target')
PY_PATH
    atomic_config "$RUN/fedora-kitty-theme.path" "$CONFIG/systemd/user/fedora-kitty-theme.path"
    if systemctl --user show-environment >/dev/null 2>&1; then
        run systemctl --user daemon-reload
        run systemctl --user enable --now fedora-kitty-theme.path
        run systemctl --user restart fedora-kitty-theme.path
        run systemctl --user start fedora-kitty-theme.service
        if [[ $DESKTOP == noctalia && -n ${WAYLAND_DISPLAY:-} ]] && pgrep -u "$(id -u)" -x noctalia >/dev/null; then
            run timeout 15 noctalia msg config-reload
            run timeout 30 noctalia msg templates-apply
        fi
    fi
    log "Kitty follows the $DESKTOP system palette, including ANSI text colors and the Zsh prompt. Existing windows reload on palette changes."
}
