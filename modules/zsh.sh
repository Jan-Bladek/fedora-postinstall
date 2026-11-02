#!/usr/bin/env bash
module_zsh() {
    packages zsh fzf git python3 nano
    local dest=$HOME/.local/share/fedora-postinstall rc=${ZDOTDIR:-$HOME}/.zshrc
    mkdir -p "$dest/scripts" "$dest/data"
    install -m 755 "$ROOT/scripts/zsh-manager.py" "$dest/scripts/zsh-manager.py"
    install -m 644 "$ROOT/data/zsh-sources.json" "$dest/data/zsh-sources.json"
    install -m 644 "$ROOT/config/zsh/init.zsh" "$dest/data/zsh-init.zsh"
    run python3 "$dest/scripts/zsh-manager.py" install
    config_file "$ROOT/config/zsh/starship.toml" "$CONFIG/fedora-postinstall/starship.toml"
    if [[ -f $rc ]]; then cp -- "$rc" "$RUN/zshrc-before"; fi
    # shellcheck disable=SC2016 # Keep HOME expansion for the user's Zsh startup.
    printf '%s\n' 'source "$HOME/.local/share/fedora-postinstall/apps/zsh/current/init.zsh"' > "$RUN/zsh-block"
    python3 "$ROOT/scripts/merge-config-block.py" "$rc" "$RUN/zsh-block" "$RUN/zshrc" ZSH
    run zsh -n "$RUN/zshrc"
    atomic_config "$RUN/zshrc" "$rc"
    mkdir -p "$STATE/managed"
    printf '%s\n' "$rc" > "$STATE/managed/zsh"
    if [[ $(getent passwd "$USER" | cut -d: -f7) != /bin/zsh ]]; then run sudo usermod --shell /bin/zsh "$USER"; fi
    log 'Zsh + Oh My Zsh configured with autosuggestions, syntax highlighting, interactive cd and the Omarchy Starship prompt. Nano remains EDITOR/VISUAL. Open a new terminal.'
}
