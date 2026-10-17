# WiejskaPaka — pakiet B/17: spójność katalogu i listy zamówień

W `web/app.js` dodano liczniki kolejnych żądań katalogu i zamówień.
Odpowiedź wcześniejszego żądania nie nadpisuje widoku po nowszym odświeżeniu.
Zmiana konta lub wylogowanie unieważniają oczekujące aktualizacje obu widoków.
Dodatkowo kontrolowany jest numer epoki sesji.

Dodano trzy testy regresyjne sprawdzające obecność tych zabezpieczeń w kodzie.
Są to testy statyczne; nie zastępują testów w przeglądarce ani testów PostgreSQL.
Nie zmieniano konfiguracji Neon, RLS, domeny ani rzeczywistych płatności.
