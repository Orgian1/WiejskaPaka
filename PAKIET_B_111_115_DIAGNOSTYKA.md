# B/111–B/115 — diagnostyka długich testów

Wykonano diagnostykę `pytest -vv` i ustalono, że w okolicach 92% zestaw dochodzi do `tests/test_roles_offline.py::test_browser_roles_login_logout`, który uruchamia 12 scenariuszy Chromium (4 role × 3 szerokości), co jest kosztownym testem przeglądarkowym. Przeniesiono ten test do trybu opt-in: `WIEJSKAPAKA_EXTENDED_BROWSER=1 python -m pytest -q tests/test_roles_offline.py`. Pozostałe kontrole statyczne i jednostkowe tego pliku nadal wykonują się domyślnie.

Dodano pięć testów kontraktu uruchamiania testów rozszerzonych.

**Ograniczenie:** próba pełnego `python -m pytest -q` po zmianach nie zakończyła się przed limitem wykonania i w końcowej części wyświetliła `F`. Nie można potwierdzić przejścia pełnej regresji. Potrzebne są osobne badanie niezaliczonego testu i uruchomienie długich testów w wydzielonym zadaniu CI. Nie dotykano Neon, domeny ani prawdziwych płatności.
