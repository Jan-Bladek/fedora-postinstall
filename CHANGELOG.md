# Changelog

## 0.4.0 — 2026-11-02

- TUI wyboru Plasma / Noctalia / DMS, osobna lista opcjonalnych aplikacji do usunięcia,
  jedno podsumowanie zgody, pasek postępu oraz pełny log. Fallback curses bez newt.
- Dodano `--yes`, `--cleanup-apps` i `--keep-hypr-config`; brak ciągłego wpisywania YES.
- Czyszczenie używa jawnej listy RPM, testu zależności, pobrania dokładnych RPM
  do odzyskiwania i kontroli zachowania pozostałych pakietów. uuctl jest ukrywany,
  uwsm zachowany. Nie wyłączamy kworker ani współdzielonych usług systemowych.
- VS Code zastępuje VSCodium w nowych instalacjach; polityka TelemetryLevel=off,
  aktualne desktop IDs Microsoftu i scalanie ustawień JSONC.
- Naprawiono ikony i identyfikatory desktop / StartupWMClass archiwów JetBrains,
  również gdy bieżąca wersja aplikacji jest już zainstalowana.
- Profil Hyprland według Omarchy: odstępy, obramowania, animacje i skróty,
  z aplikacjami Fedory i wybraną powłoką. Poprzedni plik jest kopiowany do backupu.
- JetBrains Mono jako domyślny font, weryfikowane symbole Nerd Fonts, Kitty 90%
  opacity i wyłączone potwierdzanie zamykania, zachowanie innych ustawień terminala.
- LazyVim z przypiętego oficjalnego startera, kopią wcześniejszego środowiska Neovim
  i automatyczną instalacją wtyczek przez lazy.nvim.
- `fedora-update` obejmuje DNF/COPR, Flatpak, archiwa IDE/AppImage, Rustup,
  zarządzany LazyVim, symbole fontów i rozszerzenia VS Code.

## 0.3.0 — 2026-11-01

- Dodano wybór pulpitu w menu i przez `--desktop noctalia|dms|plasma`.
- Wariant Plasma instaluje aplikacje bez konfiguracji Hyprland i blokuje usuwanie KDE.
- Dodano stabilne RPM DankMaterialShell (obecnie Dux Shell), z walidacją
  upstream COPR duxlabs/dms oraz repozytorium zależności duxlabs/dux-repo.
- Jeden selektor obsługuje autostart, skróty i kontrolę IPC Noctalia/DMS.
  DMS nie jest włączany jako globalna usługa sesji Plasma.
- Nie zmieniamy własnych profili powłok. Niezmieniony szablon Hyprland v0.2
  migruje z kopią zapasową; własny plik otrzymuje proponowane zmiany.
- Dodano testy wariantów, menu, konfliktów, źródeł DMS i zachowania konfiguracji
  oraz natywny test instalacji i powtórzenia RPM DMS na Fedorze 44.

## 0.2.1 — 2026-11-01

- Walidacja sesji sprawdza aktywny socket Wayland, włączony monitor i odpowiedź
  IPC Noctalia z limitem czasu. Sama obecność zawieszonego procesu nie wystarcza.
- Usunięto zależność sprawdzenia monitorów od instrukcji Python `assert`, która
  znika przy optymalizacji interpretera.
- `validate-session --check-only` pozwala sprawdzać sesję automatycznie i jawnie
  pozostawia wymóg ręcznej akceptacji przed usunięciem Plasma.
- Dodano `scripts/plan-plasma-removal`: wspólną z modułem listę kandydatów i test
  zależności RPM bez usuwania pakietów. Testy chronią aplikacje KDE i Qt.
- Dodano interaktywny test portalu ScreenCast i rzeczywistych klatek PipeWire.
- Moduł OBS zastępuje atrapę `noopenh264` prawdziwym kodekiem z dostarczanego
  przez Fedorę repozytorium Cisco i sprawdza rzeczywiste kodowanie klatki H.264.
  Pakiety wymagające atrapy po nazwie blokują wymianę zamiast być usuwane.
- Dodano regresję odtwarzającą błąd kodera oraz test trzech zakodowanych klatek,
  powtórzenia konfiguracji i zachowania pozostałych pakietów.
- Wyniki kolejnych prób uśpienia i OBS są opisane w [TESTING.md](TESTING.md).

## 0.2.0 — 2026-10-31

- Naprawiono instalację na Fedora 44: `polkit-kde`, `7zip`, `wget2-wget`,
  ustawianie Bash przez `usermod` oraz repozytorium Hyprland.
- Dodano narzędzia Rust/Cargo, Python/venv/pip i C/C++ z zachowaniem istniejącego rustup.
- Dodano aktualizację bazowych pakietów przed instalacją zależności.
- Poprawiono konfigurację Lua Hyprland, monitory, skróty i integrację Noctalia.
- Dodano ograniczone do Hyprland 0.57.0 w VM obejście regresji EGL/VirGL.
- Zatrzymano rekurencyjne uruchamianie DrKonqi w sesji Hyprland,
  zachowując systemd-coredump i działanie w Plasma.
- Naprawiono instalację Flatpak bez terminala, wraz z wymaganymi runtime’ami.
- Dodano wymagany do dialogów Hyprland pakiet `hyprland-guiutils`.
- Oddzielono manifesty weryfikacji kolejnych uruchomień; nieudana transakcja
  nie zatruwa następnej instalacji. Zachowano konfigurację użytkownika.
- Poprawiono wybór modułów bez whiptail i obsługę jawnego `--modules`.
- Dopasowano domyślny edytor do rzeczywistego wpisu desktop z RPM VSCodium
  i rozszerzono kontrolę powiązań MIME.
- Aktualizator archiwów producentów pomija aplikacje, których nie instalowano.
- Dodano testy natywnych pakietów i kompilatorów Fedora oraz instalacji z
  podpisanych obrazów ISO w jednorazowej maszynie KVM.
- Opublikowano raport i zrzut rzeczywistej sesji Fedora KDE → Hyprland + Noctalia.
  Dokładne wyniki, awarie i nieprzetestowane funkcje: [TESTING.md](TESTING.md).

To wydanie wymaga dalszej walidacji sprzętowej. Samo zainstalowanie pakietów
nie potwierdza działania nagrywania OBS, zewnętrznych monitorów ani usuwania Plasma.
