#!/usr/bin/env bash
module_vscode() {
    source "$ROOT/modules/repositories.sh"
    cat > "$RUN/vscode.repo" <<'REPO'
[code]
name=Visual Studio Code (Microsoft)
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
    install_reviewed_repo vscode "$RUN/vscode.repo"
    packages code
    python3 "$ROOT/scripts/merge-code-policy.py" /etc/vscode/policy.json "$RUN/code-policy.json"
    run sudo install -d -m 755 /etc/vscode
    run sudo install -m 644 "$RUN/code-policy.json" /etc/vscode/.policy-fedora-postinstall.json
    run sudo mv -T /etc/vscode/.policy-fedora-postinstall.json /etc/vscode/policy.json
    local settings=$CONFIG/Code/User/settings.json
    mkdir -p "$CONFIG/Code/User"
    if [[ -f $settings ]]; then cp -- "$settings" "$RUN/code-settings-before.jsonc"; fi
    python3 "$ROOT/scripts/merge-json.py" "$settings" "$ROOT/config/vscode/settings.json" "$RUN/code-settings.json"
    atomic_config "$RUN/code-settings.json" "$settings"
    log 'VS Code installed; TelemetryLevel=off is enforced by the Linux policy. Third-party extensions have independent privacy settings.'
}
