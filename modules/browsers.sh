#!/usr/bin/env bash
module_browsers() {
    source "$ROOT/modules/repositories.sh"
    vendor_repo brave-browser https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo
    packages brave-browser
    # The official LibreWolf repo endpoint is checked at runtime; fail rather than substitute.
    vendor_repo librewolf https://repo.librewolf.net/librewolf.repo
    packages librewolf
}
