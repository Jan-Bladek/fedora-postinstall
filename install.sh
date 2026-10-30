#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ROOT
source "$ROOT/lib/core.sh"
DRY_RUN=0
MODULES='snapshots dependencies hyprland noctalia terminal development browsers multimedia utilities defaults optimization updates'
while (($#)); do
    case $1 in
        --dry-run) DRY_RUN=1 ;;
        --modules) shift; MODULES=${1:?Missing module list} ;;
        --help) echo 'install.sh [--dry-run] [--modules "snapshots dependencies hyprland noctalia terminal development browsers multimedia utilities defaults optimization updates kde-removal"]'; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done
for module in $MODULES; do
    [[ -f $ROOT/modules/$module.sh && $module != */* ]] || die "Unknown module: $module"
done
if [[ -t 0 && $DRY_RUN == 0 ]] && command -v whiptail >/dev/null; then
    items=()
    for module in $MODULES; do items+=("$module" "$module" ON); done
    items+=(kde-removal 'Remove Plasma AFTER session validation' OFF)
    MODULES=$(whiptail --title 'Fedora · Hyprland + Noctalia' --separate-output --checklist 'Choose modules' 24 78 15 "${items[@]}" 3>&1 1>&2 2>&3) || exit 0
fi
preflight
if ((DRY_RUN)); then
    echo "PLAN Fedora 44 x86_64, modules: $MODULES"
    for module in $MODULES; do cat "$ROOT/plans/$module.txt"; done
    exit 0
fi
init_state
# A recovery record is mandatory even when snapshot creation is deselected.
source "$ROOT/modules/snapshots.sh"
backup_state
for module in $MODULES; do
    log "MODULE $module"
    # shellcheck disable=SC1090
    source "$ROOT/modules/$module.sh"
    "module_${module//-/_}"
    printf '%s\n' "$module" >> "$STATE/completed.log"
done
source "$ROOT/lib/verify.sh"
verify
log 'Finished. Log into Hyprland, test lock/suspend/screenshare, then run scripts/validate-session.'
