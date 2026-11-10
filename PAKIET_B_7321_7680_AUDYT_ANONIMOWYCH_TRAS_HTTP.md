# WiejskaPaka — B/7321–B/7680: audyt anonimowego dostępu przez HTTP

## Wykonane kontrole

- Dodano `scripts/audit_anonymous_http_routes.py`: automatyczne żądania HTTP do każdej trasy wymagającej logowania, bez tokenu, na prawdziwym lokalnym serwerze Uvicorn.
- Serwer używa jednorazowej bazy SQLite i środowiska wyczyszczonego z danych PostgreSQL/Neon.
- Sprawdzono **78 tras niepublicznych**: **78 odpowiedzi 401/403**, **0 wyników niejednoznacznych**, **0 tras wymagających natychmiastowego przeglądu z powodu nieoczekiwanej odpowiedzi**.
- Zapisano szczegółowy raport `RAPORT_ANONIMOWE_TRASY_HTTP_B_7321_7680.json`.
- Dodano 3 testy regresyjne: **3/3 PASS**.
- Ponownie uruchomiono zestaw akceptacyjny HTTP: **4/4 zestawy PASS**.
- `node --check web/app.js`: PASS; `python -m compileall -q backend scripts`: PASS.

## Zakres i ograniczenia

- Testy potwierdzają, że **anonimowe żądania** nie przechodzą do 78 chronionych tras. **Nie dowodzą** poprawności uprawnień między zalogowanymi użytkownikami ani ochrony wszystkich obiektów.
- Nie uruchomiono rzeczywistego PostgreSQL, przeglądarki Chromium połączonej sieciowo ani testów na fizycznych telefonach.
- Nie podłączano rzeczywistych płatności, domeny, hostingu ani Neon.
- Lokalna aplikacja **nie jest jeszcze zatwierdzona produkcyjnie**.
