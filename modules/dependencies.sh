#!/usr/bin/env bash
module_dependencies() {
    # Keep older installation media consistent with today's dependency graph.
    # In particular, Fedora's kmime co-installability fix must precede kf6-kmime.
    log 'Updating installed Fedora packages before adding the desktop and applications; review the DNF transaction.'
    run sudo dnf5 upgrade --refresh
    packages diffutils bash git curl wget2-wget tar unzip zip xz bzip2 7zip jq pciutils usbutils iproute bind-utils traceroute lsof strace btop wl-clipboard xdg-utils util-linux newt python3 python3-pip lua
    run /usr/bin/python3 --version
    run /usr/bin/python3 -m pip --version
}
