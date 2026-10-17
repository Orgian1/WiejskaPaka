# Etap 17 — analiza zapytań dynamicznych

Rozszerzono `backend/neon_sql_inventory.py` o zachowawcze rozpoznawanie widocznych fragmentów SQL w f-stringach, konkatenacjach i formatowaniu `%`. Wcześniej takie zapytania raportowano bez wskazania tabel, nawet gdy nazwa tabeli była dosłownie obecna w kodzie. Teraz raport zachowuje wykryte nazwy tabel i jednocześnie oznacza całość jako DYNAMIC, wymagającą ręcznej weryfikacji.

Ograniczenia: nie wykonano testu na Neon; nie przeprowadzono audytu wszystkich ścieżek autoryzacji. Statyczna analiza nie dowodzi bezpieczeństwa zapytań. Nie włączono RLS, nie zmieniono bazy ani strony publicznej, nie uruchomiono prawdziwych płatności.

Testy lokalne: 1278 passed, 3 skipped, 16 subtests passed.
