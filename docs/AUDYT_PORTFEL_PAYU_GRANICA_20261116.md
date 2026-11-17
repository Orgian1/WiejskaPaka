# Audyt granicy portfela i przygotowania PayU — 2026-11-16

## Potwierdzony stan kodu

- Aktywny portfel demo znajduje się w `backend/wallet_preview.py`, instalowany przez `backend/app.py`. Działa wyłącznie po `WP_ENABLE_WALLET_PREVIEW=1` w środowisku test/development.
- Endpoint `POST /wallet/topups` w trybie demo **bezwarunkowo** dopisuje symulowane środki; nie jest i nie może być endpointem płatności produkcyjnej.
- Endpoint `POST /wallet/withdrawals` rezerwuje kwotę brutto, wymaga PIN i zapisuje zamrożone warunki wypłaty. Finalizacja jest wyłącznie testowa, nie wysyła pieniędzy.
- Właściwe reguły naliczania prowizji są w `backend/invoicing.py`; istniejący portfel korzysta z `calculate_commission_grosze`. Nowe testy `tests/test_payu_wallet_compatibility.py` porównują je z pomocniczymi obliczeniami PayU dla klienta i rolnika.
- Moduły `backend/payu_*.py` są na razie odrębnym przygotowaniem; nie są podłączone do rzeczywistego salda, a dziennik `payu_journal_schema.py` jest wyłącznie schematem testowym.
- `backend/payu_journal_events.py` wymaga uprzednio **uwierzytelnionego** zdarzenia. Sam moduł nie weryfikuje podpisów ani nie wykonuje księgowania.
- Reklamy portfela są osobnym modułem `backend/wallet_ads.py` i frontendem `web/wallet-ads.js`, nie powinny modyfikować salda.

## Blokery przed uruchomieniem PayU

1. Zaimplementować oddzielny endpoint inicjacji płatności, który **nie** korzysta z `wallet_preview.move(..., 'topup')` i nie uznaje salda przed weryfikacją po stronie serwera.
2. Dodać autentykację zdarzeń dostawcy oraz kontrolę zgodności identyfikatora zamówienia, waluty, kwoty i właściciela operacji.
3. Zapewnić transakcyjne, dokładnie jednokrotne księgowanie po uwierzytelnieniu i potwierdzeniu wpłaty, z unikalnym identyfikatorem zapisu księgowego.
4. Obsłużyć niezależnie pełne i częściowe zwroty, rozliczenie wypłat, niepowodzenia i uzgadnianie rozbieżności.
5. Uzgodnić z operatorem przepływy marketplace, wypłaty, KYC i regulacje. Dopiero wtedy włączyć prawdziwy adapter PayU.
6. Przeprowadzić kompleksowe testy HTTP i przeglądarkowe: portfel, reklamy, RLS, równoległe zdarzenia, restart i PostgreSQL; osobno zatwierdzić wygląd.

## Wynik weryfikacji

GitHub Actions run `43958349394`: zakończony sukcesem dla zestawu testów reklam, przygotowania PayU i zgodności obliczeń portfela. To **nie** potwierdza ukończenia integracji ani wszystkich testów end-to-end. Nie scalono gałęzi i nie wdrożono produkcji.
