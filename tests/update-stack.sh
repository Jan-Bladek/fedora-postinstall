#!/usr/bin/env bash
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable && $EUID != 0 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/core.sh"
source "$ROOT/modules/updates.sh"
source "$ROOT/modules/defaults.sh"
RUN=$(mktemp -d)
trap 'rm -rf -- "$RUN"' EXIT
module_updates
"$HOME/.local/bin/fedora-update" --yes
for app in dev.vencord.Vesktop com.valvesoftware.Steam md.obsidian.Obsidian app.localsend.localsend_app; do
    flatpak info --user "$app" >/dev/null
done
[[ $(xdg-mime query default text/plain) == "$(code_desktop_id)" ]]
[[ $(xdg-settings get default-web-browser) == brave-browser.desktop ]]
printf 'Unified update retained installed apps and default associations.\n'
