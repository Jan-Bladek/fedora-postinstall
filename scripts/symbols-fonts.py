#!/usr/bin/env python3
"""Install/update upstream Nerd Font symbols with GitHub's published SHA256."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import zipfile


def main(mode):
    if os.geteuid() == 0:
        raise SystemExit('Run as desktop user')
    base = Path.home()/'.local/share/fedora-postinstall/fonts/symbols'
    receipt = base/'origin.json'
    if mode == 'update' and not receipt.exists():
        return
    fetch = runpy.run_path(str(Path(__file__).with_name('vendor-apps.py')))['fetch']
    release = json.loads(fetch('https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest'))
    asset = next(a for a in release['assets'] if a['name'] == 'NerdFontsSymbolsOnly.zip')
    version, digest = release['tag_name'], asset.get('digest', '')
    if not re.fullmatch(r'[A-Za-z0-9._+-]+', version) or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Refusing font release without a SHA256 digest')
    target = base/version/'SymbolsNerdFontMono-Regular.ttf'
    if not target.exists():
        blob = fetch(asset['browser_download_url'])
        if hashlib.sha256(blob).hexdigest() != digest[7:]:
            raise ValueError('Nerd Font checksum mismatch')
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            member = next(n for n in archive.namelist() if n.split('/')[-1] == target.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    dest = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'fonts/fedora-postinstall-symbols.ttf'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not dest.is_symlink():
        raise ValueError('User font collision; refusing to overwrite')
    if dest.is_symlink():
        if not dest.readlink().is_relative_to(base):
            raise ValueError('Unmanaged font symlink; refusing to overwrite')
        dest.unlink()
    dest.symlink_to(target)
    receipt.write_text(json.dumps({'version': version, 'url': asset['browser_download_url'], 'sha256': digest[7:]}, indent=2)+'\n')
    if shutil.which('fc-cache'):
        subprocess.run(['fc-cache', '-f'], check=True)
    print('Nerd Font symbols:', version)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('install', 'update'):
        raise SystemExit('Usage: symbols-fonts.py install|update')
    main(sys.argv[1])
