# Validation record — updated 2026-11-01

**Full Fedora KDE 44 CLI installation, repeat and reboot passed** in
[the follow-up KVM run](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41304027246).
The separate local VM demonstrated Noctalia/Kitty GUI, lock/unlock, portal frames
and a short OBS recording. Graphical suspend/resume failed in its TCG/VirGL setup
on both tested kernels. Positive Plasma removal is untested.


## Follow-up validation — v0.2.1

[Full KVM run 41304027246](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41304027246)
passed at runtime commit `641709d`: all 12 default modules, repeat installation,
compiler programs, configuration preservation, removal guards, reboot and DNF check.
[Result JSON](tests/vm/evidence/fedora44-kvm-result-v0.2.1.json) records this run.
It is an SSH-only fixture; it does not establish graphical suspend or recording.

[Focused application run 41304746513](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41304746513)
passed at `bd3af75`, including the later protection for placeholder-specific SDKs.
It deliberately installed Fedora's `noopenh264` stub, reproduced the encoder
failure, invoked the real codec helper twice, and encoded/decoded three H.264 frames
at 64×64. No original RPM other than the placeholder was removed, and `dnf5 check`
passed. The same job also installed the selected Flatpaks/vendor RPMs and checked
browser/editor associations. The [static/native checks](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41304746404)
passed Bash syntax, ShellCheck and **12** safety/regression tests. The local suite
also passed all 12 tests on November 1.

In the local graphical guest, `tests/vm/portal-smoke.py` received **three actual
1280×800 RGB frames**, each with 256 distinct byte values, after interactive monitor
approval in the Hyprland portal. This verifies a real ScreenCast/PipeWire frame path,
rather than just the presence of services. The captured desktop was reviewed before
publication:

![Actual frame received from the ScreenCast portal](tests/vm/evidence/fedora44-portal-frame.png)

Native OBS 32.1.1 was then tested interactively on kernel 7.2.13-200.fc44 with
real OpenH264. After approving the PipeWire screen source, Start/Stop Recording
produced a finalized 313344-byte MP4 lasting **12.501 seconds**. FFprobe decoded
**375 H.264 video frames at 1024×640** and an AAC audio stream. A frame extracted
from the actual recording shows the captured desktop:

![Decoded frame from the actual OBS recording](tests/vm/evidence/fedora44-obs-decoded-frame.png)

[FFprobe JSON](tests/vm/evidence/fedora44-obs-probe.json) records the file result.
This was software encoding in TCG/VirGL: OBS reported **84.8% rendering lag** and
**2.1% encoding lag**. It establishes a working short screen recording, not smooth
performance or hardware acceleration. The audio source was a virtual null monitor;
physical microphone/speaker capture and streaming were not tested. OBS subsequently
closed normally with zero reported memory leaks. An earlier incomplete recording was
0 bytes and was not counted as success. The older OBS process crashed while closing
its preview (`obs_enter_graphics` in the core backtrace); that shutdown crash is not
claimed fixed by replacing the codec. No raw core or full video is published.

`validate-session --check-only` passed in a healthy real session, including after
cold boot on kernel 7.2.13-200.fc44. New regression tests reject missing/disabled
monitors and failed Noctalia IPC even with `PYTHONOPTIMIZE=1`. This automatic mode
does not authorize removal; the destructive module still requires manual acceptance.

The read-only Plasma plan was exercised in local and KVM guests. `rpm -e --test`
reported dependencies from `sddm-wayland-plasma`, `plasma-login-manager`,
`plasma-setup`, Fedora look-and-feel, Discover and NetworkManager subpackages.
Complete installed-RPM inventories matched before and after the test. KDE apps and
Qt remained installed. The refusal is intentional: simply installing SDDM does not
replace its KWin-dependent greeter. **Positive Plasma removal remains unvalidated**;
no dependency blockers were automatically deleted or manual acceptance fabricated.

A fresh deep/S3 test on kernel **7.2.13-200.fc44** reproduced the graphical resume
failure after OBS had closed. QEMU reported suspended, `system_wakeup` resumed the
kernel and SSH with the same boot ID, and the journal reported `PM: suspend exit`.
The display remained inactive. Session validation could not complete because
Hyprland instance discovery returned an IPC error (`Resource temporarily unavailable`). This kernel update did not resolve graphical
resume in this local fixture.

The earlier kernel 6.19 s2idle follow-up also failed graphical recovery. RTC and
keyboard did not wake it; an ACPI power-button event resumed the kernel, but Noctalia
IPC failed and graphics did not recover. No permanent sleep-mode override is shipped.

## Original v0.2.0 validation: actual Fedora KDE VM

A separate QEMU VM was created from the Fedora 44 KDE Live filesystem, using the
Fedora Everything netinst installer. The host is Omarchy; `/dev/kvm` is unavailable
locally, so local tests used TCG with 4 virtual CPUs, 8 GiB RAM and virtio/virgl.
The guest booted from its own Btrfs virtual disk with kernel 6.19.10-300.fc44,
SELinux **Enforcing** and NetworkManager active. A baseline qcow2 snapshot exists
outside the repository. Existing host desktop configuration was not modified.
After local checks the guest powered off normally; an additional offline qcow2
snapshot `hyprland-noctalia-core-tested` records the tested desktop state.

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

## Local guest results

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
- After the failed resume, a normal shutdown/reboot did not finish. The disposable
  QEMU process was power-cycled, Fedora booted its disk again, and starting SDDM
  restored Noctalia. The local fixture now enables SDDM/graphical.target explicitly;
  this does not test the installer's preservation of Plasma Login Manager.
- The compositor warned that `hyprland-guiutils` was absent. Version 0.2.2-2.fc44
  installed successfully from the existing lionheartp COPR in the local guest;
  this runtime dependency is included in the desktop module and in both
  subsequent successful full KVM passes.
- A terminal-module rerun retained a deliberately modified Kitty config unchanged
  (matching SHA256), wrote a proposed `.fedora-postinstall-new`, and exited 0,
  including `dnf5 check`. This also exercised the corrected live-backup handling.

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
- The text selection fallback was exercised through a local PTY with whiptail
  hidden; `EXIT` returned 0 before preflight or system changes. Explicit `--modules`
  now bypasses the menu; whiptail output is normalized before module verification.
  Whiptail rendered at 80×24 and 100×32 in local PTYs; Cancel returned 0.
  Full interactive checklist use on Fedora has not been validated.
- Nine Python safety/regression tests passed, including dry-run isolation, failed
  transaction handling, repository validation with Python optimizations, preservation
  of existing Rust toolchains, rejection of an incorrect editor default with whitespace-separated module lists, and version/VM gating of the EGL workaround.
- [Fedora container CI](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41193533968)
  installed native dependencies, Noctalia and Polkit, created a Python venv with pip,
  compiled and ran C++ and Rust programs, and passed `dnf5 check`.
  Observed toolchains: Python 3.14.8, GCC 16.2.1, Rust/Cargo 1.99.1.

## Full KVM integration

[Final run 41220450322](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41220450322)
**passed** at runtime-code commit `e634617`, including the final VSCodium MIME fix.
[Result JSON](tests/vm/evidence/fedora44-kvm-result.json) records the module list,
ISO hashes and the explicit SSH-only graphical-session limitation.

- Download and signature/SHA256 verification of both official ISO images.
- Unattended provisioning of the stock KDE Live filesystem to a Btrfs virtual disk.
- All 12 default modules installed and installed again successfully.
- Python venv/pip, compiled-and-executed C++ and Rust smoke programs.
- Hyprland's own parser accepted the generated Lua configuration.
- A deliberately changed Kitty config retained its exact SHA256; a proposed new
  configuration was written alongside it.
- Removal outside a validated Hyprland session failed, leaving RPM lists unchanged.
- Reboot from the guest disk succeeded, followed by `dnf5 check`.
- SELinux remained Enforcing; NetworkManager and tailscaled were active without
  any Tailscale account login. Bluetooth runtime was skipped: no adapter in this VM.

After reboot: kernel 7.2.13-200.fc44, Hyprland 0.57.0, Noctalia 5.4.0,
Kitty 0.49.2, Polkit KDE 6.7.5 and Plasma Desktop 6.7.5. Plasma was retained.
An [earlier full pass](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41218983387)
verified the same installation/repeat/reboot path before the final editor MIME fix.
The KVM fixture did not start a graphical session; GUI evidence is from the local VM.

The [application smoke test](https://github.com/Jan-Bladek/fedora-postinstall/actions/runs/41220447418)
also passed in a disposable Fedora 44 container: Vesktop, Steam, Obsidian and LocalSend
with their runtimes, plus Brave 1.98.63, LibreWolf 159.0, VSCodium 1.143.17232
and Tailscale 1.104.4. It read back all four browser MIME associations,
`xdg-settings get default-web-browser`, the RPM-owned VSCodium desktop association
and passed `dnf5 check`. Its privileged container is a hosted-runner fixture for
bubblewrap; the installer does not change host container permissions. This container
test did not claim a running systemd tailscaled service.

Earlier fixture failures (media selection, login manager, password hash, KVM device
permissions and an absent test-account config directory) were corrected. Runtime
tests additionally exposed old `kmime` conflicting with `kf6-kmime`, Flatpak declining
runtime installation without a TTY, and VSCodium's changed desktop ID. The fixes are:
base-package upgrade before application installation, explicit noninteractive Flatpak
flags, and selection/verification of a desktop file owned by the installed codium RPM.
Fedora's updated kmime contains the
[co-installability fix](https://packages.fedoraproject.org/pkgs/kmime/kmime/fedora-44-updates.html).
A live `/etc` archive race is logged while retaining the archive; fatal tar failures
still abort installation. Raw cores, VM disks, keys and private backup archives are
not published.

## Not established by these results

Physical GPU compatibility, real monitor hotplug/HiDPI, laptop energy use, audio
hardware, sustained OBS recording/streaming and hardware encoding, physical lock/suspend/resume, IDE activation and
positive Plasma removal/reinstallation still require separate validation. Installing
an application is not proof that all of its features work. Hyprmod remains explicitly
skipped pending a supported Fedora installation method.
