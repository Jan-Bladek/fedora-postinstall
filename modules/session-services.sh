#!/usr/bin/env bash
configure_ksplash_activation() {
    [[ ${DESKTOP:-} != plasma ]] || return 0
    local vendor=${1:-/usr/share/dbus-1/services/org.kde.KSplash.service}
    local data_home=${XDG_DATA_HOME:-$HOME/.local/share} target unit failed desktop line
    [[ -f $vendor ]] || return 0
    # Apply only to the Fedora activation entry that waits for Plasma's splash.
    # New/different upstream activation mechanisms require a separate review.
    if ! python3 - "$vendor" <<'PY_VENDOR'
import configparser, shlex, sys
cfg = configparser.ConfigParser(interpolation=None)
cfg.read(sys.argv[1])
entry = cfg['D-BUS Service'] if cfg.has_section('D-BUS Service') else {}
sys.exit(not (entry.get('Name') == 'org.kde.KSplash' and
              shlex.split(entry.get('Exec', '')) == ['/usr/bin/plasma_waitforname', 'org.kde.KSplash'] and
              not entry.get('SystemdService')))
PY_VENDOR
    then
        log 'Upstream KSplash activation differs; no compatibility override applied.'
        return 0
    fi
    target=$data_home/dbus-1/services/org.kde.KSplash.service
    unit=$CONFIG/systemd/user/fedora-ksplash-activation.service
    if [[ -e $target ]]; then cp -- "$target" "$RUN/ksplash-activation-before.service"; fi
    config_file "$ROOT/config/dbus-1/services/org.kde.KSplash.service" "$target"
    config_file "$ROOT/config/systemd/user/fedora-ksplash-activation.service" "$unit"
    if ! cmp -s "$ROOT/config/dbus-1/services/org.kde.KSplash.service" "$target" ||
       ! cmp -s "$ROOT/config/systemd/user/fedora-ksplash-activation.service" "$unit"; then
        log 'Custom KSplash activation retained; review the .fedora-postinstall-new proposal before applying.'
        return 0
    fi
    if systemctl --user show-environment >/dev/null 2>&1; then
        if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} && -n ${WAYLAND_DISPLAY:-} ]]; then
            export XDG_CURRENT_DESKTOP=Hyprland XDG_SESSION_DESKTOP=Hyprland XDG_SESSION_TYPE=wayland
            run dbus-update-activation-environment --systemd XDG_CURRENT_DESKTOP XDG_SESSION_DESKTOP XDG_SESSION_TYPE
        fi
        run systemctl --user daemon-reload
        run busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig
        desktop=$(systemctl --user show-environment)
        if grep -Fxq 'XDG_CURRENT_DESKTOP=Hyprland' <<< "$desktop"; then
            # Confirm that the guarded activation is skipped before retiring old failures.
            run systemctl --user start fedora-ksplash-activation.service
            if systemctl --user is-active --quiet fedora-ksplash-activation.service ||
               systemctl --user is-failed --quiet fedora-ksplash-activation.service; then
                die 'KSplash session condition was not applied; previous failures retained for inspection.'
            fi
            failed=$(systemctl --user list-units --failed --all --plain --no-legend 'dbus-*org.kde.KSplash@*.service')
            while read -r line; do
                [[ -n $line ]] || continue
                unit=${line%% *}
                case $unit in
                    dbus-*org.kde.KSplash@*.service)
                        journalctl --user -b -u "$unit" --no-pager > "$RUN/$unit.journal"
                        run systemctl --user reset-failed "$unit" ;;
                esac
            done <<< "$failed"
        fi
    fi
    log 'KSplash activation is skipped in Hyprland; the original KDE wait-for-name helper remains available in Plasma.'
}

module_session_services() {
    [[ ${DESKTOP:-} != plasma ]] || return 0
    install_shell_selector
    configure_ksplash_activation
}
