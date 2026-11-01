#!/usr/bin/env bash
module_noctalia() {
    packages noctalia brightnessctl
    select_shell noctalia
    log 'Noctalia v5 native package; first-run settings remain vendor defaults. No v4 migration.'
}
