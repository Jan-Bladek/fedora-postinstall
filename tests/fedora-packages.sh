#!/usr/bin/env bash
# Destructive integration fixture: only a disposable VM/container, never the host.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable ]] || { echo 'Set FEDORA_POSTINSTALL_TEST_TARGET=disposable inside a disposable guest.' >&2; exit 1; }
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 && $EUID == 0 ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/modules/dependencies.sh"
source "$ROOT/lib/development.sh"
source "$ROOT/modules/development.sh"
DEV_APPS="rustrover clion webstorm"
packages() { dnf5 -y install "$@"; }
log() { printf '%s\n' "$*"; }
run() {
    # This explicitly disposable fixture already runs as root, including in
    # minimal Fedora containers where sudo is not installed.
    if [[ $1 == sudo ]]; then shift; fi
    if [[ $1 == dnf5 ]]; then shift; dnf5 -y "$@"; else "$@"; fi
}
module_dependencies
packages polkit-kde noctalia python3-pip
install_language_tools
test -x /usr/libexec/kf6/polkit-kde-authentication-agent-1
command -v wget
command -v 7z
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
python3 -m venv "$work/venv"
"$work/venv/bin/python" -m pip --version
printf '#include <iostream>\nint main(){std::cout << "cpp-ok";}\n' > "$work/main.cpp"
g++ "$work/main.cpp" -o "$work/cpp"
[[ $("$work/cpp") == cpp-ok ]]
printf 'fn main(){println!("rust-ok");}\n' > "$work/main.rs"
rustc "$work/main.rs" -o "$work/rust"
[[ $("$work/rust") == rust-ok ]]
dnf5 check
