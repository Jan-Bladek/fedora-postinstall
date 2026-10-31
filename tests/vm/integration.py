#!/usr/bin/env python3
"""Disposable KVM integration test. Keeps guest disks and keys out of the repository."""
import argparse
import concurrent.futures
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT = '36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6'
IMAGES = {
    'Everything': ('Fedora-Everything-netinst-x86_64-44-1.7.iso', 'Fedora-Everything-44-1.7-x86_64-CHECKSUM'),
    'KDE': ('Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso', 'Fedora-KDE-44-1.7-x86_64-CHECKSUM'),
}

def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)

def download(url, path):
    run(['curl', '--proto', '=https', '--tlsv1.2', '-fsSL', '--retry', '3', url, '-o', str(path)])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--modules', default='snapshots dependencies hyprland noctalia terminal development browsers multimedia utilities defaults optimization updates')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    if work.exists():
        raise SystemExit('Work directory must not exist; no existing VM is overwritten')
    if not Path('/dev/kvm').exists():
        raise SystemExit('This integration test requires KVM')
    work.mkdir(parents=True, mode=0o700)
    reports = work / 'reports'
    reports.mkdir()
    for name in args.modules.split():
        if not re.fullmatch('[a-z-]+', name) or not (ROOT / 'modules' / f'{name}.sh').is_file() or name == 'kde-removal':
            raise SystemExit(f'Unsupported automated module: {name}')
    download('https://fedoraproject.org/fedora.gpg', work / 'fedora.gpg')
    hashes = {}
    def image(item):
        variant, (filename, checksum) = item
        base = f'https://download.fedoraproject.org/pub/fedora/linux/releases/44/{variant}/x86_64/iso/'
        download(base + checksum, work / checksum)
        signature = run(['gpgv', '--status-fd=1', '--keyring', str(work / 'fedora.gpg'), str(work / checksum)], capture_output=True)
        if f'VALIDSIG {FINGERPRINT} ' not in signature.stdout:
            raise ValueError('Unexpected Fedora signing key')
        download(base + filename, work / filename)
        expected = re.search(r'SHA256 \(' + re.escape(filename) + r'\) = ([0-9a-f]{64})', (work / checksum).read_text()).group(1)
        with (work / filename).open('rb') as data:
            actual = hashlib.file_digest(data, 'sha256').hexdigest()
        if expected != actual:
            raise ValueError(f'ISO checksum mismatch: {filename}')
        return filename, actual
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        hashes.update(pool.map(image, IMAGES.items()))
    print('Both Fedora ISO signatures and hashes verified', flush=True)
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(work / 'key')])
    ks = (ROOT / 'tests/vm/fedora44.ks.in').read_text().replace('@@SSH_PUBLIC_KEY@@', (work / 'key.pub').read_text().strip())
    http_root = work / 'http'
    http_root.mkdir()
    (http_root / 'ks.cfg').write_text(ks)
    server = ThreadingHTTPServer(('127.0.0.1', 8844), functools.partial(SimpleHTTPRequestHandler, directory=str(http_root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    run(['bsdtar', '-xf', str(work / IMAGES['Everything'][0]), '-C', str(work), 'images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img'])
    run(['qemu-img', 'create', '-f', 'qcow2', str(work / 'guest.qcow2'), '90G'])
    common = ['qemu-system-x86_64', '-accel', 'kvm', '-cpu', 'host', '-smp', '4', '-m', '6144',
              '-drive', f'file={work}/guest.qcow2,if=virtio,format=qcow2',
              '-netdev', 'user,id=n,hostfwd=tcp:127.0.0.1:22244-:22', '-device', 'virtio-net-pci,netdev=n',
              '-device', 'virtio-vga', '-display', 'none', '-no-reboot']
    proc = None
    qemu_log = (reports / 'qemu.log').open('w')
    ssh = ['ssh', '-i', str(work / 'key'), '-p', '22244', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'StrictHostKeyChecking=accept-new', '-o', f'UserKnownHostsFile={work}/known_hosts', 'tester@127.0.0.1']
    def guest(script, log, check=True):
        command = ssh + ['bash -s']
        with (reports / log).open('w') as output:
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True)
            child.stdin.write(script)
            child.stdin.close()
            for line in child.stdout:
                output.write(line)
                output.flush()
                if 'MODULE ' in line or 'ERROR:' in line or 'Finished.' in line:
                    print(line.rstrip(), flush=True)
            result = subprocess.CompletedProcess(command, child.wait(), (reports / log).read_text())
        print(result.stdout[-3500:], flush=True)
        if check and result.returncode:
            raise RuntimeError(f'Guest failed ({result.returncode}); see {log}')
        return result
    def boot_guest(log):
        return subprocess.Popen(common + ['-serial', f'file:{reports}/{log}'], stdout=qemu_log, stderr=qemu_log)
    def wait_ssh():
        for _ in range(120):
            result = subprocess.run(ssh + ['true'], capture_output=True)
            if result.returncode == 0:
                return
            if proc.poll() is not None:
                raise RuntimeError('Guest exited before SSH became ready')
            time.sleep(5)
        raise TimeoutError('Guest SSH did not start')
    try:
        proc = subprocess.Popen(common + ['-cdrom', str(work / IMAGES['Everything'][0]),
            '-drive', f'file={work / IMAGES["KDE"][0]},media=cdrom,readonly=on',
            '-kernel', str(work / 'images/pxeboot/vmlinuz'), '-initrd', str(work / 'images/pxeboot/initrd.img'),
            '-append', 'inst.stage2=hd:LABEL=Fedora-E-dvd-x86_64-44 inst.ks=http://10.0.2.2:8844/ks.cfg inst.text console=ttyS0,115200n8',
            '-serial', f'file:{reports}/anaconda-serial.log'], stdout=qemu_log, stderr=qemu_log)
        deadline = time.monotonic() + 1200
        serial = reports / 'anaconda-serial.log'
        while proc.poll() is None:
            if serial.exists():
                output = serial.read_text(errors='replace')
                if any(marker in output for marker in ('An unknown error has occurred', 'An unknown error has occured', 'exception report', 'installation will be aborted')):
                    raise RuntimeError('Anaconda reported a fatal error; see anaconda-serial.log')
            if time.monotonic() > deadline:
                raise TimeoutError('Anaconda did not finish within 20 minutes')
            time.sleep(5)
        if proc.returncode != 0:
            raise RuntimeError('QEMU installation failed')
        run(['qemu-img', 'snapshot', '-c', 'fedora-kde-baseline', str(work / 'guest.qcow2')])
        proc = boot_guest('boot.log')
        wait_ssh()
        guest('set -eu\nsudo -n -v\ncat /etc/os-release\ngetenforce\nrpm -q plasma-desktop plasma-workspace polkit-kde\n', 'baseline.log')
        archive = work / 'project.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(ROOT, arcname='project', filter=lambda info: None if '/.git' in info.name else info)
        run(['scp', '-O', '-i', str(work / 'key'), '-P', '22244', '-o', f'UserKnownHostsFile={work}/known_hosts', str(archive), 'tester@127.0.0.1:project.tar.gz'])
        guest('set -eu\ntar -xzf project.tar.gz\ncd project\nbash install.sh --dry-run\n', 'dry-run.log')
        install = 'cd project\nset -o pipefail\nyes YES | bash install.sh --modules ' + shlex.quote(args.modules) + '\nrc=${PIPESTATUS[1]}\nexit "$rc"\n'
        guest(install, 'install.log')
        guest(install, 'repeat-install.log')
        guest('set -eu\ncd project\nsudo FEDORA_POSTINSTALL_TEST_TARGET=disposable bash tests/fedora-packages.sh\nHyprland --verify-config --config "$HOME/.config/hypr/hyprland.lua"\n', 'language-and-config.log')
        guest('''set -eu
printf '\\n# integration-user-change\\n' >> "$HOME/.config/kitty/kitty.conf"
before=$(sha256sum "$HOME/.config/kitty/kitty.conf")
cd project
bash install.sh --modules terminal </dev/null
test "$before" = "$(sha256sum "$HOME/.config/kitty/kitty.conf")"
rpm -qa | sort > /tmp/packages-before-removal-guard
if bash install.sh --modules kde-removal </dev/null; then exit 1; fi
rpm -qa | sort > /tmp/packages-after-removal-guard
diff /tmp/packages-before-removal-guard /tmp/packages-after-removal-guard
''', 'preservation-and-removal-guard.log')
        guest('sudo systemctl reboot\n', 'reboot-request.log', check=False)
        proc.wait(timeout=90)
        proc = boot_guest('reboot.log')
        wait_ssh()
        guest('set -eu\ngetenforce\nsudo dnf5 check\nrpm -q hyprland noctalia kitty polkit-kde plasma-desktop\nsystemctl is-active NetworkManager\nif compgen -G "/sys/class/bluetooth/hci*" >/dev/null; then systemctl is-active bluetooth; else echo "Bluetooth runtime skipped: no adapter in VM"; fi\nif command -v tailscale >/dev/null; then systemctl is-active tailscaled; fi\n', 'after-reboot.log')
        (reports / 'result.json').write_text(json.dumps({'result': 'passed', 'modules': args.modules.split(), 'iso_sha256': hashes, 'graphical_session': 'not tested by this SSH-only fixture'}, indent=2))
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        server.shutdown()
        qemu_log.close()

if __name__ == '__main__':
    main()
