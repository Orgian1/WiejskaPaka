# WiejskaPaka — pakiety B/30–B/32, duża paczka

## B/30 — testowanie logowania i wylogowania w Chromium
- Nowy `scripts/check_roles_offline.py` uruchamia prawdziwy silnik Chromium.
- Testuje zalogowanie i wylogowanie z czterech ról: klient, rolnik, dostawca, administrator.
- Sprawdza, czy po wylogowaniu panele i ich zawartość są ukryte/wyczyszczone.

## B/31 — responsywność paneli
- Każda rola jest sprawdzana przy szerokościach 320, 390 i 1280 px (12 kombinacji).
- Kontrola braku poziomego przewijania i błędów JavaScript.
- Kontrola widoczności paneli zgodnej z rolą.

## B/32 — poprawki wyścigów sesji
- Asynchroniczne pobieranie punktów odbioru ignoruje wynik po zmianie sesji lub usunięciu karty produktu.
- Błąd wewnętrzny `SESSION_CHANGED` nie trafia do statusu karty produktu.
- Odświeżanie produktów i zamówień po zmianie sesji przechodzi przez wspólną obsługę `act()`, która ignoruje anulowane żądania.
- Cztery nowe testy regresyjne, w tym realny Chromium (jeśli zainstalowany).

## Granice testów
- API w teście Chromium jest **mockowane**. To test interfejsu, a nie rzeczywistej autoryzacji backendu ani integracji z bazą.
- Nie uruchamiano rzeczywistych płatności, Neon/PostgreSQL ani strony produkcyjnej.
- Testy fizycznych telefonów i pełnego procesu przeglądarka ↔ serwer pozostają do wykonania.

Uruchomienie: `python -m scripts.check_roles_offline`, `python -m pytest -q`.
