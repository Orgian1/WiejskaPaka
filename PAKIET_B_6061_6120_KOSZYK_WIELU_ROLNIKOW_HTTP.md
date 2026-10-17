# WiejskaPaka — B/6061–B/6120: koszyk różnych produktów od dwóch rolników przez rzeczywiste HTTP

Nowy skrypt `scripts/check_http_multi_seller_cart.py` uruchamia Uvicorn/FastAPI na lokalnym TCP i wykonuje 30 kontroli z odizolowaną SQLite. Nie łączy się z Neon ani z zewnętrznymi usługami płatniczymi.

Przykładowy koszyk:
- Rolnik A: 2 × jabłka po 349 gr i 3 × gruszki po 257 gr; dostawa tylko raz, **699 gr** (maksimum z 501 i 699 gr). Razem **2168 gr**.
- Rolnik B: 1 × miód po 999 gr; dostawa **801 gr**. Razem **1800 gr**.
- Łącznie: produkty **2468 gr**, dwie odrębne dostawy **1500 gr**, koszyk **3968 gr**.

Weryfikacja: wycena wielu sprzedawców; blokada checkoutu łącznego bez wskazania sprzedawcy; osobny checkout rolnika A i B; zachowanie pozycji B po zakupie A; idempotentne ponowienie zamówienia A; blokada ponownego użycia klucza z inną treścią; odmowa ujawnienia obcej przesyłki (404 — celowo maskuje jej istnienie); zgodność sumy zamówień z wyceną.

Wyniki w `HTTP_MULTI_SELLER_REPORT_B6061.json` i `TESTY_B_6061_6120.txt`. Kontrole składni `node --check web/app.js` i `python -m compileall -q backend scripts` wykonane.

Ograniczenia: nadal brak rzeczywistej bazy PostgreSQL, przeglądarki Chromium przez HTTP, testów na fizycznym telefonie oraz audytu produkcyjnego. Checkout jest wykonywany osobno dla każdego sprzedawcy, nie jako jedna transakcja wielu sprzedawców. Płatności pozostają wyłącznie testowe.
