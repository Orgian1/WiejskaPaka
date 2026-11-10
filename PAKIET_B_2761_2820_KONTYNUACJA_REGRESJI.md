# B/2761–B/2820 — kontynuacja pełnej regresji

- Uruchomiono cztery izolowane grupy testów na SQLite; zapisano częściowe raporty.
- Poprawiono dwa przestarzałe moduły testowe: kolejność płatność testowa → wysyłka w `test_package_b51_b55.py` oraz kontrolę resetowania sesji w `test_web_farmer_profile_session.py`.
- Weryfikacja napraw: `python -m pytest -q tests/test_package_b51_b55.py tests/test_web_farmer_profile_session.py`: 8 zaliczonych.
- Regresja całego projektu nadal nieukończona. Raporty grup z wcześniejszymi błędami są historyczne i wymagają ponowienia po zmianie testów.
- Brak zmian produkcyjnych płatności, hostingu, domeny i konfiguracji Neon.
