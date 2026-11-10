# Pakiet B/24 — audyt mobilnego HTML bez przeglądarki

Dodano `scripts/audit_mobile_markup.py`: niezależną od sieci i bazy danych kontrolę struktury HTML, poprawności odnośników nawigacji, unikalności identyfikatorów, domyślnego ukrycia prywatnych paneli, języka, viewport oraz istnienia lokalnych zasobów CSS/JS. Cztery testy regresyjne sprawdzają poprawny projekt i wykrywanie trzech rodzajów błędów.

Uruchomienie: `python -m scripts.audit_mobile_markup`.

To **audyt statyczny**, nie test rzeczywistego renderowania, uprawnień serwera ani dostępności WCAG. Próba `python -m scripts.check_mobile_browser` w tym środowisku nadal kończy się `ERR_BLOCKED_BY_ADMINISTRATOR`; nie uznajemy testu Chromium za zaliczony. Rzeczywiste PostgreSQL, RLS i telefon pozostają do sprawdzenia. Nie zmieniano Neon, strony publicznej ani płatności.
