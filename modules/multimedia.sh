#!/usr/bin/env bash
configure_obs_codecs() {
    if ! rpm -q openh264 >/dev/null 2>&1; then
        local available dependencies dependents
        if rpm -q noopenh264 >/dev/null 2>&1; then
            dependencies=$(rpm -qa --qf '%{NAME}\t[%{REQUIRENAME} ]\n') || return
            dependents=$(awk -F '\t' '$2 ~ /(^|[^[:alnum:]_+.-])noopenh264([^[:alnum:]_+.-]|$)/ {print $1}' <<< "$dependencies") || return
            [[ -z $dependents ]] || die "Retained packages explicitly require the placeholder; review before replacing it: $dependents"
        fi
        log 'OBS H.264 requires the real codec, not Fedora noopenh264. Using the Fedora/Cisco repository shipped by Fedora.'
        available=$(sudo dnf5 --repo=fedora-cisco-openh264 --setopt=fedora-cisco-openh264.gpgcheck=1 -q repoquery --available openh264) || return
        [[ -n $available ]] || die 'OpenH264 is unavailable in the Fedora/Cisco repository; H.264 recording cannot be verified.'
        if rpm -q noopenh264 >/dev/null 2>&1; then
            # Replace this exact stub; retain other dependencies and skip unrelated
            # weak recommendations (e.g. a Firefox plugin). Never use allowerasing.
            run sudo dnf5 --repo=fedora-cisco-openh264 --setopt=fedora-cisco-openh264.gpgcheck=1 \
                --setopt=clean_requirements_on_remove=False --setopt=install_weak_deps=False \
                swap noopenh264 openh264 || return
        else
            run sudo dnf5 --repo=fedora-cisco-openh264 --setopt=fedora-cisco-openh264.gpgcheck=1 \
                --setopt=install_weak_deps=False install openh264 || return
        fi
    fi
    packages ffmpeg-free
    rpm -q openh264 >/dev/null || die 'The real OpenH264 RPM was not installed.'
    if rpm -q noopenh264 >/dev/null 2>&1; then die 'The nonfunctional OpenH264 placeholder is still installed.'; fi
    packages openh264
    # Encoder enumeration also lists the stub. Actually encode a synthetic frame;
    # this does not capture user content or modify an existing OBS profile.
    run ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i color=size=32x32:rate=1 \
        -frames:v 1 -c:v libopenh264 -an -f null -
}

module_multimedia() {
    packages obs-studio
    configure_obs_codecs
    flatpak_app dev.vencord.Vesktop
    flatpak_app com.valvesoftware.Steam
    log 'OBS: choose PipeWire screen capture. Steam uses Flathub to avoid enabling RPM Fusion for one app.'
}
