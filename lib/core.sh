#!/usr/bin/env bash
log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }
die() { echo "ERROR: $*" >&2; exit 1; }
run() { log "$(printf '%q ' "$@")"; "$@"; }
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
    exec > >(tee -a "$RUN/install.log") 2>&1
    # shellcheck disable=SC2154
    trap 'rc=$?; echo "Interrupted/failed (exit $rc). Recovery: see README and $RUN" >&2; exit "$rc"' ERR
    trap 'exit 130' INT
    sudo -v
}
packages() {
    local p; local missing=()
    for p in "$@"; do
        printf '%s\n' "$p" >> "$STATE/expected-rpm"
        if ! rpm -q "$p" >/dev/null 2>&1; then missing+=("$p"); fi
    done
    if ((${#missing[@]})); then run sudo dnf5 install "${missing[@]}"; fi
}
config_file() {
    local src=$1 dst=$2
    mkdir -p "$(dirname "$dst")"
    if [[ -e $dst || -L $dst ]]; then
        if ! cmp -s "$src" "$dst"; then
            cp -- "$src" "$dst.fedora-postinstall-new"
            log "Preserved $dst; proposed configuration: $dst.fedora-postinstall-new"
        fi
    else install -m 600 "$src" "$dst"; fi
}
flatpak_app() {
    local id=$1
    packages flatpak
    if ! flatpak remote-list --user --columns=name | grep -Fxq flathub; then
        run flatpak remote-add --user flathub https://flathub.org/repo/flathub.flatpakrepo
    fi
    if ! flatpak info --user "$id" >/dev/null 2>&1; then run flatpak install --user flathub "$id"; fi
    printf '%s\n' "$id" >> "$STATE/expected-flatpak"
}
