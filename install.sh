#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ROOT
source "$ROOT/lib/core.sh"
source "$ROOT/lib/desktop.sh"
source "$ROOT/lib/ui.sh"
source "$ROOT/lib/development.sh"
if [[ -t 0 ]] && ! command -v whiptail >/dev/null && python3 -c 'import curses' 2>/dev/null; then
    whiptail() { python3 "$ROOT/scripts/tui.py" "$@"; }
fi
INSTALL_APPROVED=0
USE_PROGRESS=0
CLEANUP_APPS=''
APPLY_HYPR_PRESET=1
DEV_PROFILE=code
DRY_RUN=0
EXPLICIT_MODULES=0
DESKTOP=''
MODULES='snapshots dependencies hyprland noctalia terminal development browsers multimedia utilities defaults optimization updates'
while (($#)); do
    case $1 in
        --version) cat "$ROOT/VERSION"; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --yes) INSTALL_APPROVED=1 ;;
        --keep-hypr-config) APPLY_HYPR_PRESET=0 ;;
        --no-progress) USE_PROGRESS=-1 ;;
        --cleanup-apps) shift; CLEANUP_APPS=${1:?Missing application selection} ;;
        --dev-apps) shift; DEV_APPS=${1:?Missing development apps (use none for empty)}; [[ $DEV_APPS != none ]] || DEV_APPS='' ;;
        --dev-profile) shift; DEV_PROFILE=${1:?Missing development profile} ;;
        --desktop) shift; DESKTOP=${1:?Missing desktop choice} ;;
        --modules) shift; MODULES=${1:?Missing module list}; EXPLICIT_MODULES=1 ;;
        --help) echo 'install.sh [--dry-run] [--yes] [--no-progress] [--keep-hypr-config] [--cleanup-apps "all|id id"] [--desktop noctalia|dms|plasma] [--dev-profile code|full] [--dev-apps "code rustrover intellij-idea webstorm clion arduino-ide|none"] [--modules "snapshots dependencies hyprland noctalia dms terminal terminal-theme zsh clipboard lazyvim vscode development libreoffice hyprmod files omasnap browsers multimedia utilities defaults optimization updates cleanup kde-removal"]'; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done
if [[ -z $DESKTOP && -t 0 && $DRY_RUN == 0 && $EXPLICIT_MODULES == 0 && $INSTALL_APPROVED == 0 ]]; then
    if command -v whiptail >/dev/null; then
        DESKTOP=$(whiptail --title 'Fedora Post-Install' --radiolist 'Wybierz pulpit. Plasma pozostanie zainstalowana; czyszczenie aplikacji wybierzesz osobno.' 18 78 3 \
            noctalia 'Hyprland + Noctalia' ON dms 'Hyprland + DankMaterialShell / Dux Shell' OFF \
            plasma 'Zachowaj KDE Plasma; zainstaluj aplikacje' OFF 3>&1 1>&2 2>&3) || exit 0
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
if [[ -n $CLEANUP_APPS ]]; then
    if [[ ! " $MODULES " =~ [[:space:]]cleanup[[:space:]] ]]; then MODULES+=" cleanup"; fi
elif [[ -t 0 && $DRY_RUN == 0 && $EXPLICIT_MODULES == 0 && $INSTALL_APPROVED == 0 ]]; then
    ui_cleanup_choice
fi
if [[ -t 0 && $DRY_RUN == 0 && $EXPLICIT_MODULES == 0 && $INSTALL_APPROVED == 0 ]]; then
    ui_development_choice || exit 0
    ui_office_choice || exit 0
fi
case $DEV_PROFILE in code|full|custom) ;; *) die "Unknown development profile: $DEV_PROFILE" ;; esac
export DEV_PROFILE
resolve_dev_apps
# whiptail returns one module per line; verification uses a space-separated list.
MODULES=${MODULES//$'\n'/ }
[[ -n $MODULES ]] || exit 0
for module in $MODULES; do
    [[ -f $ROOT/modules/$module.sh && $module != */* ]] || die "Unknown module: $module"
done
validate_desktop_modules
if [[ -n $CLEANUP_APPS ]]; then
    read -r -a cleanup_keys <<< "$CLEANUP_APPS"
    python3 - "$ROOT" "${cleanup_keys[@]}" <<'PY_CHECK'
import runpy, sys
planner = runpy.run_path(sys.argv[1]+'/scripts/cleanup-plan.py')
planner['plan'](sys.argv[2:], [])
PY_CHECK
fi
preflight
if ((DRY_RUN)); then
    echo "PLAN Fedora 44 x86_64, desktop: $DESKTOP, development: $DEV_PROFILE ($DEV_APPS), modules: $MODULES"
    for module in $MODULES; do
        printf '\n[%s] Planned module (not executed):\n' "$module"
        cat "$ROOT/modules/$module.sh"
    done
    exit 0
fi
if [[ $INSTALL_APPROVED == 0 ]]; then
    if [[ -t 0 ]]; then ui_confirm_plan || exit 0
    else die 'Noninteractive installation requires --yes after reviewing --dry-run.'; fi
fi
INSTALL_APPROVED=1
export INSTALL_APPROVED CLEANUP_APPS APPLY_HYPR_PRESET
if [[ -t 0 && $USE_PROGRESS != -1 ]] && command -v whiptail >/dev/null &&
    [[ ! " $MODULES " =~ [[:space:]]kde-removal[[:space:]] ]]; then USE_PROGRESS=1; else USE_PROGRESS=0; fi
init_state
ui_start
# A recovery record is mandatory even when snapshot creation is deselected.
source "$ROOT/modules/snapshots.sh"
backup_state
module_index=0
read -r -a module_array <<< "$MODULES"
module_total=${#module_array[@]}
for module in $MODULES; do
    ui_status "Etap $((module_index+1))/$module_total: $module"
    log "MODULE $module"
    # shellcheck disable=SC1090
    source "$ROOT/modules/$module.sh"
    "module_${module//-/_}"
    printf '%s\n' "$module" >> "$STATE/completed.log"
    module_index=$((module_index+1))
    if [[ $USE_PROGRESS == 1 ]]; then printf '%s\n' "$((module_index*100/module_total))" > "$RUN/progress-percent"; fi
done
source "$ROOT/lib/verify.sh"
verify
if [[ $DESKTOP == plasma ]]; then
    log 'Finished. KDE Plasma retained; no Hyprland session configuration or Plasma removal was selected.'
else
    log 'Finished. Log into Hyprland, test lock/suspend/screenshare, then run scripts/validate-session.'
fi
