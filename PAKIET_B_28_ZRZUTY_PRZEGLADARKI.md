# Pakiet B/28 — zrzuty widoku mobilnego

Rozszerzono istniejący test Chromium o **opcjonalne** zrzuty publicznej strony
przy szerokościach 320, 390 i 1280 px. Zrzuty nie obejmują logowania ani
prywatnych paneli użytkowników. Bez flagi `--screenshots` nic nie zapisuje.

Uruchomienie na komputerze z Playwright i Chromium:

```bash
python -m scripts.check_mobile_browser --screenshots ./podglad_mobilny
```

Pliki PNG zostaną zapisane w katalogu `podglad_mobilny`. Przed ich
udostępnieniem należy obejrzeć je ręcznie. Test korzysta z jednorazowej
bazy SQLite i localhost, nie łączy się z Neon. Samo sprawdzenie zrzutów
nie zastępuje testu na fizycznym telefonie.
