# WIEJSKAPAKA — FINAL WYGLĄD + RLS + REKLAMY (2026-11-16)

**Jedyna jednoznaczna nazwa tej wersji:** `WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116`.

**Gałąź bazowa:** `release/demo-final-20261116` (zawiera kod z `integration/demo-final-candidate-20261116`, którego historią są PR #62 RLS, #63 reklamy i #64 oceny). Wywodzi się z `codex/demo-finalization-20261112`, gdzie opisano zaakceptowane poprawki interfejsu. Bazowe układy stron, produktów i paneli nie były przepisywane w tym pakiecie. **Uwaga:** sam GitHub nie potwierdza wizualnej zgodności z ekranem zaakceptowanym przez użytkownika; wymaga porównania przeglądarkowego przed nazwaniem demo ostatecznym.

## Co jest w tej gałęzi
- Dotychczasowe RLS, endpointy, PIN, rozliczenia groszowe, reklamy portfela i oceny sprzedawców pozostają w bazie gałęzi.
- Reklama po kliknięciu Portfel: wyraźny czerwony X oraz czerwony licznik 5–1, X nieaktywny przed upływem 5 sekund, automatyczne otwarcie portfela; obowiązuje istniejący atomowy limit jednej emisji na konto / 30 minut, wspólny dla urządzeń.
- `audience` kampanii: `klient` / `rolnik` / `both` (wartość odziedziczona dla starszych kampanii). Administrator ustawia odbiorców, a backend wybiera reklamy na podstawie prawdziwej roli z sesji. Nowe kampanie w panelu domyślnie kierowane są do klientów; dla sprzedawców tworzy się oddzielne kampanie. Przed testami należy dodać po jednej aktywnej kampanii dla każdej roli; historyczne `both` mogą nadal trafić do obu grup.
- Schema SQLite uruchamianego demo przechodzi bezstratną aktualizację istniejącej tabeli. Nowy schemat PostgreSQL zawiera kolumnę w ręcznej migracji 002, a już istniejący schemat RLS dostaje osobną ręczną migrację 004.
- Żadnych zmian środowiska produkcyjnego, serwera VPS, kont PayU, prawdziwych rozliczeń, PIN, sald czy cen.

## Odbiór przed ogłoszeniem gotowości
1. Uruchomić niezależnie testy `tests/test_wallet_ads_http.py`, `tests/test_wallet_ads_browser.py`, pełną regresję, bramkę PostgreSQL FORCE RLS i testy schematu lock; przejrzeć wyniki, bez uznawania starszych PASS za nowe.
2. W Chromium 320 i 1280 px porównać zatwierdzony katalog produktów/rzędy, rozwijane szczegóły, górny pasek, panelem klienta i sprzedawcy. Zweryfikować czerwony X i samoczynne zamknięcie po 5 sekundach.
3. Sprawdzić admin: kampania klienta nie może wyświetlić się sprzedawcy; kampania sprzedawcy nie może wyświetlić się klientowi, obie działają niezależnie od sesji/urządzenia, z limitem konta 30 minut. Przetestować kampanie bez aktywnych emisji oraz awarie serwera reklam.
4. Test PostgreSQL tylko na osobnej bazie: dotychczasowa kolejność `001`, `002`, `003`, a potem `004_wallet_ads_audience.up.sql` dla już istniejącej bazy. **Nie uruchamiać nowego 002 na starej bazie, na której jest już 002 bez audience.** Gdy buduje się zupełnie nowy schemat, kolumna jest w obecnej definicji 002, więc 004 jest idempotentnym potwierdzeniem. Przed migracją obowiązują wcześniejsze blokady zgodności ACL i bezpieczeństwa; rollback 004 ustawia wartości `both`, zachowując dane.
5. Nie scalać do main, nie wdrażać produkcji ani VPS bez niezależnego odbioru.

**Stan na utworzenie gałęzi:** zapisano kod, migrację i nowe przypadki testowe w GitHub. Nie wykonano niezależnego uruchomienia testów ani wizualnego porównania. Ta nazwa umożliwia jednoznaczne odnalezienie źródła bez szukania starych okien czatu.
