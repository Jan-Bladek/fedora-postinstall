#!/usr/bin/env bash
module_cleanup() {
    local p unit path selection=${CLEANUP_APPS:-all}
    local -a targets=() keys=() units=() nevras=()
    read -r -a keys <<< "$selection"
    python3 "$ROOT/scripts/cleanup-plan.py" "${keys[@]}" > "$RUN/cleanup-plan.json"
    cat "$RUN/cleanup-plan.json"
    mapfile -t targets < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["remove"]))' "$RUN/cleanup-plan.json")
    if [[ ${targets[0]:-} == '' ]]; then targets=(); fi
    if ((${#targets[@]})); then
        # Keep EVERY package outside the exact app list, including Qt, KWin,
        # Plasma login, uwsm, NetworkManager, SELinux and kernel workers.
        run sudo rpm -e --test "${targets[@]}"
        packages dnf5-plugins
        mkdir -p "$RUN/cleanup-rpms"
        for p in "${targets[@]}"; do
            nevras+=("$(rpm -q --qf '%{NEVRA}' "$p")")
            while IFS= read -r path; do
                if [[ $path == /usr/lib/systemd/user/*.service ]]; then units+=("${path##*/}"); fi
            done < <(rpm -ql "$p")
        done
        if declare -F ui_status >/dev/null; then ui_status "Kopia odzyskiwania ${#targets[@]} pakietów przed usunięciem"; fi
        run dnf5 download --destdir "$RUN/cleanup-rpms" "${nevras[@]}"
        run sudo rpm -e --test "${targets[@]}"
        rpm -qa --qf '%{NAME}\n' | sort -u > "$RUN/cleanup-retained-before"
        # Stop only service units OWNED by apps about to be removed. Never
        # disable shared KDE, system services, akonadi or kernel workqueues.
        for unit in "${units[@]}"; do
            if systemctl --user is-enabled --quiet "$unit"; then run systemctl --user disable "$unit"; fi
            if systemctl --user is-active --quiet "$unit"; then run systemctl --user stop "$unit"; fi
        done
        if printf '%s\n' "${targets[@]}" | grep -Fxq kdeconnectd && pgrep -u "$(id -u)" -x kdeconnectd >/dev/null; then
            run pkill -TERM -u "$(id -u)" -x kdeconnectd
        fi
        if declare -F ui_status >/dev/null; then ui_status "Usuwanie ${#targets[@]} wybranych pakietów aplikacji"; fi
        run sudo rpm -e "${targets[@]}"
        rpm -qa --qf '%{NAME}\n' | sort -u > "$RUN/cleanup-retained-after"
        printf '%s\n' "${targets[@]}" | sort -u > "$RUN/cleanup-removed"
        comm -23 "$RUN/cleanup-retained-before" "$RUN/cleanup-retained-after" > "$RUN/cleanup-actually-removed"
        cmp "$RUN/cleanup-removed" "$RUN/cleanup-actually-removed" || die 'Cleanup package inventory mismatch.'
        run sudo dnf5 check
        if systemctl --user show-environment >/dev/null 2>&1; then run systemctl --user daemon-reload; fi
    fi
    if python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["hide_uuctl"])' "$RUN/cleanup-plan.json"; then
        python3 "$ROOT/scripts/hide-uuctl.py" "$CONFIG"
    fi
    # Common alternate installations: remove only the selected app, retaining
    # Flatpak runtimes and application data (never use --unused/--delete-data).
    if command -v flatpak >/dev/null; then
        local key app scope
        for key in firefox libreoffice; do
            if [[ $selection == all || " $selection " == *" $key "* ]]; then
                if [[ $key == firefox ]]; then app=org.mozilla.firefox; else app=org.libreoffice.LibreOffice; fi
                for scope in --user --system; do
                    if flatpak info "$scope" "$app" >/dev/null 2>&1; then
                        if [[ $scope == --system ]]; then
                            run sudo flatpak uninstall --assumeyes --noninteractive "$scope" "$app"
                        else
                            run flatpak uninstall --assumeyes --noninteractive "$scope" "$app"
                        fi
                    fi
                done
            fi
        done
    fi
    log "App cleanup complete. Recovery RPMs: $RUN/cleanup-rpms. Kernel workers and shared services were retained."
}
