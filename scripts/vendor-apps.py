#!/usr/bin/env python3
"""Versioned official vendor downloads. No remote installers, Git HEAD or root execution."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE = Path.home() / '.local/share/fedora-postinstall/apps'
BIN = Path.home() / '.local/bin'
DESKTOP = Path.home() / '.local/share/applications'
HOSTS = {'data.services.jetbrains.com', 'download.jetbrains.com', 'download-cdn.jetbrains.com',
         'download-cf.jetbrains.com', 'api.github.com', 'github.com',
         'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}

def fetch(url):
    u = urlparse(url)
    if u.scheme != 'https' or u.hostname not in HOSTS:
        raise ValueError(f'Untrusted URL: {url}')
    with urlopen(Request(url, headers={'User-Agent': 'fedora-postinstall'}), timeout=90) as response:
        if urlparse(response.url).scheme != 'https' or urlparse(response.url).hostname not in HOSTS:
            raise ValueError('Unexpected download redirect')
        return response.read()

def jetbrains(code):
    data = json.loads(fetch(f'https://data.services.jetbrains.com/products/releases?code={code}&latest=true&type=release'))
    release = data[code][0]
    asset = release['downloads']['linux']
    digest = fetch(asset['checksumLink']).decode().split()[0]
    return release['version'], asset['link'], digest

def arduino():
    release = json.loads(fetch('https://api.github.com/repos/arduino/arduino-ide/releases/latest'))
    asset = next(a for a in release['assets'] if a['name'].endswith('_Linux_64bit.AppImage'))
    digest = asset.get('digest', '')
    if not digest.startswith('sha256:'):
        raise ValueError('Arduino release has no authenticated SHA256 digest; refusing unverified binary')
    return release['tag_name'], asset['browser_download_url'], digest[7:]

def install(name, metadata, launcher):
    version, url, digest = metadata
    if not re.fullmatch(r'[A-Za-z0-9._+-]+', version) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest):
        raise ValueError('Invalid version/digest')
    app = BASE / name
    target = app / version
    current = app / 'current'
    if current.is_symlink() and current.resolve() == target and target.exists():
        print(f'{name}: already installed {version}')
        return
    print(f'{name}: {version} from {url}, SHA256 {digest}')
    if sys.argv[1] == 'update' and input('Install reviewed vendor release? [YES]: ') != 'YES':
        return
    blob = fetch(url)
    if hashlib.sha256(blob).hexdigest().lower() != digest.lower():
        raise ValueError('Checksum mismatch')
    app.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with tempfile.TemporaryDirectory(dir=app) as tmp:
            work = Path(tmp)
            if name == 'arduino-ide':
                (work / 'arduino-ide').write_bytes(blob)
                (work / 'arduino-ide').chmod(0o755)
            else:
                archive = work / 'archive.tar.gz'
                archive.write_bytes(blob)
                unpack = work / 'unpack'
                unpack.mkdir()
                with tarfile.open(archive) as tar:
                    tar.extractall(unpack, filter='data')
                roots = list(unpack.iterdir())
                if len(roots) != 1 or not roots[0].is_dir():
                    raise ValueError('Unexpected archive layout')
                shutil.move(str(roots[0]), str(work / 'payload'))
                archive.unlink()
                shutil.move(str(work / 'payload'), target)
            if name == 'arduino-ide':
                target.mkdir()
                shutil.move(str(work / 'arduino-ide'), target / 'arduino-ide')
    executable = target / launcher
    if not executable.is_file():
        raise ValueError(f'Launcher missing: {executable}; previous current version retained')
    pending = app / 'current.new'
    if pending.is_symlink():
        pending.unlink()
    pending.symlink_to(version)
    pending.replace(current)
    BIN.mkdir(parents=True, exist_ok=True)
    link = BIN / name
    if link.exists() and not link.is_symlink():
        raise ValueError(f'User executable collision: {link}')
    if link.is_symlink():
        link.unlink()
    link.symlink_to(current / launcher)
    DESKTOP.mkdir(parents=True, exist_ok=True)
    desktop = DESKTOP / f'fedora-postinstall-{name}.desktop'
    if not desktop.exists():
        desktop.write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec="{link}" %U\nTerminal=false\nCategories=Development;\n')
    (target / 'origin.json').write_text(json.dumps({'version': version, 'url': url, 'sha256': digest}, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in {'install', 'update'}:
        raise SystemExit('Usage: vendor-apps.py install|update')
    if os.geteuid() == 0:
        raise SystemExit('Run as desktop user')
    for name, code, launcher in [('rustrover', 'RR', 'bin/rustrover.sh'),
                                  ('intellij-idea', 'IIU', 'bin/idea.sh'),
                                  ('webstorm', 'WS', 'bin/webstorm.sh')]:
        install(name, jetbrains(code), launcher)
    install('arduino-ide', arduino(), 'arduino-ide')
