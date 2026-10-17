# Pakiety B/33–B/35 — awarie logowania w Chromium

## B/33: odmowa logowania
Test w prawdziwym silniku Chromium, z mockowanym API, weryfikuje komunikat HTTP 401 i brak prywatnych paneli.

## B/34: utrata ważności sesji
Po przyjęciu tokenu testowego, ale odrzuceniu `/auth/me`, aplikacja wraca do stanu niezalogowanego i nie pokazuje paneli.

## B/35: brak połączenia
Symulowana awaria sieci przy logowaniu wyświetla błąd, bez odsłonięcia danych i bez wyjątków JavaScript.

Uruchom: `python -m scripts.check_auth_failures_offline` (wymaga Playwright i Chromium).

Wyniki lokalne: trzy scenariusze Chromium zaliczone; `python -m pytest -q`: 2494 passed, 6 skipped, 16 subtests passed.

**Granice testów:** mockowane API, bez serwera, PostgreSQL i rzeczywistych płatności. To nie jest audyt produkcyjny. Nie wykonywano zmian na Neon ani wiejskapaka.pl.
