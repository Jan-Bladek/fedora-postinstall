#!/usr/bin/env bash
module_omasnap() {
    [[ ${DESKTOP:-} != plasma ]] || die 'Omasnap requires Hyprland; it is not configured for Plasma.'
    command -v Hyprland >/dev/null || die 'Install Hyprland before Omasnap.'
    [[ -f $CONFIG/hypr/hyprland.lua ]] || die 'Omasnap needs an existing Hyprland Lua main config; no user config was replaced.'
    packages git gcc gcc-c++ cmake ninja-build pkgconf-pkg-config qt6-qtbase-devel \
        layer-shell-qt-devel wayland-devel wayland-protocols-devel libdeflate-devel \
        qt6-qtwayland wl-clipboard xdg-utils tesseract tesseract-langpack-eng
    local dest=$HOME/.local/share/fedora-postinstall module=$CONFIG/hypr/fedora-postinstall-omasnap.lua
    mkdir -p "$dest/scripts" "$dest/data" "$HOME/.local/bin"
    install -m 644 "$ROOT/data/omasnap-release" "$dest/data/omasnap-release"
    install -m 755 "$ROOT/scripts/omasnap-manager" "$dest/scripts/omasnap-manager"
    install -m 755 "$ROOT/scripts/validate-omasnap" "$HOME/.local/bin/validate-omasnap"
    if declare -F ui_status >/dev/null; then ui_status "Omasnap: kompilacja i testy upstream (może potrwać kilka minut)"; fi
    run "$dest/scripts/omasnap-manager" install
    if [[ -e $module ]]; then cp -- "$module" "$RUN/omasnap-bindings-before.lua"; fi
    cp -- "$CONFIG/hypr/hyprland.lua" "$RUN/hyprland-before-omasnap.lua"
    # Keep the user's main config intact except for our last-loaded block.
    cp -- "$ROOT/config/hyprland/omasnap.lua" "$RUN/omasnap-proposed.lua"
    if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
        run hyprctl -j binds > "$RUN/bindings-before-omasnap.json"
        python3 - "$RUN/bindings-before-omasnap.json" <<'PY'
import json, sys
for bind in json.load(open(sys.argv[1])):
    if (bind.get('key', '').upper(), bind.get('modmask')) in {('PRINT', 0), ('S', 65)}:
        print('Screenshot shortcut override:', bind.get('key'), bind.get('modmask'), bind.get('arg'))
PY
    fi
    python3 "$ROOT/scripts/omasnap-bindings.py" "$CONFIG/hypr/hyprland.lua" "$RUN/omasnap-proposed.lua" "$RUN/hyprland.lua"
    source "$ROOT/modules/hyprland.sh"
    validate_hyprland_config
    atomic_config "$ROOT/config/hyprland/omasnap.lua" "$module"
    python3 "$ROOT/scripts/omasnap-bindings.py" "$CONFIG/hypr/hyprland.lua" "$module" "$RUN/hyprland.lua"
    atomic_config "$RUN/hyprland.lua" "$CONFIG/hypr/hyprland.lua"
    run "$dest/scripts/omasnap-manager" check
    if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
        run hyprctl reload
        local errors
        errors=$(hyprctl configerrors)
        [[ -z $errors || $errors == ok ]] || die "Hyprland reload failed: $errors; restore $RUN/hyprland-before-omasnap.lua"
    fi
    log 'Omasnap: Print = smart capture; Super+Shift+S = region with immediate editing. Old bindings on these keys are overridden after user and DMS settings.'
    log 'CLI/build/parser passed; actual area selection, drawing and clipboard require a live Hyprland test.'
}
