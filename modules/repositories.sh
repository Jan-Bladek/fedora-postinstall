#!/usr/bin/env bash
vendor_repo() {
    local name=$1 url=$2 file
    file=$RUN/$name.repo
    run curl --proto '=https' --tlsv1.2 -fL "$url" -o "$file"
    # Parse as data; never source a downloaded repository definition.
    python3 "$ROOT/scripts/check-repo.py" "$name" "$file"
    cat "$file"
    if [[ -f /etc/yum.repos.d/$name.repo ]]; then
        cmp -s "$file" "/etc/yum.repos.d/$name.repo" || die "Existing $name.repo differs; review manually."
    else
        confirm "Trust displayed $name repository and its signing key?" || die 'Repository declined.'
        run sudo install -m 644 "$file" "/etc/yum.repos.d/$name.repo"
    fi
    run sudo dnf5 --refresh makecache
}
