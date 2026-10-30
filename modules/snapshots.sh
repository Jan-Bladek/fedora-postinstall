#!/usr/bin/env bash
backup_state() {
    rpm -qa --qf '%{NEVRA}\n' | sort > "$RUN/packages-before.txt"
    systemctl list-unit-files > "$RUN/units-before.txt"
    findmnt -no SOURCE,FSTYPE,OPTIONS / > "$RUN/filesystem.txt"
    tar -C "$HOME" --exclude='.config/BraveSoftware' --exclude='.config/discord' -czf "$RUN/user-config.tar.gz" .config
    sudo tar -C / -czf "$RUN/etc.tar.gz" etc
    sudo chown "$(id -u):$(id -g)" "$RUN/etc.tar.gz"
    log "Recovery records: $RUN (may contain private data; never publish)"
}
module_snapshots() {
    if [[ $(findmnt -no FSTYPE /) != btrfs ]]; then log 'Not Btrfs: file backups only.'; return; fi
    packages snapper
    if sudo snapper -c root list >/dev/null 2>&1; then
        run sudo snapper -c root create --type single --description 'Before Fedora postinstall' --print-number
    elif confirm 'Configure Snapper root and create a snapshot? This does not add bootloader integration.'; then
        run sudo snapper -c root create-config /
        run sudo snapper -c root create --description 'Before Fedora postinstall' --print-number
    else log 'Snapper declined; file backups remain available.'; fi
}
