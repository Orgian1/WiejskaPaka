# Pakiet 3/5 — zgodność sprzedawców (wersja testowa)

Dodano potwierdzanie wersji roboczych zasad przez rolnika, prywatny status zgodności, rejestr zdarzeń oraz ręczny przegląd administratora. Endpointy: `GET /farmers/me/compliance`, `POST /farmers/me/compliance/acknowledge`, `POST /admin/farmers/{farmer_id}/compliance/review`.

**Zastrzeżenie:** zatwierdzenie administratora nie jest weryfikacją KYC, nie zezwala na wypłaty produkcyjne. Nie gromadzimy PESEL/NIP/dat urodzenia w tej wersji; należy najpierw wdrożyć bezpieczny proces z operatorem i politykę retencji. Wersja `2026-10-draft` nie jest prawnie zatwierdzonym regulaminem. Nie kodujemy niezweryfikowanych progów DAC7. Zliczane zamówienia mają charakter wyłącznie informacyjny i nie są licznikiem transakcji DAC7.

PostgreSQL: zastosuj `database/upgrade_pack3.sql` przed uruchomieniem API. Produkcyjne testy integracyjne, przegląd RODO, regulaminy i analiza DAC7 nadal są wymagane.
