#!/usr/bin/env python3
"""Selective user-state checkpoints; no wholesale extraction into HOME or /etc."""
import argparse
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import uuid

GROUPS = ('hyprland', 'kitty', 'zsh', 'defaults', 'desktop', 'services', 'applications', 'lazyvim')
APP_NAMES = ('rustrover', 'intellij-idea', 'webstorm', 'clion', 'arduino-ide', 'flea', 'omasnap', 'zsh')


def roots():
    home = Path.home().absolute()
    return {'home': home, 'config': Path(os.environ.get('XDG_CONFIG_HOME', home/'.config')).absolute(),
            'data': Path(os.environ.get('XDG_DATA_HOME', home/'.local/share')).absolute()}


def state_root():
    return Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'fedora-postinstall'


def specs():
    return {
        'hyprland': [('config', 'hypr')], 'kitty': [('config', 'kitty')],
        'zsh': [('home', '.zshrc'), ('config', 'fedora-postinstall/starship.toml')],
        'defaults': [('config', p) for p in ('mimeapps.list', 'kdeglobals', 'xdg-terminals.list', 'environment.d/60-fedora-postinstall.conf')]+[('data', 'applications/mimeapps.list')],
        'desktop': [('config', p) for p in ('noctalia', 'dms', 'btop/btop.conf', 'fontconfig/conf.d/60-jetbrains-mono.conf', 'xdg-desktop-portal/hyprland-portals.conf')],
        'services': [('config', 'systemd/user'), ('config', 'autostart')]+[('data', 'dbus-1/services')],
        'applications': [('data', f'fedora-postinstall/apps/{name}/current') for name in APP_NAMES]+[('data', 'applications')]+[('home', f'.local/bin/{name}') for name in (*APP_NAMES, 'flea-filemanager1')]+[('data', 'fonts/fedora-postinstall-symbols.ttf')],
        'lazyvim': [('config', 'nvim')],
    }


def classify(root, rel):
    for group, entries in specs().items():
        for base, prefix in entries:
            if base == root and (rel == prefix or rel.startswith(prefix+'/')):
                # MIME associations belong to defaults, not launcher rollback.
                if root == 'data' and rel == 'applications/mimeapps.list':
                    return 'defaults'
                return group
    return None


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        json.dump(value, file, indent=2, ensure_ascii=False)
        file.write('\n'); file.flush(); os.fsync(file.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def file_digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def safe_target(key, point_roots):
    root, rel = key.split(':', 1)
    relative = PurePosixPath(rel)
    current_roots = roots()
    if root not in current_roots or relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Unsafe checkpoint path: '+key)
    if str(current_roots[root]) != point_roots[root] or not classify(root, relative.as_posix()):
        raise ValueError('Checkpoint belongs to a different HOME/XDG layout: '+key)
    base = current_roots[root]
    target = base.joinpath(*relative.parts)
    # A directory symlink is saved as a link, never traversed to restore children.
    parent = target.parent
    while parent != base:
        if parent.is_symlink():
            raise ValueError('Refusing to follow a parent symlink: '+str(parent))
        parent = parent.parent
    return target


def entry_at(path, blobs=None):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        return {'kind': 'link', 'target': os.readlink(path)}
    if stat.S_ISDIR(info.st_mode):
        return {'kind': 'dir', 'mode': stat.S_IMODE(info.st_mode)}
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Unsupported configuration file type: '+str(path))
    digest = hashlib.sha256()
    temporary = None
    if blobs is not None:
        blobs.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = tempfile.NamedTemporaryFile(dir=blobs, delete=False)
        temporary = Path(handle.name)
    else:
        handle = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
                if handle:
                    handle.write(chunk)
        final = path.lstat()
        if (final.st_ino, final.st_size, final.st_mtime_ns) != (info.st_ino, info.st_size, info.st_mtime_ns):
            raise ValueError('Configuration changed while making its backup: '+str(path))
        sha = digest.hexdigest()
        if handle:
            handle.close()
            os.replace(temporary, blobs/sha)
        return {'kind': 'file', 'sha256': sha, 'mode': stat.S_IMODE(info.st_mode)}
    finally:
        if handle and not handle.closed:
            handle.close()
        if temporary:
            temporary.unlink(missing_ok=True)


def capture(blobs, groups):
    result = {}
    bases = roots()
    def visit(root, rel):
        path = safe_target(root+':'+rel, {name: str(base) for name, base in bases.items()})
        value = entry_at(path, blobs)
        if value is None:
            return
        group = classify(root, rel)
        if group in groups:
            result[root+':'+rel] = dict(value, group=group)
        if value['kind'] == 'dir':
            # Payload versions are deliberately not copied; current is a link.
            if rel.endswith('/current') and group == 'applications':
                return
            for child in sorted(path.iterdir()):
                visit(root, rel+'/'+child.name)
    seen = set()
    for group in groups:
        for root, rel in specs()[group]:
            if (root, rel) not in seen:
                visit(root, rel); seen.add((root, rel))
    return result


def strip_group(value):
    return {k: v for k, v in value.items() if k != 'group'} if value else None


class Lock:
    def __enter__(self):
        state_root().mkdir(parents=True, exist_ok=True, mode=0o700)
        self.file = (state_root()/'lock').open('a')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close(); raise RuntimeError('Installer/update/restore already running.')
        return self

    def __exit__(self, *args):
        self.file.close()


class ReadLock:
    """Exclude concurrent mutations without creating files during --check."""
    def __enter__(self):
        self.file = None
        try:
            self.file = (state_root()/'lock').open('r')
        except FileNotFoundError:
            return self
        try:
            fcntl.flock(self.file, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            raise RuntimeError('Installer/update/restore already running; retry --check afterward.')
        return self

    def __exit__(self, *args):
        if self.file:
            self.file.close()


def create(label, kind='manual', groups=GROUPS, source_run=None):
    os.umask(0o077)
    identifier = dt.datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    directory = state_root()/'checkpoints'/identifier
    directory.mkdir(parents=True, mode=0o700)
    document = {'format': 1, 'id': identifier, 'label': label, 'kind': kind,
                'created': dt.datetime.now().astimezone().isoformat(), 'status': 'open',
                'roots': {key: str(value) for key, value in roots().items()},
                'groups': list(groups), 'source_run': str(source_run) if source_run else None,
                'before': {}, 'after': None, 'rpm_backups': [], 'snapshot': None}
    try:
        document['before'] = capture(directory/'blobs', groups)
        atomic_json(directory/'manifest.json', document)
    except BaseException:
        shutil.rmtree(directory)
        raise
    return identifier


def load(identifier):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', identifier) or identifier in ('.', '..'):
        raise ValueError('Invalid checkpoint ID')
    directory = state_root()/'checkpoints'/identifier
    if directory.is_symlink() or (directory/'manifest.json').is_symlink():
        raise ValueError('Checkpoint directory/manifest cannot be a symlink')
    doc = json.loads((directory/'manifest.json').read_text())
    if doc.get('format') != 1 or doc.get('id') != identifier:
        raise ValueError('Unsupported checkpoint manifest')
    for key, value in doc['before'].items():
        safe_target(key, doc['roots'])
        if value.get('group') != classify(*key.split(':', 1)):
            raise ValueError('Invalid checkpoint component')
    return directory, doc


def attach_rpms(document):
    source = document.get('source_run')
    if not source:
        return
    run = Path(source)
    allowed = state_root()/'runs'
    if run.parent.resolve() != allowed.resolve() or run.is_symlink():
        raise ValueError('Recovery RPMs must come from an installer run')
    document['rpm_backups'] = []
    for name in ('cleanup-rpms', 'plasma-rpms'):
        if (run/name).is_symlink():
            raise ValueError('Recovery RPM directory cannot be a symlink')
        for file in sorted((run/name).glob('*.rpm')):
            if file.is_symlink() or not file.is_file():
                raise ValueError('Invalid recovery RPM')
            document['rpm_backups'].append({'path': str(file), 'sha256': file_digest(file)})


def finish(identifier, status='complete', snapshot=None):
    directory, document = load(identifier)
    document['after'] = capture(directory/'blobs', document['groups'])
    document['status'] = status
    if snapshot is not None:
        document['snapshot'] = snapshot
    attach_rpms(document)
    atomic_json(directory/'manifest.json', document)


def list_points():
    result = []
    folder = state_root()/'checkpoints'
    if folder.exists():
        for path in sorted(folder.iterdir(), reverse=True):
            if path.is_dir() and not path.is_symlink():
                try:
                    _, doc = load(path.name)
                    result.append({key: doc.get(key) for key in ('id', 'label', 'kind', 'created', 'status', 'groups', 'snapshot')})
                except (ValueError, OSError, KeyError):
                    continue
    return result


def plan(identifier, groups, force=False):
    directory, document = load(identifier)
    if set(groups)-set(GROUPS)-{'packages'}:
        raise ValueError('Unknown restore component')
    before, after = document['before'], document.get('after')
    rows = []
    for key in sorted(set(before) | set(after or {})):
        value, expected = before.get(key), (after or {}).get(key)
        group = classify(*key.split(':', 1))
        if group not in groups:
            continue
        target = safe_target(key, document['roots'])
        current = entry_at(target)
        original = strip_group(value)
        if current == original:
            continue
        conflict = after is None or current != strip_group(expected)
        # No recursive deletion, even with --force.
        blocked = bool(current and current['kind'] == 'dir' and
                       original and original['kind'] != 'dir' and any(target.iterdir()))
        rows.append({'key': key, 'path': str(target), 'component': group,
                     'action': 'restore' if value else 'remove', 'conflict': conflict,
                     'blocked': blocked, 'apply': not blocked and (force or not conflict)})
    rpms = []
    if 'packages' in groups:
        for item in document.get('rpm_backups', []):
            file = Path(item['path'])
            run = Path(document.get('source_run') or '')
            if file.parent not in (run/'cleanup-rpms', run/'plasma-rpms') or run.parent.resolve() != (state_root()/'runs').resolve():
                raise ValueError('Unsafe recovery RPM path')
            if file.is_symlink() or file_digest(file) != item['sha256']:
                raise ValueError('Recovery RPM checksum mismatch: '+str(file))
            rpms.append(str(file))
    return {'point': identifier, 'components': list(groups), 'files': rows, 'rpms': rpms,
            'snapshot': document.get('snapshot')}


def apply(identifier, groups, force=False):
    preview = plan(identifier, groups, force)
    if any(not item['apply'] for item in preview['files']):
        raise ValueError('Later edits/unsafe directory replacement detected. Review the plan; --force permits later edits but never recursive deletion.')
    directory, doc = load(identifier)
    # Validate every blob before making the first user-file change.
    for row in preview['files']:
        value = doc['before'].get(row['key'])
        if value and value['kind'] == 'link' and row['component'] == 'applications' and row['path'].endswith('/current'):
            payload = Path(row['path']).parent/value['target']
            if not payload.is_dir():
                raise ValueError('Previous application payload is missing: '+str(payload))
        if value and value['kind'] == 'file':
            sha = value['sha256']
            if not re.fullmatch('[0-9a-f]{64}', sha):
                raise ValueError('Invalid backup digest')
            blob = directory/'blobs'/sha
            if blob.is_symlink() or file_digest(blob) != sha:
                raise ValueError('Backup blob checksum mismatch')
    # Verify local RPM signatures before doing any restoration.
    for package in preview['rpms']:
        check = subprocess.run(['rpmkeys', '--checksig', '--verbose', package], env=dict(os.environ, LC_ALL='C'), capture_output=True, text=True)
        if check.returncode or not re.search(r'signature.*:\s*OK', check.stdout, re.I):
            raise ValueError('Trusted RPM signature required: '+package)
    reverse = create('Before restoring '+identifier, 'before-restore', tuple(g for g in groups if g != 'packages'))
    changes = sorted(preview['files'], key=lambda item: (0 if doc['before'].get(item['key'], {}).get('kind') == 'dir' else 1, len(Path(item['path']).parts)))
    try:
        if preview['rpms']:
            subprocess.run(['sudo', 'dnf5', '--assumeyes', '--setopt=localpkg_gpgcheck=1', 'install', *preview['rpms']], check=True, umask=0o022)
        for row in changes:
            target = safe_target(row['key'], doc['roots'])
            value = doc['before'].get(row['key'])
            if not value:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if value['kind'] == 'dir':
                if target.is_symlink() or target.is_file():
                    target.unlink()
                target.mkdir(exist_ok=True); target.chmod(value['mode'])
            else:
                if target.is_dir() and not target.is_symlink():
                    target.rmdir()  # refuses nonempty directories
                temporary = target.parent/('.fedora-restore-'+uuid.uuid4().hex)
                try:
                    if value['kind'] == 'link':
                        temporary.symlink_to(value['target'])
                    else:
                        shutil.copyfile(directory/'blobs'/value['sha256'], temporary)
                        temporary.chmod(value['mode'])
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
        for row in sorted(preview['files'], key=lambda item: len(Path(item['path']).parts), reverse=True):
            if row['key'] not in doc['before']:
                target = safe_target(row['key'], doc['roots'])
                if target.is_dir() and not target.is_symlink():
                    try:
                        target.rmdir()
                    except OSError as error:
                        # User files added later are retained.
                        if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                            raise
                else:
                    target.unlink(missing_ok=True)
    except BaseException:
        finish(reverse, 'restore-failed')
        raise
    finish(reverse)
    return reverse, preview


def import_run(identifier):
    if not re.fullmatch('[A-Za-z0-9_.-]+', identifier) or identifier in ('.', '..'):
        raise ValueError('Invalid installer run ID')
    run = state_root()/'runs'/identifier
    if run.is_symlink():
        raise ValueError('Invalid installer run')
    point = create('Imported installer run '+identifier, 'legacy', source_run=run)
    directory, doc = load(point)
    doc['before'] = {}
    try:
        with tarfile.open(run/'user-config.tar.gz', 'r:*') as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts:
                    raise ValueError('Unsafe legacy archive entry')
                if not name.parts or name.parts[0] != '.config' or len(name.parts) < 2:
                    continue
                rel = PurePosixPath(*name.parts[1:]).as_posix()
                group = classify('config', rel)
                if not group:
                    continue
                value = {'mode': member.mode, 'group': group}
                if member.isdir():
                    value['kind'] = 'dir'
                elif member.issym():
                    value = {'kind': 'link', 'target': member.linkname, 'group': group}
                elif member.isfile():
                    data = archive.extractfile(member).read()
                    sha = hashlib.sha256(data).hexdigest()
                    (directory/'blobs').mkdir(exist_ok=True)
                    (directory/'blobs'/sha).write_bytes(data)
                    value.update(kind='file', sha256=sha)
                else:
                    raise ValueError('Unsupported legacy archive entry')
                doc['before']['config:'+rel] = value
        if (run/'zshrc-before').is_file():
            doc['before']['home:.zshrc'] = dict(entry_at(run/'zshrc-before', directory/'blobs'), group='zsh')
        doc['status'] = 'legacy-no-after-state'; doc['after'] = None
        attach_rpms(doc)
        atomic_json(directory/'manifest.json', doc)
    except BaseException:
        shutil.rmtree(directory)
        raise
    return point


def main():
    parser = argparse.ArgumentParser(description='Internal checkpoint interface; use fedora-restore for recovery.')
    parser.add_argument('action', choices=('create', 'finish'))
    parser.add_argument('value')
    parser.add_argument('--kind', default='installer')
    parser.add_argument('--source-run')
    parser.add_argument('--status', default='complete')
    args = parser.parse_args()
    if args.action == 'create':
        print(create(args.value, args.kind, source_run=args.source_run))
    else:
        finish(args.value, args.status)


if __name__ == '__main__':
    main()
