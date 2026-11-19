# Źródła danych portfela — audyt techniczny 19.11.2026

Przejrzano `backend/app.py`, `backend/wallet_preview.py`, `backend/wallet_withdrawals.py`, `backend/payment_store.py` i `backend/wallet_ads.py` na gałęzi zatwierdzonego wyglądu.

## Ustalenia
- `wallet_preview_entries` rejestruje **symulowane** doładowania i wnioski o wypłatę. Samo `kind='withdrawal'` i `state='pending'` nie oznacza wykonanej wypłaty ani należnej prowizji.
- `wallet_preview_terms` przechowuje zamrożone warunki symulowanej wypłaty: brutto, prowizję 5% dla sprzedawcy albo 0% dla klienta, kwotę netto.
- `wallet_preview_resolutions` zawiera terminalne stany `completed_test` i `cancelled_test`. To nadal **test**, nie bankowe potwierdzenie rozliczenia.
- `payment_simulations` i `payment_simulation_events` również nie potwierdzają rzeczywistych płatności.
- `wallet_ads` i `wallet_ad_impressions` służą do emisji reklam; wyświetlenie reklamy nie jest dowodem uiszczenia opłaty reklamowej.
- `commission_drafts` to szkice prowizji od zamówień, a nie opłaty za wypłaty.

## Wniosek
**Nie ma podstaw, aby traktować którekolwiek z powyższych danych jako autorytatywny rejestr produkcyjnych, zapłaconych opłat platformy.** Nie należy automatycznie wystawiać na ich podstawie faktur.

## Bezpieczna kolejność
1. Dla testów można przygotować osobny, wyraźnie oznaczony adapter `completed_test` → `seller_withdrawal_fee`, tylko do raportów symulacyjnych, z niezmiennym `source_id`; nie mieszać z raportami produkcyjnymi.
2. Produkcyjny rejestr opłat musi opierać się na potwierdzonych zdarzeniach operatora płatności i księgowania, z idempotencją oraz osobnymi korektami.
3. Dopiero po wdrożeniu rejestru źródłowego i weryfikacji podatkowej można projektować generowanie rzeczywistych dokumentów.

Nie zmieniać zatwierdzonych plików UI, nie uruchamiać PayU ani KSeF.
