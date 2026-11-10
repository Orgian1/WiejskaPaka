# Pakiet B/21 — blokada wielokrotnego zapisu formularzy

Dodano `singleWrite` w `web/app.js`, blokujący powtórne żądania mutujące z formularzy rejestracji, dodawania produktu, edycji profilu i dodawania punktu odbioru. Blokada jest zwalniana również po błędzie serwera. Komunikaty sukcesu oraz odświeżanie widoku po operacji nie występują, jeśli użytkownik zmienił sesję.

Nowe testy: `tests/test_web_single_write_guard.py` (test wykonania JS w Node i kontrola podłączenia formularzy).

Pełny zestaw lokalny: 2464 zaliczone, 6 pominiętych, 16 podtestów zaliczonych. Testy PostgreSQL na rzeczywistym serwerze i testy na telefonie nadal niewykonane. To zabezpieczenie UI nie zastępuje serwerowej idempotencji i autoryzacji.

Nie zmieniono Neon, wiejskapaka.pl ani płatności produkcyjnych.
