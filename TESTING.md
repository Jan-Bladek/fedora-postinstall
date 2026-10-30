# Validation record — 2026-10-30

Host: Omarchy (not Fedora). Nothing installed into the host desktop configuration.

- Bash syntax: all shell entrypoints passed `bash -n`.
- ShellCheck 0.11.0: passed (SC1091 external source resolution excluded; dynamic module source annotated).
- Python unittest: 4 tests passed: dry-run makes no home writes or privileged/network calls; invalid module rejected; unsafe repository definitions rejected; expected vendor definition accepted.
- Live metadata: official JetBrains API returned RR 2026.2.5, IIU/WS 2026.2.4. Arduino official GitHub release returned 2.3.10 AppImage with SHA256. No IDE binaries executed on host.
- Repository definitions fetched: Brave documented endpoint, LibreWolf, VSCodium, Tailscale generic Fedora endpoint and lionheartp Fedora 44 COPR definition. This verifies endpoints, NOT successful RPM dependency resolution on Fedora.
- Full Fedora installation, KDE removal/reinstallation, Lua runtime API, Polkit path, portal capture, lock, idle, sleep/resume, GPU acceleration and repeat installation: NOT TESTED.
- Docker daemon unavailable to current user; no Fedora container/VM tests performed. Containers would not validate a graphical session anyway.

Release gate for production: validate all untested items on a disposable Fedora KDE 44 VM and target hardware first. Review the conservative removal allowlist if additional Plasma packages are present. Do not claim all requested applications were installed: Hyprmod is explicitly deferred.
