#!/usr/bin/env python3
"""Install reviewed Zsh plugin revisions and a checksum-verified Starship binary."""
import fcntl
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
import urllib.request


def install(action):
    installed_root = Path.home()/'.local/share/fedora-postinstall'
    source_root = Path(__file__).resolve().parents[1]
    manifest = (source_root/'data/zsh-sources.json').read_bytes()
    init = (source_root/'config/zsh/init.zsh' if (source_root/'config/zsh/init.zsh').exists()
            else source_root/'data/zsh-init.zsh').read_bytes()
    app = installed_root/'apps/zsh'
    current = app/'current'
    if action == 'update' and not current.is_symlink():
        return
    spec = json.loads(manifest)
    expected_urls = {
        'ohmyzsh': 'https://github.com/ohmyzsh/ohmyzsh.git',
        'zsh-autosuggestions': 'https://github.com/zsh-users/zsh-autosuggestions.git',
        'zsh-syntax-highlighting': 'https://github.com/zsh-users/zsh-syntax-highlighting.git',
        'zsh-interactive-cd': 'https://github.com/johannjhang/zsh-interactive-cd.git',
    }
    if set(spec['repositories']) != set(expected_urls):
        raise ValueError('Unexpected Zsh source set')
    for name, repo in spec['repositories'].items():
        if repo['url'] != expected_urls[name] or not re.fullmatch('[0-9a-f]{40}', repo['revision']):
            raise ValueError('Unreviewed Zsh source')
    starship = spec['starship']
    if (not re.fullmatch(r'v\d+\.\d+\.\d+', starship['version']) or
            starship['url'] != f"https://github.com/starship/starship/releases/download/{starship['version']}/starship-x86_64-unknown-linux-gnu.tar.gz" or
            not re.fullmatch('[0-9a-f]{64}', starship['sha256'])):
        raise ValueError('Invalid Starship release')
    app.mkdir(parents=True, exist_ok=True)
    with (app/'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        version = hashlib.sha256(manifest+init).hexdigest()[:20]
        target = app/version
        if not target.exists():
            with tempfile.TemporaryDirectory(prefix='.build-', dir=app) as temp:
                work = Path(temp)
                for name, repo in spec['repositories'].items():
                    dest = work/'ohmyzsh' if name == 'ohmyzsh' else work/'custom/plugins'/name
                    dest.mkdir(parents=True)
                    subprocess.run(['git', 'init', '-q', str(dest)], check=True)
                    subprocess.run(['git', '-C', str(dest), '-c', 'core.hooksPath=/dev/null',
                                    'fetch', '--depth', '1', repo['url'], repo['revision']], check=True)
                    actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'FETCH_HEAD'], text=True).strip()
                    if actual != repo['revision']:
                        raise ValueError('Plugin revision mismatch')
                    subprocess.run(['git', '-C', str(dest), '-c', 'core.hooksPath=/dev/null',
                                    'checkout', '--detach', 'FETCH_HEAD'], check=True)
                    shutil.rmtree(dest/'.git')
                with urllib.request.urlopen(starship['url'], timeout=120) as response:
                    blob = response.read()
                if hashlib.sha256(blob).hexdigest() != starship['sha256']:
                    raise ValueError('Starship checksum mismatch; previous shell retained')
                archive = work/'starship.tar.gz'
                archive.write_bytes(blob)
                (work/'bin').mkdir()
                with tarfile.open(archive) as tar:
                    member = tar.getmember('starship')
                    if not member.isfile():
                        raise ValueError('Unexpected Starship archive')
                    tar.extract(member, work/'bin', filter='data')
                archive.unlink()
                (work/'bin/starship').chmod(0o755)
                (work/'init.zsh').write_bytes(init)
                (work/'sources.json').write_bytes(manifest)
                subprocess.run(['zsh', '-n', str(work/'init.zsh')], check=True)
                subprocess.run([str(work/'bin/starship'), '--version'], check=True)
                work.rename(target)
        if current.exists() and not current.is_symlink():
            raise ValueError('Unmanaged Zsh payload; refusing to replace')
        pending = app/'current.new'
        if pending.is_symlink():
            pending.unlink()
        pending.symlink_to(version)
        pending.replace(current)
        print(f'Zsh plugins + Starship: reviewed payload {version}')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in {'install', 'update'}:
        raise SystemExit('Usage: zsh-manager.py install|update')
    if os.geteuid() == 0:
        raise SystemExit('Run as desktop user')
    install(sys.argv[1])
