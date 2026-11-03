#!/usr/bin/env bash
log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }
die() { echo "ERROR: $*" >&2; exit 1; }
run() {
    log "$(printf '%q ' "$@")"
    if [[ ${INSTALL_APPROVED:-0} == 1 ]]; then
        if [[ $1 == sudo && ${2:-} == dnf5 ]]; then shift 2; set -- sudo dnf5 --assumeyes "$@"
        elif [[ $1 == dnf5 ]]; then shift; set -- dnf5 --assumeyes "$@"; fi
    fi
    "$@"
}
confirm() { local reply; read -r -p "$1 [type YES]: " reply; [[ $reply == YES ]]; }
preflight() {
    ((EUID != 0)) || die 'Run as your desktop user; sudo is used only where required.'
    if ((DRY_RUN)); then return; fi
    source /etc/os-release
    [[ $ID == fedora && $VERSION_ID == 44 ]] || die 'Supported target: mutable Fedora 44 only.'
    [[ ! -e /run/ostree-booted ]] || die 'Atomic editions are not supported.'
    [[ $(uname -m) == x86_64 ]] || die 'Full application set requires x86_64.'
    command -v dnf5 >/dev/null || die 'DNF5 is required.'
    [[ $(getenforce) == Enforcing ]] || die 'Enable SELinux Enforcing before installation.'
    command -v sudo >/dev/null || die 'sudo is required.'
    if [[ ${DESKTOP:-} == plasma ]]; then
        rpm -q plasma-desktop plasma-workspace >/dev/null || die 'The Plasma preset requires an existing KDE Plasma installation.'
    fi
}
init_state() {
    umask 077
    STATE=${XDG_STATE_HOME:-$HOME/.local/state}/fedora-postinstall
    CONFIG=${XDG_CONFIG_HOME:-$HOME/.config}
    export STATE CONFIG
    mkdir -p "$STATE" "$CONFIG"
    exec 9>"$STATE/lock"
    flock -n 9 || die 'Another installer is running.'
    RUN=$STATE/runs/$(date +%Y%m%dT%H%M%S)-$$
    export RUN
    mkdir -p "$RUN"
    if [[ ${USE_PROGRESS:-0} == 1 ]]; then
        exec > "$RUN/install.log" 2>&1
    else
        exec > >(tee -a "$RUN/install.log") 2>&1
    fi
    # shellcheck disable=SC2154
    trap 'rc=$?; echo "Interrupted/failed (exit $rc). Recovery: see README and $RUN" >&2; exit "$rc"' ERR
    trap 'exit 130' INT
    trap 'rc=$?; if declare -F ui_finish >/dev/null; then ui_finish "$rc"; fi; if [[ -n ${SUDO_KEEPALIVE_PID:-} ]]; then if kill -0 "$SUDO_KEEPALIVE_PID" 2>/dev/null; then kill "$SUDO_KEEPALIVE_PID"; fi; fi' EXIT
    sudo -v
    if [[ ${INSTALL_APPROVED:-0} == 1 ]]; then
        (exec 9>&-; while sleep 45; do sudo -n -v || exit; done) &
        SUDO_KEEPALIVE_PID=$!
    fi
}
rpm_requirement_installed() {
    # DNF accepts both exact RPM names and virtual Provides (e.g. nodejs22
    # provides nodejs, and nodejs22-npm provides npm on Fedora 44).
    rpm -q "$1" >/dev/null 2>&1 || rpm -q --whatprovides "$1" >/dev/null 2>&1
}
packages() {
    local p; local missing=()
    for p in "$@"; do
        if ! rpm_requirement_installed "$p"; then missing+=("$p"); fi
    done
    if declare -F ui_status >/dev/null; then ui_status "Instalowanie: ${missing[*]:-pakiety już obecne}"; fi
    if ((${#missing[@]})); then run sudo dnf5 install "${missing[@]}" || return; fi
    for p in "$@"; do rpm_requirement_installed "$p" || die "Requested RPM was not installed: $p"; done
    printf '%s\n' "$@" >> "$RUN/expected-rpm"
}
atomic_config() {
    local source=$1 destination=$2 temporary
    mkdir -p "$(dirname "$destination")"
    temporary=$(mktemp "$(dirname "$destination")/.fedora-postinstall.XXXXXX") || return
    if ! install -m 600 "$source" "$temporary"; then rm -f -- "$temporary"; return 1; fi
    if ! mv -T -- "$temporary" "$destination"; then rm -f -- "$temporary"; return 1; fi
}
config_file() {
    local src=$1 dst=$2
    mkdir -p "$(dirname "$dst")"
    if [[ -e $dst || -L $dst ]]; then
        if ! cmp -s "$src" "$dst"; then
            cp -- "$src" "$dst.fedora-postinstall-new"
            log "Preserved $dst; proposed configuration: $dst.fedora-postinstall-new"
        fi
    else atomic_config "$src" "$dst"; fi
}
flatpak_app() {
    local id=$1
    if declare -F ui_status >/dev/null; then ui_status "Flatpak: $id"; fi
    packages flatpak
    if ! flatpak remote-list --user --columns=name | grep -Fxq flathub; then
        run flatpak remote-add --user flathub https://flathub.org/repo/flathub.flatpakrepo
    fi
    if ! flatpak info --user "$id" >/dev/null 2>&1; then
        # Flatpak does not accept piped confirmation reliably without a TTY.
        # The selected application module authorizes its required runtime too.
        run flatpak install --user --assumeyes --noninteractive flathub "$id"
    fi
    printf '%s\n' "$id" >> "$RUN/expected-flatpak"
}

consent() {
    if [[ ${INSTALL_APPROVED:-0} == 1 ]]; then log "Approved in summary: $*"; return 0; fi
    confirm "$@"
}
