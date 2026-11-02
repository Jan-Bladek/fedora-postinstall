#!/usr/bin/env bash
module_files() {
    packages nautilus xdg-utils
    run xdg-mime default org.gnome.Nautilus.desktop inode/directory
    [[ $(xdg-mime query default inode/directory) == org.gnome.Nautilus.desktop ]] || die 'Nautilus default verification failed.'
}
