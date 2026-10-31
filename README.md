# Fedora Post-Install · Hyprland + Noctalia

Modułowy instalator Bash dla istniejącej **Fedory 44 x86_64 (DNF5, wariant klasyczny, także KDE Desktop)**. To projekt do walidacji w maszynie wirtualnej przed użyciem na głównym komputerze. Nie jest nową dystrybucją. Fedora Atomic, starsze/nowsze wydania i ARM są świadomie blokowane. Pełna instalacja graficzna **nie została przetestowana na Fedorze**; testy statyczne nie zastępują tej weryfikacji.

Wymagania: konto użytkownika z sudo, SELinux Enforcing, internet, Wayland-capable GPU; praktycznie 8 GB RAM i co najmniej 30 GB wolnego miejsca dla IDE i kopii. Zalecane 16 GB RAM dla pracy z JetBrains/OBS. Dane prywatne i katalog domowy wymagają niezależnej kopii zapasowej.

## Uruchomienie

```bash
git clone https://github.com/Jan-Bladek/fedora-postinstall.git
cd fedora-postinstall
bash install.sh --dry-run
bash install.sh
```

Nie uruchamiaj całego instalatora przez sudo. Jeżeli dostępny jest `whiptail`, pojawia się checklist TUI; bez niego używana jest domyślna lista modułów. Repozytoria i destrukcyjny etap zawsze wymagają osobnych potwierdzeń. `--dry-run` działa również poza Fedorą, drukuje pełne moduły i nie wywołuje menedżerów pakietów, sudo ani pobierania. Nie rozwiązuje zależności bez metadanych systemu docelowego.

Wybór modułów bez TUI:

```bash
bash install.sh --modules "snapshots dependencies hyprland noctalia terminal updates"
```

Zachowaj kolejność powyżej. Moduły aplikacji potrzebują dostępu do sieci i curl/python3. Domyślna pełna lista instaluje dependencies jako pierwsze po snapshotach. Każdy przebieg tworzy nowy katalog logów i własną listę oczekiwanych pakietów zapisywaną po udanych transakcjach; po błędzie napraw przyczynę i uruchom ponownie. Nie ma automatycznego pomijania modułu tylko dlatego, że poprzednio zapisano go w logu.

## Moduły i źródła

| Moduł | Działanie i źródła |
|---|---|
| snapshots | Pakiety, jednostki systemd, kopia /etc i ~/.config; opcjonalny Snapper dla Btrfs |
| dependencies | Git, curl, wget, archiwizacja, narzędzia diagnostyczne, wl-clipboard, newt |
| hyprland | Fedora RPM; jeśli brak Hyprland, oferuje wskazany przez dokumentację Noctalia COPR lionheartp/Hyprland |
| noctalia | Natywny RPM `noctalia` v5, ustawienia pierwszego uruchomienia producenta |
| terminal | Kitty, Bash, EDITOR/VISUAL/TERMINAL |
| development | Rust/Cargo, Python 3 (pip, nagłówki), C/C++ (GCC, CMake, Ninja, GDB), VSCodium RPM producenta; RustRover, IntelliJ IDEA, WebStorm z oficjalnego API JetBrains; Arduino IDE 2 AppImage z GitHub Arduino |
| browsers | Brave i LibreWolf z repozytoriów dostawców |
| multimedia | OBS z Fedory; Vesktop i Steam z Flathub |
| utilities | Obsidian i LocalSend z Flathub; Tailscale RPM, tailscaled bez logowania |
| defaults | Brave HTTP/HTTPS/HTML, VSCodium text/plain, terminal Kitty |
| optimization | Diagnostyka; zachowanie zarządzania energią Fedory, zram i zabezpieczeń |
| updates | Polecenie ~/.local/bin/fedora-update |
| kde-removal | Oddzielny, potwierdzany etap z działającej sesji Hyprland |

Źródła są sprawdzane w chwili uruchomienia: brak pakietu, niedostępne repozytorium lub niezgodna konfiguracja zatrzymują instalację. Nie wymuszamy `--allowerasing`, nie dodajemy AUR ani przypadkowych zamienników. Repozytoria mają kontrolę HTTPS, hostów i `gpgcheck`; DNF pokazuje klucz do zaakceptowania. To nie jest niezależna weryfikacja tożsamości klucza: porównaj fingerprint z dokumentacją dostawcy przed zaufaniem. COPR jest repozytorium społecznościowym, nie oficjalnym repo Fedory. Zmiana już istniejącego pliku .repo wymaga ręcznego przeglądu.

Priorytet źródeł nie oznacza instalowania nieutrzymywanych RPM z przypadkowych repozytoriów. Flathub wybrano dla aplikacji bez potwierdzonego, utrzymywanego natywnego źródła w tym projekcie. Steam korzysta z Flathub zamiast włączania RPM Fusion dla jednej aplikacji. Manifesty Flathub nie muszą być utrzymywane przez autorów aplikacji.

**JetBrains:** Toolbox jest zalecaną przez producenta opcją interaktywną, lecz ten projekt używa oficjalnych archiwów IDE, aby rzeczywiście automatyzować instalację wszystkich trzech programów bez nieudokumentowanego sterowania GUI Toolbox. Nie są zarządzane przez Toolbox. Licencję/trial aktywuje użytkownik. Pobieranie porównuje SHA256 z API/checksum dostawcy, zapisuje origin.json, zachowuje starsze wersje i przełącza symlink current. Te sumy chronią integralność transportu, nie stanowią niezależnego podpisu producenta. Arduino bez opublikowanego digest SHA256 jest blokowane. Dostęp do portów szeregowych: po przeglądzie `sudo usermod -aG dialout "$USER"`, potem ponowne logowanie; nietypowe płytki wymagają reguł udev producenta. Nie instalujemy reguł MODE=0666.

**Hyprmod:** zidentyfikowano https://github.com/BlueManCZ/hyprmod. Projekt GTK4/libadwaita istnieje, ale brak potwierdzonego pakietu/wsparcia Fedora; instalator zgłasza pominięcie i zapisuje manual-actions. Nie wykonuje curl | sh. To jawnie nieukończony element listy aplikacji.

## Sesja i konfiguracja

Konfiguracja wymaga Hyprland >=0.55 z Lua oraz Noctalia v5. Nie instaluje starego v4/Quickshell ani Waybar, dunst czy osobnego launchera. Noctalia obsługuje interfejs, powiadomienia, schowek i funkcje sesji. Ustawienia Noctalia tworzy sam upstream; projekt nie wymyśla schematu settings. Dobierz idle, blokadę, monitory i skalowanie w ustawieniach Noctalia, następnie przetestuj przed usuwaniem Plasma.

Super+Enter: Kitty; Super+Space: launcher; Super+S: panel; Super+B: Brave; Super+Q: zamknij; Super+F: fullscreen; Super+1–9: workspace; Shift+Super+1–9: przenieś okno. Układ klawiatury PL. Audio i screencast używają PipeWire/WirePlumber i portalu Hyprland, file chooser portalu GTK. Polkit uruchamia natywny pakiet Fedory `polkit-kde` (`/usr/libexec/kf6/polkit-kde-authentication-agent-1`). Agent pozostaje po usunięciu Plasma. SDDM jest instalowany jako dostępny zamiennik; istniejący menedżer logowania jest zachowany. Fedora KDE 44 domyślnie używa Plasma Login Manager, nie SDDM ([zmiana Fedory](https://fedoraproject.org/wiki/Changes/PlasmaLoginManager)). Wybierz Hyprland na ekranie logowania; zapamiętanie sesji zależy od menedżera logowania. Nie włączamy autologowania.

Pliki użytkownika nie są nadpisywane; propozycja trafia do `.fedora-postinstall-new`. Przy istniejącym hyprland.conf/Lua konieczne jest ręczne scalenie i sprawdzenie, którą konfigurację ładuje compositor. Zmienne środowiskowe environment.d wymagają nowego logowania. Dodaj ~/.local/bin do PATH. Brak uniwersalnego standardu domyślnego terminala: TERMINAL, MIME i skrót sesji wskazują Kitty.

## Usuwanie Plasma i odzyskiwanie

Po pierwszej instalacji wyloguj się i zaloguj do Hyprland. Sprawdź także Wi-Fi, Bluetooth, zewnętrzne monitory, blokadę, uśpienie i wybudzenie. Następnie:

```bash
bash scripts/validate-session
bash install.sh --modules "kde-removal"
```

Etap wymaga aktywnej sesji, monitorów, braku błędów konfiguracji, procesu Noctalia, usług i ręcznego potwierdzenia testów. To test zdrowia plus akceptacja człowieka, nie dowód działania każdej funkcji. RPM analizuje zależności dokładnej listy. Jeśli zachowany pakiet wymaga Plasma, operacja zostaje zablokowana; nie rozszerza listy kosztem aplikacji. Archiwa dokładnych wersji RPM muszą być dostępne do pobrania przed usunięciem. Brak wersji w repozytorium blokuje usuwanie. Usunięcie używa `rpm -e` z zależnościami, bez kaskady i autoremove; końcowe `dnf5 check` weryfikuje bazę.

Lista jest konserwatywna: lokalne dodatki Plasma spoza listy mogą pozostać. Ich usunięcie wymaga osobnego audytu. Autostarty należące do usuniętych RPM znikają wraz z nimi; własne autostarty użytkownika pozostają do przeglądu. Qt i aplikacje KDE są chronione przez zachowanie wszystkich pakietów spoza listy, a nie przez nazwy kilku aplikacji. Lista wszystkich zachowanych pakietów jest sprawdzana po operacji.

TTY: Ctrl+Alt+F3, zaloguj się. Logi i kopie: `~/.local/state/fedora-postinstall/runs/`. Znajdź przebieg z plasma-rpms, następnie:

```bash
sudo dnf5 install ~/.local/state/fedora-postinstall/runs/ODPOWIEDNI-PRZEBIEG/plasma-rpms/*.rpm
sudo systemctl restart display-manager.service
```

Restart display managera kończy bieżące sesje. Kopię konfiguracji rozpakuj najpierw do osobnego katalogu i przywracaj wybrane pliki; nie nadpisuj bezmyślnie całego /etc. Pełne przywrócenie profilu systemu nie jest automatyczne: repozytoria, usługi, nowo zainstalowane programy i zmiany użytkownika trzeba przejrzeć względem zapisanych manifestów. Snapshot root nie obejmuje zwykle /home ani EFI/boot. Nie zakładamy bootowania snapshotów; odzyskanie Snapper może wymagać live USB, montowania subwoluminów i instrukcji właściwych dla układu dysku. Brak snapshotu oznacza kopie plików i RPM, nie transakcyjny rollback.

## Aktualizacje i odinstalowanie

`fedora-update` aktualizuje DNF (w tym włączone COPR i Noctalia), Flatpak użytkownika i systemowe, następnie sprawdza oficjalne wydania IDE/Arduino i pyta o aktualizację. Nie wykonuje git pull i nie dotyka konfiguracji. Przy większej zmianie API Noctalia/Hyprland trzeba przeczytać release notes i sprawdzić configerrors; nie ma gwarancji zgodności przyszłych RPM. Zachowane stare katalogi aplikacji umożliwiają ręczne cofnięcie symlinka current. Odinstalowanie archiwów: usuń odpowiedni katalog ~/.local/share/fedora-postinstall/apps/NAZWA oraz własny symlink i plik fedora-postinstall-NAZWA.desktop. RPM/Flatpak usuwaj normalnym menedżerem, po sprawdzeniu zależności.

## Diagnostyka i ograniczenia

`journalctl --user -b`, `journalctl -b -u sddm`, `hyprctl configerrors`, `systemctl --user status pipewire wireplumber xdg-desktop-portal-hyprland`, `sudo dnf5 check`. Z Noctalia korzystaj z natywnego screenshot UI; w OBS wybierz PipeWire. Zgoda portalu jest interaktywna. Akceleracja OBS/kodeki/NVIDIA zależą od GPU i dostępności sterowników; instalator nie obiecuje NVENC/VAAPI bez testu. LocalSend potrzebuje zgody firewall na właściwej zaufanej sieci; nie otwieramy portów globalnie. Tailscale uruchamia się bez `tailscale up` i bez konta.

TUI wymaga wcześniej dostępnego newt/whiptail, w przeciwnym razie wybierz moduły argumentem. Nie ma jeszcze testów VM ani automatycznego przywracania pełnego stanu, potwierdzonego wsparcia Hyprmod ani walidacji GPU. Przed użyciem produkcyjnym potrzebna jest pełna instalacja Fedora KDE 44 w VM, drugi przebieg, test błędu sieci, przerwania, rollback RPM oraz sprzętowe testy lock/suspend/screenshare. Instalator zatrzymuje się przy błędach zamiast deklarować sukces.

## Testy

```bash
bash tests/check.sh
```

Bash -n, ShellCheck i unittest sprawdzają m.in. brak zmian/sudo/sieci w dry-run oraz odrzucanie niebezpiecznych repozytoriów. CI uruchamia te same testy. Wyniki lokalne: patrz TESTING.md.

## Dokumentacja źródłowa (sprawdzana 2026-10-30)

- [Fedora: zarządzanie pakietami](https://docs.fedoraproject.org/en-US/quick-docs/dnf/)
- [Hyprland: instalacja](https://wiki.hypr.land/Getting-Started/Installation/)
- [Noctalia: instalacja v5](https://docs.noctalia.dev/noctalia/getting-started/installation/)
- [Noctalia: Hyprland Lua](https://docs.noctalia.dev/noctalia/compositor-settings/hyprland/)
- [Brave RPM](https://brave.com/linux/), [VSCodium RPM](https://repo.vscodium.dev/), [LibreWolf RPM](https://rpm.librewolf.net/repodata/)
- [JetBrains Toolbox](https://www.jetbrains.com/help/toolbox-app/installation.html), [IDEA](https://www.jetbrains.com/help/idea/installation-guide.html)
- [Arduino IDE 2](https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing)
- [Tailscale ręczne repozytoria](https://pkgs.tailscale.com/stable/)
- [Vesktop Flathub](https://flathub.org/apps/dev.vencord.Vesktop), [Steam](https://flathub.org/apps/com.valvesoftware.Steam), [Obsidian](https://flathub.org/apps/md.obsidian.Obsidian), [LocalSend](https://flathub.org/apps/org.localsend.localsend_app)

## Języki programowania

Moduł `development` instaluje Python 3, pip, python3-devel oraz GCC/G++,
Make, CMake, Ninja, GDB i pkg-config z repozytoriów Fedory. Do projektów Python
używaj `python3 -m venv .venv`, następnie `source .venv/bin/activate`;
nie instaluj bibliotek przez sudo pip.

Rust domyślnie pochodzi z podpisanych pakietów Fedory: rust, cargo, clippy,
rustfmt i rust-src. Jeśli istnieje rustup, instalator korzysta z niego i zapewnia
stable z komponentami domyślnymi oraz rust-src, zachowując domyślny toolchain
użytkownika. Nie miesza pakietów Rust z rustup. `fedora-update` aktualizuje
pakiety przez DNF i istniejące toolchainy rustup przez `rustup update` jako użytkownik.
Źródło: [Fedora Developer Portal — Rust](https://developer.fedoraproject.org/tech/languages/rust/rust-installation.html).

## Aktualizacja po błędzie polkit-gnome

Wersja 0.2.0 zastępuje niedostępny `polkit-gnome` natywnym `polkit-kde`,
przestarzałe pakiety p7zip pakietem 7zip i używa nazwy RPM wget2-wget.
Po `git pull` uruchom instalator ponownie. Stare, nieudane wpisy oczekiwanych
pakietów nie są już odczytywane przy weryfikacji nowego przebiegu.
Jeżeli masz wcześniejszą konfigurację Hyprland, sprawdź proponowany plik
`~/.config/hypr/hyprland.lua.fedora-postinstall-new` i zastąp w swojej konfiguracji
polecenie agenta Polkit ścieżką `/usr/libexec/kf6/polkit-kde-authentication-agent-1`.
Nie uruchamiaj równocześnie dwóch agentów. Wersję sprawdzisz przez
`bash install.sh --version`.
