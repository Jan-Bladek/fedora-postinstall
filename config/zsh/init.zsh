# Fedora Post-Install: Oh My Zsh with Omarchy's Starship appearance.
# Source only from an interactive .zshrc.
export ZSH="$HOME/.local/share/fedora-postinstall/apps/zsh/current/ohmyzsh"
export ZSH_CUSTOM="$HOME/.local/share/fedora-postinstall/apps/zsh/current/custom"
ZSH_THEME=""
zstyle ':omz:update' mode disabled
plugins=(git fzf zsh-autosuggestions zsh-interactive-cd zsh-syntax-highlighting)
export EDITOR=nano VISUAL=nano SUDO_EDITOR=nano
export BAT_THEME=ansi
path=("$HOME/.local/bin" $path)
typeset -U path
source "$ZSH/oh-my-zsh.sh"
# Tab completion menu and familiar terminal navigation.
zmodload zsh/complist
zstyle ':completion:*' menu select
bindkey -e
# interactive-cd registers Tab itself; do not replace its widget.
bindkey '^I' zic-completion
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias g='git'
alias gcm='git commit -m'
alias gcam='git commit -a -m'
n() { if (( $# == 0 )); then nvim .; else nvim "$@"; fi; }
export STARSHIP_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fedora-postinstall/starship.toml"
eval "$("$HOME/.local/share/fedora-postinstall/apps/zsh/current/bin/starship" init zsh)"
