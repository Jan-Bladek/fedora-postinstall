#!/usr/bin/env bash
# Full native desktop-tool installation only inside an ephemeral Fedora container.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if ((EUID == 0)); then
    dnf5 -y install sudo python3 git curl shadow-utils diffutils tar util-linux
    useradd -m experience-tester
    printf 'experience-tester ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/experience-test
    chmod 440 /etc/sudoers.d/experience-test
    exec sudo -H -u experience-tester env FEDORA_POSTINSTALL_TEST_TARGET=disposable bash "$ROOT/tests/experience.sh"
fi
source "$ROOT/lib/core.sh"
source "$ROOT/modules/terminal.sh"
source "$ROOT/modules/lazyvim.sh"
source "$ROOT/modules/vscode.sh"
source "$ROOT/modules/defaults.sh"
source "$ROOT/modules/files.sh"
source "$ROOT/modules/updates.sh"
RUN=$(mktemp -d)
CONFIG=$HOME/.config
STATE=$HOME/.local/state/fedora-postinstall
DESKTOP=dms
export INSTALL_APPROVED=1
mkdir -p "$CONFIG/btop" "$CONFIG/kitty" "$CONFIG/Code/User" "$STATE"
printf '# my terminal preference\nscrollback_lines 5555\n' > "$CONFIG/kitty/kitty.conf"
printf '{ // keep my setting\n "files.autoSave": "onFocusChange",\n}\n' > "$CONFIG/Code/User/settings.json"
printf 'theme_background = True\nupdate_ms = 1500\n' > "$CONFIG/btop/btop.conf"
module_terminal
module_terminal
grep -Fxq 'theme_background = False' "$CONFIG/btop/btop.conf"
grep -Fxq 'update_ms = 1500' "$CONFIG/btop/btop.conf"
[[ $(grep -c '^theme_background =' "$CONFIG/btop/btop.conf") == 1 ]]
module_files
module_files
[[ $(xdg-mime query default inode/directory) == org.gnome.Nautilus.desktop ]]
grep -q '^scrollback_lines 5555$' "$CONFIG/kitty/kitty.conf"
grep -q '^confirm_os_window_close 0$' "$CONFIG/kitty/kitty.conf"
[[ $(grep -c '^# BEGIN FEDORA-POSTINSTALL KITTY$' "$CONFIG/kitty/kitty.conf") == 1 ]]
fc-match 'JetBrains Mono'
fc-match 'Symbols Nerd Font Mono'
module_vscode
module_vscode
code --version
python3 - <<'PY'
import json
from pathlib import Path
assert json.loads(Path('/etc/vscode/policy.json').read_text())['TelemetryLevel'] == 'off'
s=json.loads((Path.home()/'.config/Code/User/settings.json').read_text())
assert s['files.autoSave'] == 'onFocusChange'
assert s['telemetry.telemetryLevel'] == 'off'
PY
module_defaults
[[ $(xdg-mime query default text/plain) == "$(code_desktop_id)" ]]
module_lazyvim
module_lazyvim
module_updates
before=$(sha256sum "$CONFIG/nvim/init.lua")
"$HOME/.local/bin/fedora-update" --yes
[[ $before == "$(sha256sum "$CONFIG/nvim/init.lua")" ]]
sudo dnf5 check
