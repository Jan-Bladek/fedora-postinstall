#!/usr/bin/env bash
prepare_hyprland_config() {
    local version=$1
    cp -- "$ROOT/config/hyprland/hyprland.lua" "$RUN/hyprland.lua"
    if [[ $version =~ 0\.57\.0([^0-9]|$) ]] && systemd-detect-virt --vm --quiet; then
        # https://github.com/hyprwm/Hyprland/discussions/16702
        cat >> "$RUN/hyprland.lua" <<'LUA'

-- Hyprland 0.57.0 VM compatibility: retain EGL alpha formats for VirGL clients.
hl.config({ quirks = { skip_non_kms_dmabuf_formats = false } })
LUA
        log 'Applied Hyprland 0.57.0 VM EGL compatibility workaround; a fresh session is required.'
    fi
}

validate_hyprland_config() {
    # Configuration-only validation must never share the live session's sockets.
    local config_root runtime
    config_root=$(mktemp -d "$RUN/hypr-verify-config.XXXXXX")
    runtime=$(mktemp -d "$RUN/hypr-verify-runtime.XXXXXX")
    mkdir -p "$config_root/fedora-postinstall" "$config_root/hypr"
    chmod 700 "$runtime"
    printf '%s\n' "${DESKTOP:-noctalia}" > "$config_root/fedora-postinstall/shell"
    # Preserve relative imports in custom configs, while keeping runtime sockets isolated.
    if [[ -d $CONFIG/hypr ]]; then cp -a -- "$CONFIG/hypr/." "$config_root/hypr/"; fi
    atomic_config "$RUN/hyprland.lua" "$config_root/hypr/hyprland.lua"
    run env -u HYPRLAND_INSTANCE_SIGNATURE -u WAYLAND_DISPLAY XDG_RUNTIME_DIR="$runtime" \
        XDG_CONFIG_HOME="$config_root" HYPRLAND_NO_RT=1 Hyprland --verify-config --config "$config_root/hypr/hyprland.lua" \
        > "$RUN/hyprland-verify.log" 2>&1
    cat "$RUN/hyprland-verify.log"
    grep -Fq 'config ok' "$RUN/hyprland-verify.log" || die 'Hyprland rejected the proposed configuration; previous main config retained.'
}

write_hyprland_config() {
    local target=$CONFIG/hypr/hyprland.lua legacy=$RUN/hyprland-legacy.lua
    if [[ ${APPLY_HYPR_PRESET:-0} == 1 ]]; then
        mkdir -p "$CONFIG/hypr"
        if [[ -e $target ]]; then cp -- "$target" "$RUN/hyprland-before-requested-preset.lua"; fi
        atomic_config "$RUN/hyprland.lua" "$target"
        log 'Applied the requested Omarchy-style preset. Previous main config is backed up in this run.'
        return
    fi
    cp -- "$ROOT/config/hyprland/legacy-v0.2.lua" "$legacy"
    if grep -Fq 'skip_non_kms_dmabuf_formats = false' "$RUN/hyprland.lua"; then
        sed -n '/^-- Hyprland 0.57.0 VM compatibility/,$p' "$RUN/hyprland.lua" > "$RUN/legacy-quirk"
        printf '\n' >> "$legacy"
        cat "$RUN/legacy-quirk" >> "$legacy"
    fi
    if [[ ! -L $target && -f $target ]] && cmp -s "$legacy" "$target"; then
        cp -- "$target" "$RUN/hyprland-before-shell-selector.lua"
        atomic_config "$RUN/hyprland.lua" "$target"
        log 'Migrated the unmodified v0.2 Hyprland template to the shell selector; backup saved in this run.'
    elif [[ ! -L $target && -f $target ]]; then
        cp -- "$ROOT/config/hyprland/legacy-v0.3.lua" "$legacy"
        if [[ -s $RUN/legacy-quirk ]]; then printf '\n' >> "$legacy"; cat "$RUN/legacy-quirk" >> "$legacy"; fi
        if cmp -s "$legacy" "$target"; then
            cp -- "$target" "$RUN/hyprland-before-omarchy-settings.lua"
            atomic_config "$RUN/hyprland.lua" "$target"
        else
            config_file "$RUN/hyprland.lua" "$target"
        fi
    else
        config_file "$RUN/hyprland.lua" "$target"
        if ! cmp -s "$RUN/hyprland.lua" "$target"; then
            log 'Merge hyprland.lua.fedora-postinstall-new before using the selected shell; existing custom configuration was retained.'
        fi
    fi
}

configure_session_services() {
    if [[ -f /usr/lib/systemd/user/drkonqi-coredump-launcher@.service ]]; then
        config_file "$ROOT/config/systemd/user/drkonqi-coredump-launcher@.service.d/hyprland.conf" \
            "$CONFIG/systemd/user/drkonqi-coredump-launcher@.service.d/90-fedora-postinstall.conf"
        if systemctl --user show-environment >/dev/null 2>&1; then
            run systemctl --user daemon-reload
        else
            log 'User manager is not available; session service configuration applies at next login.'
        fi
    fi
}

module_hyprland() {
    local available version
    if ! rpm -q hyprland >/dev/null 2>&1; then
        # Reuse the system package cache populated by the dependencies module.
        # A failed query aborts; only a successful empty result offers COPR.
        available=$(sudo dnf5 -q repoquery --available hyprland)
        if [[ -z $available ]]; then
            source "$ROOT/modules/repositories.sh"
            log 'Native Hyprland unavailable. Noctalia docs list this community COPR; review required.'
            vendor_repo hyprland-copr "https://copr.fedorainfracloud.org/coprs/lionheartp/Hyprland/repo/fedora-$VERSION_ID/lionheartp-Hyprland-fedora-$VERSION_ID.repo"
        fi
    fi
    # No implicit allowerasing or distribution synchronization.
    packages hyprland hyprland-guiutils xorg-x11-server-Xwayland xdg-desktop-portal-hyprland xdg-desktop-portal-gtk pipewire pipewire-pulseaudio wireplumber polkit-kde NetworkManager bluez sddm mesa-dri-drivers mesa-vulkan-drivers
    [[ -x /usr/libexec/kf6/polkit-kde-authentication-agent-1 ]] || die 'Fedora KDE Polkit agent executable is missing.'
    version=$(Hyprland --version)
    version=${version%%$'\n'*}
    log "$version"
    [[ $version =~ 0\.([0-9]+) && ${BASH_REMATCH[1]} -ge 55 ]] || die 'Lua config requires Hyprland >=0.55; no configuration was replaced.'
    install_shell_selector
    if [[ ${DESKTOP:-} == dms ]]; then prepare_dms_includes; fi
    prepare_hyprland_config "$version"
    validate_hyprland_config
    write_hyprland_config
    config_file "$ROOT/config/portals.conf" "$CONFIG/xdg-desktop-portal/hyprland-portals.conf"
    run sudo systemctl enable --now NetworkManager bluetooth
    if ! systemctl is-enabled display-manager.service >/dev/null 2>&1; then run sudo systemctl enable sddm; fi
    configure_session_services
    log 'Existing display manager retained. Select Hyprland at next login.'
}
