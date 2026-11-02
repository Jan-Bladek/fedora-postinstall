#!/usr/bin/env bash
# Destructive fixture. Never run on the user's installed workstation.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if ((EUID == 0)); then
    dnf5 -y install python3 sudo diffutils shadow-utils
    mapfile -t apps < <(python3 - "$ROOT" <<'PY'
import runpy, sys
catalog=runpy.run_path(sys.argv[1]+'/scripts/cleanup-plan.py')['groups']()
print('\n'.join(sorted({p for _, packages in catalog.values() for p in packages if not p.startswith('@')})))
PY
)
    dnf5 -y install plasma-desktop plasma-workspace uwsm dolphin okular kwrite libreoffice-writer libreoffice-calc "${apps[@]}"
    useradd -m cleanup-tester
    printf 'cleanup-tester ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/cleanup-test
    chmod 440 /etc/sudoers.d/cleanup-test
    exec sudo -H -u cleanup-tester env FEDORA_POSTINSTALL_TEST_TARGET=disposable bash "$ROOT/tests/cleanup-packages.sh"
fi
source "$ROOT/lib/core.sh"
source "$ROOT/modules/cleanup.sh"
RUN=$(mktemp -d)
CONFIG=$HOME/.config
CLEANUP_APPS=all
export INSTALL_APPROVED=1
mkdir -p "$CONFIG" "$HOME/Documents"
printf 'keep-user-data\n' > "$HOME/Documents/keep.txt"
rpm -q plasma-desktop plasma-workspace uwsm dolphin okular kwrite qt6-qtbase > "$RUN/protected-before"
module_cleanup
module_cleanup
rpm -q plasma-desktop plasma-workspace uwsm dolphin okular kwrite qt6-qtbase > "$RUN/protected-after"
cmp "$RUN/protected-before" "$RUN/protected-after"
[[ $(cat "$HOME/Documents/keep.txt") == keep-user-data ]]
grep -Fxq 'NoDisplay=true' "$HOME/.local/share/applications/uuctl.desktop"
if rpm -q firefox libreoffice-writer kmail kde-connect >/dev/null 2>&1; then exit 1; fi
printf 'Application cleanup, repeat and retained desktop validation passed.\n'
sudo dnf5 check
