import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import recovery
spec = importlib.util.spec_from_file_location('update_manager', ROOT/'scripts/update-manager.py')
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        env = dict(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home/'config'),
                   XDG_DATA_HOME=str(self.home/'data'), XDG_STATE_HOME=str(self.home/'state'))
        self.environment = patch.dict(os.environ, env)
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.file = self.home/'config/kitty/kitty.conf'
        self.file.parent.mkdir(parents=True)
        self.file.write_text('before')

    def point(self):
        point = recovery.create('test', groups=('kitty',))
        self.file.write_text('after')
        recovery.finish(point)
        return point

    def test_selective_restore_and_reverse_checkpoint(self):
        point = self.point()
        other = self.home/'config/hypr/custom.conf'
        other.parent.mkdir(); other.write_text('personal')
        reverse, _ = recovery.apply(point, ('kitty',))
        self.assertEqual(self.file.read_text(), 'before')
        self.assertEqual(other.read_text(), 'personal')
        recovery.apply(reverse, ('kitty',))
        self.assertEqual(self.file.read_text(), 'after')

    def test_later_edit_refused_then_explicit_force(self):
        point = self.point(); self.file.write_text('personal')
        with self.assertRaises(ValueError):
            recovery.apply(point, ('kitty',))
        self.assertEqual(self.file.read_text(), 'personal')
        recovery.apply(point, ('kitty',), True)
        self.assertEqual(self.file.read_text(), 'before')

    def test_corruption_refused_before_first_change(self):
        point = self.point()
        directory, doc = recovery.load(point)
        sha = doc['before']['config:kitty/kitty.conf']['sha256']
        (directory/'blobs'/sha).write_text('corrupted')
        with self.assertRaises(ValueError):
            recovery.apply(point, ('kitty',))
        self.assertEqual(self.file.read_text(), 'after')

    def test_new_directory_removed_without_recursive_delete(self):
        point = recovery.create('empty', groups=('hyprland',))
        file = self.home/'config/hypr/nested/config'
        file.parent.mkdir(parents=True); file.write_text('installed')
        recovery.finish(point)
        extra = file.parent/'personal'; extra.write_text('keep')
        recovery.apply(point, ('hyprland',))
        self.assertFalse(file.exists()); self.assertEqual(extra.read_text(), 'keep')

    def test_replaced_parent_symlink_cannot_escape(self):
        point = self.point()
        self.file.unlink(); self.file.parent.rmdir()
        outside = self.home/'outside'; outside.mkdir()
        (outside/'kitty.conf').write_text('outside')
        self.file.parent.symlink_to(outside)
        with self.assertRaises(ValueError):
            recovery.apply(point, ('kitty',), True)
        self.assertEqual((outside/'kitty.conf').read_text(), 'outside')

    def test_original_symlink_restored_without_copying_payload(self):
        self.file.unlink(); self.file.symlink_to('/unavailable/original')
        point = recovery.create('link', groups=('kitty',))
        self.file.unlink(); self.file.write_text('new')
        recovery.finish(point); recovery.apply(point, ('kitty',))
        self.assertEqual(os.readlink(self.file), '/unavailable/original')

    def test_legacy_archive_traversal_never_extracted(self):
        run = recovery.state_root()/'runs/legacy'; run.mkdir(parents=True)
        with tarfile.open(run/'user-config.tar.gz', 'w:gz') as archive:
            member = tarfile.TarInfo('../escape'); archive.addfile(member)
        with self.assertRaises(ValueError):
            recovery.import_run('legacy')
        self.assertFalse((self.home/'escape').exists())
        self.assertEqual(recovery.list_points(), [])

    def test_legacy_archive_requires_force(self):
        run = recovery.state_root()/'runs/legacy'; run.mkdir(parents=True)
        with tarfile.open(run/'user-config.tar.gz', 'w:gz') as archive:
            archive.add(self.file, arcname='.config/kitty/kitty.conf')
        point = recovery.import_run('legacy')
        self.file.write_text('changed')
        with self.assertRaises(ValueError):
            recovery.apply(point, ('kitty',))
        recovery.apply(point, ('kitty',), True)
        self.assertEqual(self.file.read_text(), 'before')

    def test_lock_excludes_parallel_operation_and_releases(self):
        with recovery.Lock():
            with self.assertRaises(RuntimeError):
                with recovery.Lock():
                    pass
        with recovery.Lock():
            pass

    def test_preview_does_not_change_files(self):
        point = self.point()
        before = sorted(str(p) for p in self.home.rglob('*'))
        recovery.plan(point, ('kitty',))
        self.assertEqual(before, sorted(str(p) for p in self.home.rglob('*')))
        self.assertEqual(self.file.read_text(), 'after')

    def test_recovery_signature_required_before_dnf_or_changes(self):
        point = self.point()
        directory, doc = recovery.load(point)
        run = recovery.state_root()/'runs/rpm-test'; (run/'cleanup-rpms').mkdir(parents=True)
        rpm = run/'cleanup-rpms/test.rpm'; rpm.write_bytes(b'unsigned')
        doc['source_run'] = str(run); recovery.attach_rpms(doc)
        recovery.atomic_json(directory/'manifest.json', doc)
        result = subprocess.CompletedProcess([], 0, 'digests OK', '')
        with patch.object(recovery.subprocess, 'run', return_value=result) as command:
            with self.assertRaises(ValueError):
                recovery.apply(point, ('kitty', 'packages'))
        self.assertEqual(command.call_count, 1)
        self.assertEqual(self.file.read_text(), 'after')

    def test_check_accepts_dnf_100_without_sudo_or_state_writes(self):
        def fake(args, **kwargs):
            self.assertNotIn('sudo', args)
            self.assertNotIn('update', args)
            return subprocess.CompletedProcess(args, 100 if args[0] == 'dnf5' else 0, '', '')
        with patch.object(update.shutil, 'which', return_value='/tool'), patch.object(update.subprocess, 'run', side_effect=fake):
            update.check()
        self.assertFalse(recovery.state_root().exists())

    def test_reboot_exit_one_is_successful_reboot_hint(self):
        with patch.object(update.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, 'Reboot required', '')):
            self.assertEqual(update.reboot_status(), 'required')
        with patch.object(update.subprocess, 'run', return_value=subprocess.CompletedProcess([], 2, '', 'Unknown argument')):
            self.assertEqual(update.reboot_status(), 'unknown')

    def test_failed_update_finalizes_checkpoint_and_report(self):
        def failed_process(*args, **kwargs):
            self.assertTrue(recovery.list_points())
            self.assertEqual(recovery.list_points()[0]['status'], 'open')
            process = unittest.mock.Mock()
            process.stdout = iter(['::fedora-stage::[1/10] RPM\n', '[1/47] package download\n', 'transaction failed\n'])
            process.returncode = 42
            process.poll.return_value = 42
            return process
        with patch.object(update.subprocess, 'run'), patch.object(update.subprocess, 'Popen', side_effect=failed_process), patch.object(update, 'rpm_inventory', return_value={}), patch.object(update, 'snapshot', return_value=None), patch.object(update, 'reboot_status', return_value='unknown'):
            with self.assertRaises(RuntimeError):
                update.execute()
        report = json.loads(next((recovery.state_root()/'updates').glob('*/report.json')).read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['stages'], [{'name': 'RPM', 'status': 'failed'}])
        self.assertEqual(recovery.load(report['checkpoint'])[1]['status'], 'failed')

    def test_failed_configured_snapshot_aborts_before_update(self):
        with patch.object(update.subprocess, 'run'), patch.object(update.subprocess, 'Popen') as engine, patch.object(update, 'rpm_inventory', return_value={}), patch.object(update, 'snapshot', side_effect=RuntimeError('snapshot failed')), patch.object(update, 'reboot_status', return_value='unknown'):
            with self.assertRaises(RuntimeError):
                update.execute()
        engine.assert_not_called()
        self.assertEqual(recovery.list_points()[0]['status'], 'failed')

    def test_rpm_summary_records_added_removed_and_version_changes(self):
        changes = update.rpm_changes({'a.x86_64': '1', 'b.noarch': '1'}, {'a.x86_64': '2', 'c.noarch': '1'})
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[1], {'package': 'b.noarch', 'before': '1', 'after': None})

    def test_configured_snapper_snapshot_number_is_retained(self):
        results = [subprocess.CompletedProcess([], 0, 'btrfs\n', ''),
                   subprocess.CompletedProcess([], 0, '', ''),
                   subprocess.CompletedProcess([], 0, '42\n', '')]
        with patch.object(update.shutil, 'which', return_value='/usr/bin/snapper'), patch.object(update.subprocess, 'run', side_effect=results) as command:
            self.assertEqual(update.snapshot(), {'config': 'root', 'number': 42})
            self.assertIn('--print-number', command.call_args.args[0])

    def test_yes_never_overrides_conflict_in_cli(self):
        point = self.point(); self.file.write_text('personal')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/fedora-restore'), point,
                                 '--components', 'kitty', '--apply', '--yes'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.file.read_text(), 'personal')

    def test_read_lock_never_creates_state_and_refuses_active_mutation(self):
        with recovery.ReadLock():
            pass
        self.assertFalse(recovery.state_root().exists())
        with recovery.Lock():
            with self.assertRaises(RuntimeError):
                with recovery.ReadLock():
                    pass

    def test_dnf_metadata_umask_does_not_weaken_backup_umask(self):
        result = subprocess.run(['bash', '-c', 'source "$1/lib/core.sh"; umask 077; dnf5() { umask; }; run dnf5 check; umask', 'test', str(ROOT)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines()[-2:], ['0022', '0077'])
