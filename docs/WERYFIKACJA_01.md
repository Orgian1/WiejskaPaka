# Weryfikacja 01 — blokada przypadkowego uruchomienia produkcyjnego

Wersja developerska **nie jest dopuszczona do produkcji**. Przy `WP_ENV=production`, `prod` lub `live` backend przerywa uruchamianie z komunikatem. Nieznane wartości `WP_ENV` również są odrzucane. Dozwolone są wyłącznie development/dev/test/testing.

Rozszerzono nagłówek `Cache-Control: no-store` dla wrażliwych tras finansowych, księgowych, zamówień i powiadomień. Nie stanowi to zastępstwa dla testów penetracyjnych ani audytu uprawnień.

Testy: `WP_ENV=test python -m pytest -q` — 136 zaliczonych w środowisku lokalnym. Nadal **nie** przeprowadzono testów integracyjnych na działającym PostgreSQL, przeglądarkowych, z PSP, ani przeglądu prawnego. Nie modyfikowano domeny, DNS ani płatności.

Blokady produkcyjnej nie wolno usuwać, dopóki wymagania wydaniowe nie zostaną faktycznie spełnione i udokumentowane.
