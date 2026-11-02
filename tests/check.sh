#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mapfile -t files < <(find . -type f -name '*.sh' -o -path './scripts/desktop-shell' -o -path './scripts/clipboard-history' -o -path './scripts/flea-manager' -o -path './scripts/omasnap-manager' -o -path './scripts/fedora-update' -o -path './scripts/validate-omasnap' -o -path './scripts/validate-session' -o -path './scripts/plan-plasma-removal')
for file in "${files[@]}"; do bash -n "$file"; done
shellcheck -x -e SC1091 "${files[@]}"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
