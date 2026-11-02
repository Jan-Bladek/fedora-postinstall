#!/usr/bin/env bash
# Compiles upstream and checks installation only in a disposable Fedora fixture.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if ((EUID == 0)); then
    dnf5 -y install sudo python3 git curl shadow-utils diffutils
    source "$ROOT/lib/core.sh"
    source "$ROOT/modules/repositories.sh"
    RUN=$(mktemp -d)
    INSTALL_APPROVED=1
    vendor_repo hyprland-copr "https://copr.fedorainfracloud.org/coprs/lionheartp/Hyprland/repo/fedora-$VERSION_ID/lionheartp-Hyprland-fedora-$VERSION_ID.repo"
    dnf5 -y install hyprland
    useradd -m omasnap-tester
    printf 'omasnap-tester ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/omasnap-test
    chmod 440 /etc/sudoers.d/omasnap-test
    exec sudo -H -u omasnap-tester env FEDORA_POSTINSTALL_TEST_TARGET=disposable bash "$ROOT/tests/omasnap-packages.sh"
fi
source "$ROOT/lib/core.sh"
source "$ROOT/modules/omasnap.sh"
RUN=$(mktemp -d)
CONFIG=$HOME/.config
DESKTOP=noctalia
export INSTALL_APPROVED=1
mkdir -p "$CONFIG/hypr"
printf '%s\n' '-- custom imported file' 'hl.config({ misc = { disable_hyprland_logo = true } })' > "$CONFIG/hypr/personal.lua"
cat > "$CONFIG/hypr/hyprland.lua" <<'LUA'
-- keep my personal Hyprland config
dofile((os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/hypr/personal.lua")
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.bind("PRINT", hl.dsp.exec_cmd("old-screenshot"))
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd("old-editor"))
hl.bind("SUPER + X", hl.dsp.exec_cmd("my-personal-app"))
LUA
module_omasnap
payload=$(readlink "$HOME/.local/share/fedora-postinstall/apps/omasnap/current")
module_omasnap
[[ $payload == "$(readlink "$HOME/.local/share/fedora-postinstall/apps/omasnap/current")" ]]
grep -Fxq -- '-- keep my personal Hyprland config' "$CONFIG/hypr/hyprland.lua"
grep -Fq 'my-personal-app' "$CONFIG/hypr/hyprland.lua"
[[ $(grep -c '^-- BEGIN FEDORA-POSTINSTALL OMASNAP$' "$CONFIG/hypr/hyprland.lua") == 1 ]]
"$HOME/.local/share/fedora-postinstall/scripts/omasnap-manager" update
"$HOME/.local/share/fedora-postinstall/scripts/omasnap-manager" check
sudo dnf5 check
echo 'Omasnap source build, upstream smoke tests, repeated install, config preservation and parser validation passed.'
