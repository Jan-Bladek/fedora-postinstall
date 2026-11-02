import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Options(unittest.TestCase):
    def test_sdk_installation_depends_on_selected_ide(self):
        script = r'''
source "$1/lib/development.sh"
source "$1/modules/development.sh"
DEV_APPS=$2
packages() { echo "PACKAGES $*"; }
run() { echo "RUN $*"; }
command() { return 1; }
install_language_tools
'''
        for apps, expected in [('code', []), ('', []), ('intellij-idea', []),
                               ('rustrover', ['rust cargo']), ('clion', ['gcc gcc-c++']),
                               ('webstorm', ['nodejs npm'])]:
            with self.subTest(apps=apps):
                result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT), apps],
                                        text=True, capture_output=True, check=True)
                for packages in ('rust cargo', 'gcc gcc-c++', 'nodejs npm'):
                    self.assertEqual(packages in result.stdout, packages in expected)

    def test_vendor_install_downloads_only_selected_clion(self):
        script = r'''
import runpy, sys, os
from pathlib import Path
path = Path(sys.argv[1]) / 'scripts/vendor-apps.py'
ns = runpy.run_path(str(path))
source = path.read_text().split("if __name__ == '__main__':")[1]
os.geteuid = lambda: 1000
ns['jetbrains'] = lambda code: code
ns['install'] = lambda name, metadata, launcher: print(name, metadata, launcher)
ns['arduino'] = lambda: (_ for _ in ()).throw(AssertionError('Arduino not selected'))
sys.argv = ['vendor-apps.py', 'install', 'clion']
import textwrap
exec(textwrap.dedent(source), ns)
'''
        result = subprocess.run(['python3', '-c', script, str(ROOT)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), 'clion CL bin/clion.sh')

    def test_dms_migration_is_idempotent_and_keeps_custom_code(self):
        ns = runpy.run_path(str(ROOT/'scripts/dms-includes.py'))
        template = (ROOT/'config/hyprland/hyprland.lua').read_text()
        old = '-- user settings\n' + ns['OLD'] + '\n-- more user settings\n'
        new = ns['migrate'](old, template)
        self.assertIn('require("dms.colors")', new)
        self.assertNotIn('dofile(path)', new)
        self.assertTrue(new.startswith('-- user settings\n'))
        self.assertTrue(new.endswith('-- more user settings\n'))
        self.assertEqual(ns['migrate'](new, template), new)
        self.assertEqual(ns['migrate']('-- custom includes', template), '-- custom includes')

    def test_debloat_refuses_dolphin_without_working_flea(self):
        with tempfile.TemporaryDirectory() as home:
            script = r'''
source "$1/lib/core.sh"
source "$1/modules/cleanup.sh"
ROOT=$1
RUN=$HOME
CLEANUP_APPS=dolphin
run() { echo FORBIDDEN; }
module_cleanup
'''
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                                    env=dict(os.environ, HOME=home), text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('before removing Dolphin', result.stderr)
            self.assertNotIn('FORBIDDEN', result.stdout)

    def test_office_selection_excludes_rpm_and_flatpak_from_cleanup(self):
        # Exercise the actual cleanup module with no installed RPMs and a Flatpak spy.
        with tempfile.TemporaryDirectory() as home:
            script = r'''
source "$1/lib/core.sh"
source "$1/modules/cleanup.sh"
ROOT=$1
RUN=$HOME
CONFIG=$HOME/config
MODULES='cleanup libreoffice'
CLEANUP_APPS=all
mkdir -p "$HOME/.local/bin"
printf '#!/bin/sh\n' > "$HOME/.local/bin/flea"
chmod +x "$HOME/.local/bin/flea"
mkdir -p "$HOME/bin"
printf '#!/bin/sh\nexit 0\n' > "$HOME/bin/rpm"
chmod +x "$HOME/bin/rpm"
export PATH="$HOME/bin:$PATH"
run() { :; }
xdg-mime() { echo com.thisisgm.flea.desktop; }
flatpak() { echo "FLATPAK $*" >> "$HOME/flatpak-calls"; return 1; }
# Skip unrelated launcher hiding, which is covered by existing tests.
python3() {
    if [[ $1 == */hide-launcher.py ]]; then return 0; fi
    command python3 "$@"
}
module_cleanup
'''
            result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(ROOT)],
                                    env=dict(os.environ, HOME=home), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            import json
            plan = json.loads((Path(home)/'cleanup-plan.json').read_text())
            self.assertNotIn('libreoffice', plan['groups'])
            self.assertIn('dolphin', plan['groups'])
            self.assertNotIn('LibreOffice', (Path(home)/'flatpak-calls').read_text())

    def test_temporary_flea_compiler_cleanup_preserves_existing_packages(self):
        for build_status, dependency_status in ((0, 0), (42, 0), (0, 7)):
            with self.subTest(build=build_status, dependencies=dependency_status), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                shim = work/'bin'
                shim.mkdir()
                scripts = {
                    'cargo': '#!/bin/sh\necho "cargo $*" >> "$TEST_LOG"\nexit "$BUILD_STATUS"\n',
                    'sudo': '#!/bin/sh\necho "sudo $*" >> "$TEST_LOG"\nif [ "$1" = dnf5 ]; then touch "$TEST_INSTALLED"; exit 0; fi\nexec "$@"\n',
                    'rpm': '#!/bin/sh\nif [ "$1" = -qa ]; then echo keep; echo gcc; echo rust-src; if [ -f "$TEST_INSTALLED" ]; then echo cargo; echo rust; echo rust-std-static; echo extra-library; fi; elif [ "$2" = --test ]; then exit "$DEPENDENCY_STATUS"; fi\n',
                }
                for name, content in scripts.items():
                    path = shim/name
                    path.write_text(content)
                    path.chmod(0o755)
                startup = work/'startup'
                startup.write_text('command() { if [[ $* == "-v cargo" && ! -f $TEST_INSTALLED ]]; then return 1; fi; builtin command "$@"; }\n')
                log = work/'log'
                result = subprocess.run(['bash', str(ROOT/'scripts/flea-build.sh')], capture_output=True, text=True,
                                        env=dict(os.environ, PATH=str(shim)+':'+os.environ['PATH'],
                                                 BASH_ENV=str(startup), TEST_LOG=str(log),
                                                 TEST_INSTALLED=str(work/'installed'), BUILD_STATUS=str(build_status),
                                                 DEPENDENCY_STATUS=str(dependency_status)))
                self.assertEqual(result.returncode, build_status if not dependency_status else 1, result.stderr)
                commands = log.read_text().splitlines()
                self.assertIn('sudo rpm -e --test cargo rust rust-std-static', commands)
                self.assertEqual('sudo rpm -e cargo rust rust-std-static' in commands, not dependency_status)
                self.assertFalse(any('rpm -e' in line and ('rust-src' in line or 'gcc' in line or 'extra-library' in line) for line in commands))
