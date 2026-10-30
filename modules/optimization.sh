#!/usr/bin/env bash
module_optimization() {
    log 'Retaining Fedora power management, zram, SELinux and security services. No speculative service disabling.'
    run systemd-analyze
    run lspci -k
    log 'NVIDIA proprietary drivers/codecs are hardware-specific and are not silently installed. HiDPI uses preferred auto scale.'
}
