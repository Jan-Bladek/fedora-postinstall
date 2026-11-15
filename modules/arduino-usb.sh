#!/usr/bin/env bash
module_arduino_usb() {
    local account target=/etc/udev/rules.d/60-fedora-postinstall-arduino.rules
    packages systemd-udev shadow-utils
    account=$(id -un)
    [[ $account != root ]] || die 'Configure Arduino USB access as the desktop user.'
    getent group dialout >/dev/null || die 'Fedora dialout group is missing; serial permissions were not changed.'
    [[ ! -L $target ]] || die 'Refusing to overwrite a symlink at the Arduino udev rules path.'
    if [[ -f $target ]]; then
        sudo cat "$target" | tee "$RUN/arduino-udev-before.rules" >/dev/null
    fi
    run udevadm verify "$ROOT/config/udev/60-fedora-postinstall-arduino.rules"
    run sudo install -D -m 644 "$ROOT/config/udev/60-fedora-postinstall-arduino.rules" "$target"
    run sudo udevadm control --reload-rules
    if ! id -nG "$account" | tr ' ' '\n' | grep -Fxq dialout; then
        run sudo usermod -aG dialout "$account"
    fi
    id -nG "$account" | tr ' ' '\n' | grep -Fxq dialout || die 'Arduino serial group membership was not saved.'
    log 'Arduino USB access configured. Log out and back in, then unplug/reconnect the board. Run the IDE without sudo.'
}
