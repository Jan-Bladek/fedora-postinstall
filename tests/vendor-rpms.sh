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
# Match install.sh's init_state: a fresh container account has no .config yet.
CONFIG=${XDG_CONFIG_HOME:-$HOME/.config}
mkdir -p "$CONFIG"
module_browsers
vendor_repo vscodium https://repo.vscodium.dev/vscodium.repo
packages codium
vendor_repo tailscale https://pkgs.tailscale.com/stable/fedora/tailscale.repo
packages tailscale
module_defaults
cat "$CONFIG/mimeapps.list"
find /usr/share/applications -maxdepth 1 -name '*brave*' -print
for type in x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml; do
    actual=$(xdg-mime query default "$type")
    printf 'Default for %s: <%s>\n' "$type" "$actual"
    [[ $actual == brave-browser.desktop ]] || die "Wrong browser association: $type"
done
actual=$(xdg-settings get default-web-browser)
printf 'Default web browser: <%s>\n' "$actual"
[[ $actual == brave-browser.desktop ]] || die 'Wrong xdg-settings browser'
actual=$(xdg-mime query default text/plain)
printf 'Default text editor: <%s>\n' "$actual"
desktop=$(codium_desktop_id)
[[ $actual == "$desktop" ]] || die 'Wrong text editor association'
rpm -qf "/usr/share/applications/$actual"
rpm -q brave-browser librewolf codium tailscale
# A container is not a systemd boot test; the KVM workflow checks tailscaled.
tailscale version
sudo dnf5 check
