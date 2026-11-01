#!/usr/bin/env bash
# Only execute in a disposable Fedora 44 CI container, never on the workstation.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/core.sh"
source "$ROOT/lib/desktop.sh"
source "$ROOT/modules/dms.sh"
if ((EUID == 0)); then
    dnf5 -y install curl python3 sudo
    useradd -m dms-tester
    printf 'dms-tester ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/dms-test
    chmod 440 /etc/sudoers.d/dms-test
    exec sudo -H -u dms-tester env FEDORA_POSTINSTALL_TEST_TARGET=disposable bash "$ROOT/tests/dms-packages.sh"
fi
RUN=$(mktemp -d)
CONFIG=$RUN/config
export XDG_CONFIG_HOME=$CONFIG
trap 'rm -rf -- "$RUN"' EXIT
mkdir -p "$CONFIG"
run() {
    if [[ $1 == sudo && $2 == dnf5 ]]; then shift 2; sudo dnf5 -y "$@"; else "$@"; fi
}
# Trust only for this ephemeral CI fixture; real installers ask the user.
confirm() { echo "Disposable fixture acceptance: $*"; }
module_dms
module_dms
[[ $("$ROOT/scripts/desktop-shell" name) == dms ]]
rpm -q dms
command -v dms
dms ipc --help
sudo dnf5 check
# Do not pretend a container is a running Wayland session.
