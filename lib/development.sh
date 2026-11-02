#!/usr/bin/env bash
# Explicit application selection drives optional SDK installation.
resolve_dev_apps() {
    if [[ ${DEV_APPS+x} != x ]]; then
        case ${DEV_PROFILE:-code} in
            code) DEV_APPS=code ;;
            full) DEV_APPS='code rustrover intellij-idea webstorm clion arduino-ide' ;;
            *) die 'Unknown development profile.' ;;
        esac
    fi
    local app
    DEV_APPS=${DEV_APPS//$'\n'/ }
    DEV_APPS=${DEV_APPS//\"/}
    for app in $DEV_APPS; do
        case $app in code|rustrover|intellij-idea|webstorm|clion|arduino-ide) ;; *) die "Unknown development app: $app" ;; esac
    done
    export DEV_APPS
}
dev_selected() { [[ " ${DEV_APPS-code} " == *" $1 "* ]]; }
