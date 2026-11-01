#!/usr/bin/env python3
"""Reject disabled signature checks and unexpected vendor hosts."""
import configparser
import sys
from urllib.parse import urlparse
allowed = {
    'brave-browser': {'brave-browser-rpm-release.s3.brave.com'},
    'vscodium': {'repo.vscodium.dev'},
    'tailscale': {'pkgs.tailscale.com'},
    'librewolf': {'repo.librewolf.net'},
    'dms-copr': {'download.copr.fedorainfracloud.org'},
    'hyprland-copr': {'download.copr.fedorainfracloud.org'},
}
def require(condition, message):
    if not condition:
        raise ValueError(message)

name, path = sys.argv[1:]
c = configparser.ConfigParser(interpolation=None)
c.read(path)
require(c.sections(), 'Empty repo')
for s in c.values():
    if s.name == 'DEFAULT':
        continue
    require(s.get('gpgcheck') == '1', 'Package signature checking required')
    require(s.get('sslverify', '1') == '1', 'TLS verification required')
    require(not s.get('metalink') and not s.get('mirrorlist'), 'Unexpected indirection')
    for key in ('baseurl', 'gpgkey'):
        urls = s.get(key, '').split()
        require(urls, f'Missing {key}')
        for url in urls:
            u = urlparse(url)
            require(u.scheme == 'https' and u.hostname in allowed[name], url)
            if name == 'dms-copr':
                require(any(u.path.startswith('/results/duxlabs/'+repo+'/')
                            for repo in ('dms', 'dux-repo')), 'Unexpected DMS COPR project')
print('Repository host/TLS/signature policy passed; review the signing key trust separately.')
