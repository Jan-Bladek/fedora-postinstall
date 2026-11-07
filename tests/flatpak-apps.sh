#!/usr/bin/env bash
# Disposable Fedora container/VM only; tests the real helper without a TTY.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable && $EUID != 0 ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID =~ ^(44|45)$ ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/core.sh"
RUN=$(mktemp -d)
trap 'rm -rf -- "$RUN"' EXIT
for app in dev.vencord.Vesktop com.valvesoftware.Steam md.obsidian.Obsidian org.localsend.localsend_app; do
    flatpak_app "$app" </dev/null
    flatpak info --user "$app"
done
# Exercise the already-installed path too, without fetching the applications again.
flatpak_app org.localsend.localsend_app </dev/null
flatpak list --user --app --columns=application,version
