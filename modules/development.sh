#!/usr/bin/env bash
module_development() {
    source "$ROOT/modules/repositories.sh"
    vendor_repo vscodium https://repo.vscodium.dev/vscodium.repo
    packages codium fuse fuse-libs
    run python3 "$ROOT/scripts/vendor-apps.py" install
    log 'IDE licenses and Arduino board-specific udev rules require user setup. No blanket USB permissions applied.'
}
