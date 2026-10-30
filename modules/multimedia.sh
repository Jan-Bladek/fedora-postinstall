#!/usr/bin/env bash
module_multimedia() {
    packages obs-studio
    flatpak_app dev.vencord.Vesktop
    flatpak_app com.valvesoftware.Steam
    log 'OBS: choose PipeWire screen capture. Steam uses Flathub to avoid enabling RPM Fusion for one app.'
}
