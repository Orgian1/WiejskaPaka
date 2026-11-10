# WiejskaPaka — pakiet B/3241–B/3300

## Zmiany
- Wynik opóźnionego żądania checkout nie wyświetla PIN-u ani danych przesyłki po wylogowaniu lub przełączeniu konta.
- Odpowiedź checkout jest przypisana do konkretnej próby i epoki sesji; stara odpowiedź nie usuwa blokady innej próby.
- Zmiana konta usuwa z widoku poprzedni wynik zakupów.
- Wycena jest związana z wybranym trybem dostawy; spóźniona wycena z poprzedniego trybu nie nadpisuje aktualnej.
- Dostosowano wcześniejsze testy kontraktowe do nowych zabezpieczeń oraz dodano dwa nowe testy.

## Testy
`python -m pytest -q tests/test_b1741_checkout_ui_contract.py tests/test_b1861_quote_ui_contract.py tests/test_b3181_pending_checkout_cart_guard.py tests/test_b3241_checkout_session_races.py`
`node --check web/app.js`
`python -m compileall -q backend`

## Ograniczenia
- Weryfikacja wybranych testów kontraktowych, nie pełna regresja 200 modułów.
- Po odświeżeniu strony identyfikator rozpoczętego zakupu nie jest zachowywany.
- Nie wykonano testów PostgreSQL ani testów na fizycznym telefonie.
- Nie podłączono prawdziwych płatności, hostingu ani domeny; nie zmieniono Neon.
