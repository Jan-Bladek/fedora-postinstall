#!/usr/bin/env bash
module_cleanup() {
    source "$ROOT/lib/files.sh"
    local manager desktop
    manager=$(selected_file_manager)
    desktop=$(file_manager_desktop)
    export FILE_MANAGER=$manager
    local p unit path selection=${CLEANUP_APPS:-all}
    local -a targets=() keys=() units=() nevras=()
    read -r -a keys <<< "$selection"
    # Keep optional office apps selected for installation, regardless of module order.
    if [[ $selection == all && " ${MODULES:-} " == *" libreoffice "* ]]; then
        mapfile -t keys < <(python3 "$ROOT/scripts/cleanup-plan.py" --catalog | cut -f1 | sed '/^libreoffice$/d')
    fi
    local key
    for key in "${keys[@]}"; do
        if [[ $key == all || $key == dolphin ]]; then
            file_manager_installed || die 'Install the files module before removing Dolphin.'
            if [[ $manager == flea ]]; then run "$HOME/.local/share/fedora-postinstall/scripts/flea-manager" check; fi
            run xdg-mime default "$desktop" inode/directory
            [[ $(xdg-mime query default inode/directory) == "$desktop" ]] || die 'Selected file-manager default check failed; Dolphin retained.'
            break
        fi
    done
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
                case $path in
                    /usr/lib/systemd/user/*.service|/usr/lib/systemd/user/*.timer|/usr/lib/systemd/user/*.socket|/usr/lib/systemd/user/*.path)
                        units+=("${path##*/}") ;;
                esac
            done < <(rpm -ql "$p")
        done
        if declare -F ui_status >/dev/null; then ui_status "Kopia odzyskiwania ${#targets[@]} pakietów przed usunięciem"; fi
        run dnf5 download --destdir "$RUN/cleanup-rpms" "${nevras[@]}"
        run sudo rpm -e --test "${targets[@]}"
        rpm -qa --qf '%{NAME}\n' | sort -u > "$RUN/cleanup-retained-before"
        # Stop only service units OWNED by apps about to be removed. Never
        # disable shared KDE, system services, akonadi or kernel workqueues.
        if ((${#units[@]})); then
            mapfile -t units < <(printf '%s\n' "${units[@]}" | sort -u)
        fi
        printf '%s\n' "${units[@]}" > "$RUN/cleanup-owned-user-units"
        for unit in "${units[@]}"; do
            # Templates are not runtime unit instances. Stop their activation socket/path instead.
            [[ $unit != *@.* ]] || continue
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
        if systemctl --user show-environment >/dev/null 2>&1; then
            run systemctl --user daemon-reload
            for unit in "${units[@]}"; do
                [[ $unit != *@.* ]] || continue
                if systemctl --user is-failed --quiet "$unit"; then run systemctl --user reset-failed "$unit"; fi
            done
        fi
    fi
    if python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["hide_uuctl"])' "$RUN/cleanup-plan.json"; then
        python3 "$ROOT/scripts/hide-launcher.py" uuctl.desktop
    fi
    if python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["hide_menu_editor"])' "$RUN/cleanup-plan.json"; then
        python3 "$ROOT/scripts/hide-launcher.py" org.kde.kmenuedit.desktop
    fi
    # Common alternate installations: remove only the selected app, retaining
    # Flatpak runtimes and application data (never use --unused/--delete-data).
    if command -v flatpak >/dev/null; then
        local key app scope
        for key in firefox libreoffice; do
            if [[ $key == libreoffice && " ${MODULES:-} " == *" libreoffice "* ]]; then continue; fi
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
