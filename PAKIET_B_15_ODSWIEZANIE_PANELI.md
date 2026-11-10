# Pakiet B/15 — wyścigi odświeżania paneli

- Każde uruchomienie `loadDashboard()` otrzymuje kolejny numer żądania. Po pobraniu danych interfejs ignoruje wyniki starszych odświeżeń.
- `loadNotifications()` analogicznie odrzuca spóźnione wyniki poprzedniego pobierania.
- Zabezpieczenie numerem żądania uzupełnia dotychczasowe sprawdzanie epoki sesji.
- Zaktualizowano test statyczny dotychczasowej ochrony i dodano dwa nowe testy regresyjne.
- Testy lokalne: 2450 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych; PostgreSQL na żywo i fizyczny telefon nie były testowane.
- Neon, wiejskapaka.pl i rzeczywiste płatności bez zmian.
