#!/usr/bin/env bash
# Build vendored Flea sources. Retain existing SDKs; remove only Rust packages
# introduced for this build, with RPM dependency checks and no autoremove.
set -Eeuo pipefail
work=$(mktemp -d)
cleanup() {
    local status=$? package
    local -a added=()
    trap - EXIT
    if [[ -f $work/before ]]; then
        if rpm -qa --qf '%{NAME}\n' | sort -u > "$work/after"; then
            while IFS= read -r package; do
                if [[ $package =~ ^(rust|cargo)($|-) ]]; then added+=("$package"); fi
            done < <(comm -13 "$work/before" "$work/after")
            if ((${#added[@]})); then
                if ! sudo rpm -e --test "${added[@]}" || ! sudo rpm -e "${added[@]}"; then
                    echo 'Temporary Rust toolchain could not be removed; review the logged dependency error.' >&2
                    status=1
                fi
            fi
        else
            status=1
        fi
    fi
    rm -rf -- "$work"
    exit "$status"
}
trap cleanup EXIT
if ! command -v cargo >/dev/null; then
    rpm -qa --qf '%{NAME}\n' | sort -u > "$work/before"
    sudo dnf5 --assumeyes install rust cargo
fi
CARGO_BUILD_JOBS=2 cargo build --release --locked --offline
CARGO_BUILD_JOBS=2 cargo test --locked --offline -- --test-threads=2
