#!/usr/bin/env python3
"""Read-only update preview and checkpointed execution with persistent reports."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading

import recovery


def command(args, accepted=(0,)):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end='', flush=True)
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr, flush=True)
    if result.returncode not in accepted:
        raise RuntimeError(f"{args[0]}: exit {result.returncode}")
    return result


def check():
    failures = []
    checks = [('RPM / COPR', ['dnf5', 'check-upgrade', '--refresh'], (0, 100)),
              ('Flatpak użytkownika', ['flatpak', 'remote-ls', '--user', '--updates', '--columns=ref,version'], (0,)),
              ('Flatpak systemowy', ['flatpak', 'remote-ls', '--system', '--updates', '--columns=ref,version'], (0,)),
              ('Rustup', ['rustup', 'check'], (0,))]
    for title, args, accepted in checks:
        if not shutil.which(args[0]):
            print(title+': narzędzie nie jest zainstalowane.'); continue
        print('\n'+title, flush=True)
        try:
            if args[0] == 'flatpak':
                scope = '--user' if '--user' in args else '--system'
                installed = subprocess.run(['flatpak', 'list', scope, '--columns=origin'],
                                           text=True, capture_output=True, check=True)
                remotes = sorted(set(installed.stdout.splitlines()))
                if not remotes:
                    print('Brak zainstalowanych referencji w tym zakresie.'); continue
                for remote in remotes:
                    command([*args, remote])
                continue
            result = command(args, accepted)
            if args[0] == 'dnf5':
                print('Dostępne aktualizacje RPM.' if result.returncode == 100 else 'Brak aktualizacji RPM.')
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            failures.append(title); print(str(error), file=sys.stderr)
    print('\nPozostałe kanały: wersje JetBrains/Arduino, rozszerzenia VS Code, LazyVim oraz nowe wydania źródeł przypiętych w projekcie nie zostały sprawdzone.')
    print('Podgląd odświeża metadane repozytoriów; nie uruchamia sudo, aktualizacji ani konfiguracji Neovim.')
    if failures:
        raise RuntimeError('Nie udało się sprawdzić: '+', '.join(failures))


def snapshot():
    filesystem = subprocess.run(['findmnt', '-n', '-o', 'FSTYPE', '/'], capture_output=True, text=True, check=True).stdout.strip()
    if filesystem != 'btrfs' or not shutil.which('snapper'):
        return None
    if subprocess.run(['sudo', '-n', 'test', '-f', '/etc/snapper/configs/root']).returncode:
        return None
    result = subprocess.run(['sudo', '-n', 'snapper', '-c', 'root', 'create', '--type', 'single',
                             '--description', 'fedora-update: before update', '--print-number'],
                            capture_output=True, text=True, check=True)
    number = result.stdout.strip()
    if not number.isdigit():
        raise RuntimeError('Snapper nie zwrócił numeru migawki; aktualizacja przerwana.')
    return {'config': 'root', 'number': int(number)}


def reboot_status():
    try:
        result = subprocess.run(['sudo', '-n', 'dnf5', 'needs-restarting', '--reboothint'],
                                capture_output=True, text=True, env=dict(os.environ, LC_ALL='C'))
        if result.returncode in (0, 1) and not re.search(r'unknown|not found|unrecognized', result.stderr+result.stdout, re.I):
            return 'required' if result.returncode == 1 else 'not-required'
    except OSError:
        pass
    return 'unknown'


def rpm_inventory():
    result = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}.%{ARCH} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n'],
                            capture_output=True, text=True, check=True)
    inventory = {}
    for line in result.stdout.splitlines():
        if ' ' in line:
            name, version = line.split(' ', 1)
            inventory.setdefault(name, set()).add(version)
    return {name: ', '.join(sorted(versions)) for name, versions in inventory.items()}


def rpm_changes(before, after):
    return [{'package': name, 'before': before.get(name), 'after': after.get(name)}
            for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]


def execute():
    os.umask(0o077)
    with recovery.Lock():
        subprocess.run(['sudo', '-v'], check=True)
        stop = threading.Event()
        def refresh_sudo():
            while not stop.wait(40):
                subprocess.run(['sudo', '-n', '-v'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        thread = threading.Thread(target=refresh_sudo, daemon=True)
        thread.start()
        run = recovery.state_root()/'updates'/(dt.datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+str(os.getpid()))
        run.mkdir(parents=True, mode=0o700)
        report = {'status': 'failed', 'checkpoint': None, 'snapshot': None, 'stages': [], 'reboot': 'unknown'}
        process = None
        before_rpms = None
        try:
            point = recovery.create('Before fedora-update', 'update')
            report['checkpoint'] = point
            before_rpms = rpm_inventory()
            report['snapshot'] = snapshot()
            # Persist the snapshot ID before executing any package updates.
            directory, doc = recovery.load(point)
            doc['snapshot'] = report['snapshot']
            recovery.atomic_json(directory/'manifest.json', doc)
            print('Kopia konfiguracji: '+point, flush=True)
            print('Migawka systemu: '+str(report['snapshot']) if report['snapshot'] else
                  'Brak skonfigurowanej migawki root. Kopia plików nie cofa aktualizacji RPM/Flatpak/Rust.', flush=True)
            engine = Path(__file__).with_name('update-actions.sh')
            env = dict(os.environ, FEDORA_UPDATE_RUN=str(run))
            process = subprocess.Popen(['bash', str(engine)], env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, start_new_session=True)
            with (run/'update.log').open('w') as log:
                for line in process.stdout:
                    print(line.replace('::fedora-stage::', ''), end='', flush=True); log.write(line); log.flush()
                    match = re.match(r'::fedora-stage::\[(\d+)/\d+\] (.+)', line)
                    if match:
                        if report['stages']:
                            report['stages'][-1]['status'] = 'complete'
                        report['stages'].append({'name': match[2], 'status': 'running'})
                process.wait()
            if process.returncode:
                raise RuntimeError(f'Aktualizacja zakończona kodem {process.returncode}')
            if report['stages']:
                report['stages'][-1]['status'] = 'complete'
            report['status'] = 'complete'
        except BaseException as error:
            report['error'] = str(error) or type(error).__name__
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
            if report['stages'] and report['stages'][-1]['status'] == 'running':
                report['stages'][-1]['status'] = 'failed'
            raise
        finally:
            try:
                if report['checkpoint']:
                    try:
                        recovery.finish(report['checkpoint'], report['status'], report['snapshot'])
                        _, checkpoint = recovery.load(report['checkpoint'])
                        report['changed_files'] = sorted(key for key in set(checkpoint['before']) | set(checkpoint['after'])
                                                         if checkpoint['before'].get(key) != checkpoint['after'].get(key))
                    except Exception as error:
                        report['status'] = 'failed'; report['checkpoint_error'] = str(error)
                if before_rpms is not None:
                    try:
                        report['rpm_changes'] = rpm_changes(before_rpms, rpm_inventory())
                    except Exception as error:
                        report['rpm_inventory_error'] = str(error)
                report['reboot'] = reboot_status()
                recovery.atomic_json(run/'report.json', report)
                print('\nWynik: '+report['status'])
                for stage in report['stages']:
                    print(f"  {stage['status']}: {stage['name']}")
                print('Restart: '+{'required': 'zalecany', 'not-required': 'niewymagany według DNF', 'unknown': 'nie ustalono (sprawdź dnf5 needs-restarting)'}[report['reboot']])
                print(f"Zmienione RPM: {len(report.get('rpm_changes', []))}; pliki konfiguracji: {len(report.get('changed_files', []))}")
                print('Log i raport: '+str(run))
                if report['checkpoint']:
                    print('Podgląd przywracania: fedora-restore '+report['checkpoint'])
            finally:
                stop.set(); thread.join(timeout=5)
        if report['status'] != 'complete':
            raise RuntimeError('Nie udało się zakończyć kopii po aktualizacji; sprawdź report.json.')


def main():
    parser = argparse.ArgumentParser(description='Aktualizacje z kopią konfiguracji i raportem.')
    parser.add_argument('--check', action='store_true', help='Tylko podgląd RPM, Flatpak i Rustup')
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Uruchom jako użytkownik pulpitu.')
    if args.check:
        with recovery.ReadLock():
            check()
        return
    if not args.yes and input('Utworzyć kopię i zaktualizować wszystkie zarządzane źródła? [t/N]: ').lower() not in ('t', 'y'):
        return
    execute()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('ERROR: '+str(error), file=sys.stderr); sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
