# Changelog

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
