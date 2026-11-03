#!/usr/bin/env bash
# One entrypoint for every source managed by this installer. Never upgrade
# arbitrary pip/npm projects or replace the user's Neovim configuration.
set -Eeuo pipefail
# Private logs/checkpoints already live in mode-700 directories. DNF state must
# remain readable to unprivileged check-upgrade.
umask 022
((EUID != 0)) || { echo 'Run as desktop user.' >&2; exit 1; }
# Invoked only by update-manager.py after locking and taking a checkpoint.
: "${FEDORA_UPDATE_RUN:?Use fedora-update}"
run=$FEDORA_UPDATE_RUN
state=${XDG_STATE_HOME:-$HOME/.local/state}/fedora-postinstall
export INSTALL_APPROVED=1
printf '\n::fedora-stage::[1/10] Fedora, COPR, repozytoria dostawców\n'
sudo dnf5 --assumeyes upgrade --refresh
printf '\n::fedora-stage::[2/10] Flatpak\n'
if command -v flatpak >/dev/null; then
    flatpak update --user --assumeyes --noninteractive
    sudo flatpak update --system --assumeyes --noninteractive
fi
printf '\n::fedora-stage::[3/10] Zarządzane archiwa JetBrains i Arduino AppImage\n'
python3 "$HOME/.local/share/fedora-postinstall/scripts/vendor-apps.py" update
printf '\n::fedora-stage::[4/10] Rustup (jeżeli używany)\n'
if command -v rustup >/dev/null 2>&1; then rustup update; fi
printf '\n::fedora-stage::[5/10] LazyVim — oficjalny lazy.nvim, bez git pull konfiguracji\n'
if [[ -f $state/managed/lazyvim ]]; then
    IFS= read -r nvim_config < "$state/managed/lazyvim"
    [[ $nvim_config == "${XDG_CONFIG_HOME:-$HOME/.config}/nvim" && -f $nvim_config/.fedora-postinstall-lazyvim ]] || {
        echo 'LazyVim config moved or changed ownership; review before updating.' >&2; exit 1;
    }
    if [[ -f $nvim_config/lazy-lock.json ]]; then cp -- "$nvim_config/lazy-lock.json" "$run/lazy-lock-before.json"; fi
    timeout 600 nvim --headless '+Lazy! check' +qa
    if ! timeout 600 nvim --headless '+Lazy! update' '+lua local ok, err = pcall(require, "lazyvim.config"); if not ok then vim.api.nvim_err_writeln(err); vim.cmd("cquit 1") end' +qa; then
        if [[ -f $run/lazy-lock-before.json ]]; then
            cp -- "$run/lazy-lock-before.json" "$nvim_config/lazy-lock.json"
            if ! timeout 600 nvim --headless '+Lazy! restore' '+lua local ok = pcall(require, "lazyvim.config"); if not ok then vim.cmd("cquit 1") end' +qa; then
                echo 'LazyVim restore also failed; the saved lockfile remains in the update log directory.' >&2; exit 1
            fi
        fi
        echo 'LazyVim update failed; previous lockfile restored when available.' >&2; exit 1
    fi
fi
printf '\n::fedora-stage::[6/10] Rozszerzenia VS Code\n'
if command -v code >/dev/null; then code --update-extensions; fi
printf '\n::fedora-stage::[7/10] Czcionki symboli Nerd Fonts\n'
python3 "$HOME/.local/share/fedora-postinstall/scripts/symbols-fonts.py" update
printf '\n::fedora-stage::[8/10] Omasnap — sprawdzona rewizja, bez pobierania Git HEAD\n'
python_helper=$HOME/.local/share/fedora-postinstall/scripts/omasnap-manager
if [[ -x $python_helper ]]; then "$python_helper" update; fi
printf '\n::fedora-stage::[9/10] Flea, Hyprmod i Zsh — zarządzane rewizje\n'
if [[ -x $HOME/.local/share/fedora-postinstall/scripts/flea-manager ]]; then
    "$HOME/.local/share/fedora-postinstall/scripts/flea-manager" update
fi
if [[ -f $state/managed/hyprmod ]]; then
    IFS= read -r revision < "$HOME/.local/share/fedora-postinstall/data/hyprmod-revision"
    [[ $revision =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid Hyprmod revision' >&2; exit 1; }
    uv tool install --python /usr/bin/python3 "git+https://github.com/BlueManCZ/hyprmod.git@$revision"
    "$HOME/.local/bin/hyprmod" --install
    printf '%s\n' "$revision" > "$state/managed/hyprmod"
fi
if [[ -f $state/managed/zsh ]]; then
    python3 "$HOME/.local/share/fedora-postinstall/scripts/zsh-manager.py" update
fi
printf '\n::fedora-stage::[10/10] Kontrola zależności\n'
sudo dnf5 check
echo "Aktualizacja zakończona. Log: $run/update.log"
echo 'DNF obejmuje RPM Noctalia/DMS i aktywne COPR. Własne pliki konfiguracji pozostają zachowane.'
