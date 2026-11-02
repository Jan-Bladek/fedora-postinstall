#!/usr/bin/env bash
install_language_tools() {
    if dev_selected rustrover; then
        if command -v rustup >/dev/null 2>&1; then
            run rustup toolchain install stable --profile default --component rust-src
            run rustup run stable rustc --version
            run rustup run stable cargo --version
        else
            packages rust cargo clippy rustfmt rust-src
            run rustc --version
            run cargo --version
        fi
    fi
    if dev_selected clion; then
        packages gcc gcc-c++ make cmake ninja-build gdb pkgconf-pkg-config
        run g++ --version
    fi
    if dev_selected webstorm; then packages nodejs npm; fi
    # IntelliJ bundles its runtime; additional project SDKs are user choices.
    return 0
}
module_development() {
    source "$ROOT/lib/development.sh"
    resolve_dev_apps
    install_language_tools
    if dev_selected code; then
        source "$ROOT/modules/vscode.sh"
        module_vscode
    fi
    if dev_selected arduino-ide; then packages fuse fuse-libs; fi
    local app
    local -a vendor_apps=()
    for app in $DEV_APPS; do [[ $app == code ]] || vendor_apps+=("$app"); done
    if ((${#vendor_apps[@]})); then
        run python3 "$ROOT/scripts/vendor-apps.py" install "${vendor_apps[@]}"
    fi
    log 'Only selected IDEs and their development tools were installed. Existing SDKs are retained.'
}
