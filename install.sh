#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ROOT
source "$ROOT/lib/core.sh"
source "$ROOT/lib/desktop.sh"
DRY_RUN=0
EXPLICIT_MODULES=0
DESKTOP=''
MODULES='snapshots dependencies hyprland noctalia terminal development browsers multimedia utilities defaults optimization updates'
while (($#)); do
    case $1 in
        --version) cat "$ROOT/VERSION"; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --desktop) shift; DESKTOP=${1:?Missing desktop choice} ;;
        --modules) shift; MODULES=${1:?Missing module list}; EXPLICIT_MODULES=1 ;;
        --help) echo 'install.sh [--dry-run] [--desktop noctalia|dms|plasma] [--modules "snapshots dependencies hyprland noctalia dms terminal development browsers multimedia utilities defaults optimization updates kde-removal"]'; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done
if [[ -z $DESKTOP && -t 0 && $DRY_RUN == 0 && $EXPLICIT_MODULES == 0 ]]; then
    if command -v whiptail >/dev/null; then
        DESKTOP=$(whiptail --title 'Fedora Post-Install' --radiolist 'Choose desktop (Plasma is retained unless removal is explicitly selected)' 18 78 3 \
            noctalia 'Hyprland + Noctalia' ON dms 'Hyprland + DankMaterialShell / Dux Shell' OFF \
            plasma 'Keep KDE Plasma; install applications only' OFF 3>&1 1>&2 2>&3) || exit 0
    else
        echo 'Desktop: noctalia (Hyprland), dms (Hyprland), plasma (keep KDE).'
        read -r -p 'Choose desktop [noctalia], or EXIT: ' DESKTOP
        [[ $DESKTOP != EXIT ]] || exit 0
    fi
fi
if [[ -z $DESKTOP ]]; then
    DESKTOP=noctalia
    if [[ $EXPLICIT_MODULES == 1 && " $MODULES " =~ [[:space:]]dms[[:space:]] ]]; then DESKTOP=dms; fi
fi
# Explicit module lists retain their meaning; presets affect only default modules.
if ((EXPLICIT_MODULES == 0)); then MODULES=$(default_modules); fi
export DESKTOP
if [[ -t 0 && $DRY_RUN == 0 && $EXPLICIT_MODULES == 0 ]]; then
    if command -v whiptail >/dev/null; then
        items=()
        for module in $MODULES; do items+=("$module" "$module" ON); done
        if [[ $DESKTOP != plasma ]]; then items+=(kde-removal 'Remove Plasma AFTER session validation' OFF); fi
        MODULES=$(whiptail --title "Fedora · $DESKTOP" --separate-output --checklist 'Choose modules' 24 78 15 "${items[@]}" 3>&1 1>&2 2>&3) || exit 0
    else
        printf 'Fedora Post-Install · %s\nAvailable default modules:\n%s\n' "$DESKTOP" "$MODULES"
        if [[ $DESKTOP != plasma ]]; then echo 'Optional: kde-removal (requires a validated Hyprland session and separate confirmation).'; fi
        read -r -p 'Enter module names, press Enter for defaults, or type EXIT: ' selection
        [[ $selection != EXIT ]] || exit 0
        if [[ -n $selection ]]; then MODULES=$selection; fi
    fi
fi
# whiptail returns one module per line; verification uses a space-separated list.
MODULES=${MODULES//$'\n'/ }
[[ -n $MODULES ]] || exit 0
for module in $MODULES; do
    [[ -f $ROOT/modules/$module.sh && $module != */* ]] || die "Unknown module: $module"
done
validate_desktop_modules
preflight
if ((DRY_RUN)); then
    echo "PLAN Fedora 44 x86_64, desktop: $DESKTOP, modules: $MODULES"
    for module in $MODULES; do
        printf '\n[%s] Planned module (not executed):\n' "$module"
        cat "$ROOT/modules/$module.sh"
    done
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
if [[ $DESKTOP == plasma ]]; then
    log 'Finished. KDE Plasma retained; no Hyprland session configuration or Plasma removal was selected.'
else
    log 'Finished. Log into Hyprland, test lock/suspend/screenshare, then run scripts/validate-session.'
fi
