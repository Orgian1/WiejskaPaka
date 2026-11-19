# Audyt źródeł rozliczeń — 19.11.2026

## Potwierdzone w kodzie
W `backend/app.py` istnieją tabele `commission_drafts`, `invoice_drafts`, `accounting_export_jobs`, `accounting_audit_events` i `accounting_validation_runs`.

**Ważne rozróżnienie:** `commission_drafts` odnosi się do prowizji od zamówienia (`order_id`, `subtotal_grosze`, `rate_basis_points`). Nie jest potwierdzonym rejestrem pobranych opłat za punkty odbioru, reklamy ani prowizji 5% od wypłat sprzedawców. Nie należy łączyć tej tabeli z `monthly_platform_fees` jako źródła zapłaconych opłat.

`invoice_drafts` oraz `accounting_export_jobs` służą do roboczych dokumentów i blokowanych eksportów; nie są fakturami podatkowymi ani potwierdzeniem otrzymania płatności.

## Następny etap integracji
1. Odnaleźć w aktualnej gałęzi implementację portfela i naliczania opłat za punkty/reklamy oraz zidentyfikować autorytatywne, utrwalone zdarzenia.
2. Dla każdego zdarzenia ustalić niezmienny identyfikator, identyfikator sprzedawcy, rodzaj opłaty, kwotę w groszach, datę księgowania, stan płatności i identyfikator korekty.
3. Zaprojektować wyłącznie odczyt danych **potwierdzonych i zaksięgowanych**; nie traktować podglądów, szkiców, doładowań ani kwot sprzedaży jako pobranych opłat.
4. Dopiero potem podłączyć `monthly_fee_audit` i porównać sumy kontrolne z rejestrem źródłowym.
5. Przed wystawianiem faktur przeprowadzić osobną analizę VAT, terminów fakturowania, KSeF i statusu nabywców.

Nie zmieniać zatwierdzonych plików UI ani nie uruchamiać rzeczywistych płatności.
