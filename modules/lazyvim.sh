#!/usr/bin/env bash
module_lazyvim() {
    local revision destination=$CONFIG/nvim work=$RUN/lazyvim-starter
    packages neovim git ripgrep fd-find tree-sitter-cli gcc make unzip
    run nvim --headless -u NONE '+lua if vim.fn.has("nvim-0.11.2") ~= 1 then vim.api.nvim_err_writeln("LazyVim requires Neovim >=0.11.2"); vim.cmd("cquit 1") end' +qa
    if [[ -e $destination || -L $destination ]]; then
        if [[ ! -f $destination/.fedora-postinstall-lazyvim ]]; then
            local stamp backup original
            stamp=$(date +%Y%m%dT%H%M%S)-$$
            for original in "$destination" "${XDG_DATA_HOME:-$HOME/.local/share}/nvim" "${XDG_STATE_HOME:-$HOME/.local/state}/nvim" "${XDG_CACHE_HOME:-$HOME/.cache}/nvim"; do
                if [[ -e $original || -L $original ]]; then
                    backup=$original.pre-fedora-postinstall-$stamp
                    mv -- "$original" "$backup"
                    printf '%s\t%s\n' "$original" "$backup" >> "$RUN/lazyvim-backups.tsv"
                fi
            done
        fi
    fi
    if [[ ! -e $destination && ! -L $destination ]]; then
        revision=$(cat "$ROOT/data/lazyvim-starter-revision")
        [[ $revision =~ ^[0-9a-f]{40}$ ]] || die 'Invalid LazyVim starter revision.'
        run git clone --no-checkout https://github.com/LazyVim/starter.git "$work"
        run git -C "$work" checkout --detach "$revision"
        mkdir -p "$destination"
        (cd "$work" && tar --exclude=.git -cf - .) | tar -C "$destination" -xf -
        printf '%s\n' "$revision" > "$destination/.fedora-postinstall-lazyvim"
    fi
    if declare -F ui_status >/dev/null; then ui_status "LazyVim — instalowanie i sprawdzanie wtyczek"; fi
    run timeout 600 nvim --headless '+Lazy! sync' '+lua local ok, err = pcall(require, "lazyvim.config"); if not ok then vim.api.nvim_err_writeln(err); vim.cmd("cquit 1") end' +qa
    mkdir -p "$STATE/managed"
    printf '%s\n' "$destination" > "$STATE/managed/lazyvim"
    log 'LazyVim installed through its official starter and lazy.nvim. Run :LazyHealth for optional providers.'
}
