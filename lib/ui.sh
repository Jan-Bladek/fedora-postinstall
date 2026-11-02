#!/usr/bin/env bash
# All questions happen before the progress view. The gauge reflects completed
# modules, not a fabricated download percentage. Logs always retain command output.
ui_confirm_plan() {
    local summary
    summary="Pulpit: $DESKTOP
Wybrane IDE: ${DEV_APPS:-brak}
Moduły: $MODULES
Usuwanie aplikacji: ${CLEANUP_APPS:-nie}

Zostaną wykonane kopie konfiguracji. Zatwierdzasz instalację wybranych aplikacji,
aktualizację RPM i klucze oficjalnych dostawców / wskazanych COPR:
Fedora, Microsoft, Brave, LibreWolf, Tailscale, lionheartp/Hyprland, duxlabs/DMS.
Flea, Omasnap i HyprMod: przypięte źródła; HyprMod używa uv/PyPI.
Flea używa prywatnych bibliotek QML Omarchy i tymczasowego Rust przy braku Cargo.

Wybrany moduł Hyprland stosuje profil Omarchy i zapisuje kopię poprzedniej konfiguracji.
--keep-hypr-config zachowuje własny plik. Kitty zmienia tylko wskazane ustawienia. Usuwanie aplikacji odbywa się
wyłącznie z listy po teście zależności; bez autoremove i usuwania Plasma.
LazyVim przenosi istniejącą konfigurację i dane Neovim do kopii .pre-fedora-postinstall.
Zamknij Neovim i aplikacje wybrane do usunięcia. Licencje IDE aktywujesz samodzielnie. Dane osobiste aplikacji pozostają na dysku."
    if command -v whiptail >/dev/null; then
        whiptail --title 'Fedora · Podsumowanie' --yes-button 'Instaluj' --no-button 'Anuluj' --scrolltext --yesno "$summary" 22 78
    else
        printf '%s\n' "$summary"
        local answer
        read -r -p 'Rozpocząć instalację? [t/N]: ' answer
        [[ $answer == t || $answer == T || $answer == y || $answer == Y ]]
    fi
}
ui_cleanup_choice() {
    local answer
    if command -v whiptail >/dev/null; then
        if ! whiptail --title 'Fedora · Debloat Plasma' --yes-button 'Tak, usuń' --no-button 'Nie, zachowaj' --defaultno \
            --yesno 'Usunąć cały przygotowany zestaw zbędnych aplikacji KDE/Fedory? Obejmuje m.in. KMail/PIM, KDE Connect, gry, Firefox, Dolphin (po kontroli Flea), LibreOffice (jeśli nie wybierzesz instalacji), Spectacle, Gwenview, Dragon, KRDC/Krfb i edytor menu. Sam pulpit Plasma, Qt i dane użytkownika pozostaną. Pełna lista: data/cleanup.tsv.' 16 78; then return 0; fi
        CLEANUP_APPS=all
    else
        read -r -p 'Usunąć cały zestaw debloat Plasma? [t/N]: ' answer
        if [[ $answer == t || $answer == T || $answer == y || $answer == Y ]]; then CLEANUP_APPS=all; fi
    fi
    if [[ -n ${CLEANUP_APPS:-} ]]; then MODULES+=" cleanup"; fi
}
ui_development_choice() {
    if command -v whiptail >/dev/null; then
        DEV_APPS=$(whiptail --title 'Fedora · Zestaw programistyczny' --separate-output --checklist \
            'Wybierz IDE. Rust tylko z RustRover, C/C++ z CLion, Node.js z WebStorm.' 19 78 6 \
            code 'VS Code' ON rustrover 'RustRover + Rust' OFF \
            intellij-idea 'IntelliJ IDEA' OFF webstorm 'WebStorm + Node.js' OFF \
            clion 'CLion + C/C++' OFF arduino-ide 'Arduino IDE' OFF 3>&1 1>&2 2>&3) || return
    else
        read -r -p 'IDE (code rustrover intellij-idea webstorm clion arduino-ide; Enter = code, none = brak): ' DEV_APPS
        DEV_APPS=${DEV_APPS:-code}
        [[ $DEV_APPS != none ]] || DEV_APPS=''
    fi
    DEV_APPS=${DEV_APPS//$'\n'/ }
    export DEV_PROFILE=custom
}
ui_office_choice() {
    local answer
    if command -v whiptail >/dev/null; then
        if ! whiptail --title 'Fedora · LibreOffice' --yes-button 'Instaluj / zachowaj' --no-button 'Pomiń' --defaultno \
            --yesno 'Zainstalować LibreOffice Writer, Calc i Impress po polsku? Ten wybór zachowuje LibreOffice także przy debloat.' 12 78; then return 0; fi
    else
        read -r -p 'Zainstalować / zachować LibreOffice? [t/N]: ' answer
        [[ $answer == t || $answer == T || $answer == y || $answer == Y ]] || return 0
    fi
    MODULES+=' libreoffice'
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
        if [[ ! -f $RUN/progress-exit || $(cat "$RUN/progress-exit") == 0 ]]; then printf '100\n'; fi
    ) | whiptail --title 'Fedora · Instalacja' --gauge 'Przygotowanie' 13 78 0 >&7 2>&7 &
    UI_PID=$!
}
ui_finish() {
    local rc=${1:-0}
    if [[ -n ${UI_PID:-} ]]; then
        printf '%s\n' "$rc" > "$RUN/progress-exit"
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

ui_module_label() {
    case $1 in
        snapshots) echo 'Kopie konfiguracji i Snapper' ;;
        dependencies) echo 'Aktualizacja Fedory i narzędzia podstawowe' ;;
        hyprland) echo 'Hyprland + profil Omarchy (kopia poprzedniego configu)' ;;
        noctalia) echo 'Powłoka Noctalia' ;;
        dms) echo 'Powłoka DankMaterialShell / Dux Shell' ;;
        terminal) echo 'Kitty, Bash, JetBrains Mono i ikony fontów' ;;
        lazyvim) echo 'LazyVim + wtyczki (kopia starego Neovim)' ;;
        development) echo 'Wybrane IDE i ich narzędzia' ;;
        browsers) echo 'Brave (domyślna) + LibreWolf' ;;
        multimedia) echo 'OBS, Vesktop i Steam' ;;
        utilities) echo 'Obsidian, LocalSend i Tailscale' ;;
        defaults) echo 'Aplikacje domyślne' ;;
        optimization) echo 'Diagnostyka i zachowanie zabezpieczeń Fedory' ;;
        updates) echo 'Scentralizowane fedora-update' ;;
        *) printf '%s\n' "$1" ;;
    esac
}
