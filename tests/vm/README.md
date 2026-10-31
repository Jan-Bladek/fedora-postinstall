# Disposable Fedora KDE VM

Use only with a new, disposable virtual disk. The Kickstart template wipes **vda**.
It must never be used with a host disk passed through to the VM.

1. Download Fedora Everything netinst 44-1.7 x86_64 and its signed CHECKSUM from
   https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/iso/.
2. Verify the CHECKSUM signature with the Fedora 44 key (fingerprint
   `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`) from https://fedoraproject.org/security/,
   then verify the ISO SHA256. Also verify Fedora KDE Live 44-1.7 x86_64 and its signed CHECKSUM. The netinst installer copies the original KDE Live filesystem using the supported Kickstart liveimg command.
3. Substitute `@@SSH_PUBLIC_KEY@@` in fedora44.ks.in with a **test-only public SSH key**.
   Serve the resulting ks.cfg from a localhost HTTP server; QEMU user networking
   exposes that server to the guest as 10.0.2.2. Do not commit private keys.
4. Extract images/pxeboot/vmlinuz and initrd.img from the netinst ISO. Attach both the netinst and KDE Live ISOs. The template locates the KDE ISO by its filesystem label and mounts it read-only and copies its LiveOS/squashfs.img to the virtual disk. Create a new 90 GiB
   qcow2 disk. Boot with the ISO attached, those kernel/initrd files, and arguments
   `inst.stage2=hd:LABEL=Fedora-E-dvd-x86_64-44 inst.ks=http://10.0.2.2:8844/ks.cfg inst.text console=ttyS0,115200n8`.
5. Allocate 8 GiB RAM and 4 virtual CPUs. Use KVM where available; software TCG is
   much slower. Forward **localhost only** port 22244 to guest SSH port 22.
6. After installation, boot the virtual disk, copy this repository into the `tester`
   home directory, and run `bash install.sh --dry-run`, followed by chosen modules
   as tester. The disposable VM grants tester passwordless sudo. This setting is
   a fixture, not a change applied by the real installer.
7. Record the exact module list, package checks, failures, repeat run, reboot,
   `hyprctl configerrors`, Noctalia process and Polkit executable. Test applications
   and lock/suspend/screenshare separately; package installation does not prove them.
8. Keep downloaded ISO, VM disks, keys and raw logs outside the repository. Publish
   only a reviewed report under TESTING.md. Destroy credentials when retiring VM.

On a guest with accelerated virtio graphics, start a local desktop session for the
runtime tests. Running tests through SSH alone does not establish a graphical login.
