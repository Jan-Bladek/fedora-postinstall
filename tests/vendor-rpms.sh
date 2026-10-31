#!/usr/bin/env bash
# Real vendor RPM/default-app test in a disposable Fedora 44 user account.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable && $EUID != 0 ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/core.sh"
source "$ROOT/modules/browsers.sh"
source "$ROOT/modules/defaults.sh"
RUN=$(mktemp -d)
trap 'rm -rf -- "$RUN"' EXIT
module_browsers
vendor_repo vscodium https://repo.vscodium.dev/vscodium.repo
packages codium
vendor_repo tailscale https://pkgs.tailscale.com/stable/fedora/tailscale.repo
packages tailscale
module_defaults
for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do
    [[ $(xdg-mime query default "$type") == brave-browser.desktop ]]
done
[[ $(xdg-settings get default-web-browser) == brave-browser.desktop ]]
[[ $(xdg-mime query default text/plain) == codium.desktop ]]
rpm -q brave-browser librewolf codium tailscale
# A container is not a systemd boot test; the KVM workflow checks tailscaled.
tailscale version
sudo dnf5 check
