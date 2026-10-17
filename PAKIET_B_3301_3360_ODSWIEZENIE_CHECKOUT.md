# B/3301–B/3360 — zabezpieczenie koszyka po odświeżeniu

- W obrębie karty przeglądarki zapisujemy wyłącznie znacznik nierozstrzygniętej operacji zakupu w `sessionStorage`, przypisany do ID zalogowanego użytkownika.
- Nie zapisujemy w `sessionStorage` tokenu, PIN-u, adresu dostawy ani danych zamówienia.
- Po odświeżeniu i ponownym zalogowaniu na to samo konto interfejs blokuje ponowny zakup i modyfikacje koszyka, dopóki klient nie sprawdzi historii i świadomie nie odblokuje koszyka.
- Po potwierdzonym sukcesie znacznik jest usuwany. W razie nieznanej odpowiedzi sieciowej pozostaje.
- Ponowienie żądania z tym samym kluczem działa nadal w bieżącej sesji strony; po odświeżeniu wymagana jest kontrola historii.
- Testy: `python -m pytest -q tests/test_b1741_checkout_ui_contract.py tests/test_b3301_refresh_checkout_guard.py` (3 zaliczone); `node --check web/app.js` i `python -m compileall -q backend` (bez błędów).
- Nie przeprowadzono pełnej regresji ani testów przeglądarkowych. Bez zmian konfiguracji Neon, hostingu, domeny i płatności produkcyjnych.
