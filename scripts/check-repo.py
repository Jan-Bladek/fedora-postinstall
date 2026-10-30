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
    'hyprland-copr': {'download.copr.fedorainfracloud.org'},
}
name, path = sys.argv[1:]
c = configparser.ConfigParser(interpolation=None)
c.read(path)
assert c.sections(), 'Empty repo'
for s in c.values():
    if s.name == 'DEFAULT':
        continue
    assert s.get('gpgcheck') == '1', 'Package signature checking required'
    assert s.get('sslverify', '1') == '1', 'TLS verification required'
    assert not s.get('metalink') and not s.get('mirrorlist'), 'Unexpected indirection'
    for key in ('baseurl', 'gpgkey'):
        urls = s.get(key, '').split()
        assert urls, f'Missing {key}'
        for url in urls:
            u = urlparse(url)
            assert u.scheme == 'https' and u.hostname in allowed[name], url
print('Repository host/TLS/signature policy passed; review the signing key trust separately.')
