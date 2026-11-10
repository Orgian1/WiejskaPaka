# Pakiet B/14 — produkty rolnika i raport administratora

- Panel rolnika pokazuje listę własnych produktów, cenę, opłatę za dostawę i aktualny stan magazynowy pobrany z API.
- Nieprawidłowy stan magazynowy jest wyświetlany jako niedostępny, a nie jako liczba ujemna.
- Raport administratora jest prezentowany w osobnych wierszach i wyraźnie oznaczony jako testowy.
- Dane są wstawiane przez `textContent` (funkcja `node`), a nie `innerHTML`.
- Dodano dwa testy regresyjne.

## Ograniczenia

Testy kodu nie zastępują testów przeglądarkowych. PostgreSQL i RLS wymagają osobnego środowiska; płatności produkcyjne pozostają nieaktywne.
