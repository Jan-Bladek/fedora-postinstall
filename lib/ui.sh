#!/usr/bin/env bash
# All questions happen before the progress view. The gauge reflects completed
# modules, not a fabricated download percentage. Logs always retain command output.
ui_confirm_plan() {
    local summary
    summary="Pulpit: $DESKTOP
Moduły: $MODULES
Usuwanie aplikacji: ${CLEANUP_APPS:-nie}

Zostaną wykonane kopie konfiguracji. Zatwierdzasz instalację wybranych aplikacji,
aktualizację RPM i klucze oficjalnych dostawców / wskazanych COPR:
Fedora, Microsoft, Brave, LibreWolf, Tailscale, lionheartp/Hyprland, duxlabs/DMS.

Wybrany moduł Hyprland stosuje profil Omarchy i zapisuje kopię poprzedniej konfiguracji.
--keep-hypr-config zachowuje własny plik. Kitty zmienia tylko wskazane ustawienia. Usuwanie aplikacji odbywa się
wyłącznie z listy po teście zależności; bez autoremove i usuwania Plasma.
LazyVim przenosi istniejącą konfigurację i dane Neovim do kopii .pre-fedora-postinstall.
Zamknij aplikacje wybrane do usunięcia. Licencje IDE aktywujesz samodzielnie. Dane osobiste aplikacji pozostają na dysku."
    if command -v whiptail >/dev/null; then
        whiptail --title 'Fedora · Podsumowanie' --yes-button 'Instaluj' --no-button 'Anuluj' --yesno "$summary" 24 86
    else
        printf '%s\n' "$summary"
        local answer
        read -r -p 'Rozpocząć instalację? [t/N]: ' answer
        [[ $answer == t || $answer == T || $answer == y || $answer == Y ]]
    fi
}
ui_cleanup_choice() {
    local answer key label
    local -a items=()
    if command -v whiptail >/dev/null; then
        if ! whiptail --title 'Fedora · Aplikacje dodatkowe' --yes-button 'Wybierz aplikacje' --no-button 'Zachowaj aplikacje' \
            --yesno 'Czy chcesz usunąć wskazane zbędne aplikacje KDE/Fedory? Sam pulpit Plasma, biblioteki Qt i dane użytkownika zostaną zachowane.' 12 78; then return; fi
        while IFS=$'\t' read -r key label; do items+=("$key" "$label" ON); done < <(python3 "$ROOT/scripts/cleanup-plan.py" --catalog)
        CLEANUP_APPS=$(whiptail --title 'Usuwanie aplikacji — Spacja zaznacza' --separate-output --checklist \
            'Odznacz aplikacje, które chcesz zachować. Zależności mogą zablokować usunięcie.' 25 90 15 "${items[@]}" 3>&1 1>&2 2>&3) || return
        CLEANUP_APPS=${CLEANUP_APPS//$'\n'/ }
    else
        read -r -p 'Usunąć opcjonalne aplikacje z listy cleanup? [t/N]: ' answer
        if [[ $answer == t || $answer == T ]]; then
            python3 "$ROOT/scripts/cleanup-plan.py" --catalog
            read -r -p 'Wpisz identyfikatory lub all: ' CLEANUP_APPS
        fi
    fi
    if [[ -n ${CLEANUP_APPS:-} ]]; then MODULES+=" cleanup"; fi
}
ui_status() {
    if [[ -n ${FEDORA_PROGRESS_STATUS:-} ]]; then
        printf '%s\n' "$*" > "$FEDORA_PROGRESS_STATUS.new"
        mv -- "$FEDORA_PROGRESS_STATUS.new" "$FEDORA_PROGRESS_STATUS"
    fi
}
ui_start() {
    [[ ${USE_PROGRESS:-0} == 1 ]] || return 0
    # sudo was authenticated on the real terminal before this view starts.
    FEDORA_PROGRESS_STATUS=$RUN/progress-status
    export FEDORA_PROGRESS_STATUS
    printf '0\n' > "$RUN/progress-percent"
    ui_status 'Przygotowywanie kopii zapasowej'
    exec 7>/dev/tty
    (
        while [[ ! -f $RUN/progress-done ]]; do
            printf 'XXX\n%s\nFedora Post-Install · %s\n\n%s\n\nEtapy ukończone. Szczegóły: %s/install.log\nXXX\n' \
                "$(cat "$RUN/progress-percent")" "$DESKTOP" "$(cat "$FEDORA_PROGRESS_STATUS")" "$RUN"
            sleep 1
        done
        printf '100\n'
    ) | whiptail --title 'Fedora · Instalacja' --gauge 'Przygotowanie' 13 86 0 >&7 2>&7 &
    UI_PID=$!
}
ui_finish() {
    local rc=${1:-0}
    if [[ -n ${UI_PID:-} ]]; then
        touch "$RUN/progress-done"
        if ! wait "$UI_PID"; then printf 'Progress view closed.\n' >&7; fi
        if ((rc)); then
            printf '\nInstalacja przerwana (kod %s). Log: %s/install.log\n' "$rc" "$RUN" >&7
        else
            printf '\nInstalacja zakończona. Log: %s/install.log\n' "$RUN" >&7
        fi
        unset UI_PID
    fi
}
