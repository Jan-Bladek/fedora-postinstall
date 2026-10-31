# Validation record — 2026-10-31

## Actual Fedora KDE VM

A separate QEMU VM was created from the Fedora 44 KDE Live filesystem, using the
Fedora Everything netinst installer. The host is Omarchy; `/dev/kvm` is unavailable
locally, so local tests used TCG with 4 virtual CPUs, 8 GiB RAM and virtio/virgl.
The guest booted from its own Btrfs virtual disk with kernel 6.19.10-300.fc44,
SELinux **Enforcing** and NetworkManager active. A baseline qcow2 snapshot exists
outside the repository. Existing host desktop configuration was not modified.

Both ISO checksums matched the Fedora 44 signed CHECKSUM files. Signatures were
verified with key `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`.

| ISO | SHA256 |
|---|---|
| Fedora-Everything-netinst-x86_64-44-1.7.iso | bd285201494dd0ba09b54d05ac707de1401668b8512a573edb5922dcf9d7067e |
| Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso | c8295961d4c41adbf785a31a17c21a971d3b7415fda72dcad0c11c49577bf03a |

Local provisioning initially hit an incorrect SDDM entry in the test Kickstart;
Fedora 44 KDE ships Plasma Login Manager. The already installed local guest was
completed manually (test account, SSH and sudo), without recopying the system.
This is a fixture correction, not evidence that unattended provisioning passed.
The corrected KVM workflow is validated separately below.

## Passed in the local guest

- Real `install.sh` run with `dependencies hyprland noctalia terminal defaults updates`:
  **exit 0**, including the final `sudo dnf5 check`.
- Hyprland 0.57.0, Noctalia 5.4.0 and Kitty installed from the configured RPM sources.
- The current Lua configuration returned **config ok** using Hyprland's own parser.
- A real Wayland session started through SDDM (test-only autologin, not a product setting).
- Noctalia started automatically; its bar and application launcher rendered.
- Super+Enter launched a visible, native Wayland Kitty window running Bash.
- Wayland clipboard write/read matched `fedora-postinstall-vm-smoke`.
- Noctalia IPC returned that same clipboard text and opened its launcher.
- KDE applications remained installed and visible in the launcher.
- Noctalia `session lock` showed the lock screen; entering the disposable test
  account password through VNC returned to the same session.
- Noctalia `session suspend` put QEMU into `paused (suspended)`. QEMU `system_wakeup`
  resumed the kernel and SSH; systemd logged suspend completion. However, the
  display stayed black despite `dpmsStatus: true`, and Noctalia was blocked in
  uninterruptible sleep. **Full graphical suspend/resume failed in this TCG/VirGL
  fixture and remains unresolved.** Process existence alone did not establish
  successful graphical recovery. `/proc/<noctalia-pid>/stack` showed the wait in
  `virtio_gpu_queue_ctrl_sgs` through DRM object cleanup. No new core was produced.
  This does not establish behavior on a physical GPU.
- DrKonqi's user-unit probe reported `ConditionResult=no` in Hyprland.

![Noctalia launcher and Kitty in the actual Fedora VM](tests/vm/evidence/fedora44-noctalia-kitty.png)

## Bugs reproduced and corrected

- Fedora 44 has no supported `polkit-gnome` package in this installation path.
  The installer now uses `polkit-kde` and its verified Fedora executable path.
- Fedora package names: `7zip` replaces p7zip packages; `wget2-wget` provides wget.
- Failed package transactions no longer contaminate future verification manifests.
- Hyprland 0.57.0 with VirGL reproduced Kitty `No EGLConfigs returned` and Noctalia
  `eglChooseConfig failed`. A fresh session with
  `quirks.skip_non_kms_dmabuf_formats = false` allowed both clients to render.
  Generated configs apply this compatibility setting only to version 0.57.0 in a VM.
  The upstream report is [Hyprland discussion 16702](https://github.com/hyprwm/Hyprland/discussions/16702).
  A config reload alone did not recover this particular session; a fresh session did.
- `plasma-drkonqi` 6.6.4 recursively crashed while reporting its own failures.
  `coredumpctl info` showed SIGSEGV in Qt HTML parsing through KF6 notification code.
  Memory was available and no OOM kills were logged. A user-unit condition prevents
  automatic DrKonqi launcher execution in Hyprland, while retaining systemd-coredump
  collection and leaving Plasma sessions unchanged. No new cores appeared after applying it.
  No raw cores or process memory are published.

## Static and native package checks

- All Bash entrypoints passed `bash -n` and ShellCheck 0.11.0.
- Eight Python safety/regression tests passed, including dry-run isolation, failed
  transaction handling, repository validation with Python optimizations, preservation
  of existing Rust toolchains and version/VM gating of the EGL workaround.
- [Fedora container CI](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41193533968)
  installed native dependencies, Noctalia and Polkit, created a Python venv with pip,
  compiled and ran C++ and Rust programs, and passed `dnf5 check`.
  Observed toolchains: Python 3.14.8, GCC 16.2.1, Rust/Cargo 1.99.1.

## Full KVM integration

The manual `Fedora KDE VM integration` workflow downloads and verifies both ISO
images, provisions a new KDE guest, installs selected modules twice, checks modified
config preservation, rejects unvalidated Plasma removal and checks a reboot.
Earlier runs failed in the test fixture (media selection, login-manager choice,
password hash and transient runner KVM permissions), before application testing.
One full run reached the development and browser modules successfully, including
all three JetBrains archives and Arduino, then failed installing OBS: old `kmime`
from the ISO conflicted with new `kf6-kmime`. Fedora's updated kmime package includes
a co-installability fix; the dependencies module now updates installed packages
before adding software. A live `/etc` archive race is reported explicitly while
retaining the archive; fatal archive errors still stop installation.
The latest corrected run is pending. **Full application installation/repeat/reboot
is not yet claimed as passed.**

## Not established by these results

Physical GPU compatibility, real monitor hotplug/HiDPI, laptop energy use, audio
hardware, OBS recording/screenshare, physical lock/suspend/resume, IDE activation and
positive Plasma removal/reinstallation still require separate validation. Installing
an application is not proof that all of its features work. Hyprmod remains explicitly
skipped pending a supported Fedora installation method.
