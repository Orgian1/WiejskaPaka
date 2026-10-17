# Etap 11 — zweryfikowane odczyty PostgreSQL

- Poprawiono odczyt sesji z wierszy `dict_row` używanych przez `psycopg` w `pg_adapter.py`. Wcześniej kod oczekiwał indeksów liczbowych i nie był zgodny z rzeczywistą konfiguracją adaptera.
- Dodano trzy funkcje odczytu zamówień i adresów kuriera oparte na identyfikatorze pobranym **wyłącznie ze zweryfikowanej sesji Bearer**.
- Dodano testy pozytywne i negatywne.

## Ograniczenia i następne prace

Funkcje są pomocnicze i **nie zostały jeszcze podłączone do tras FastAPI**. Wymagają połączenia i transakcji zarządzanych przez wywołujący kod. RLS w Neon pozostaje wyłączony. Konto aplikacji ma szerokie uprawnienia odczytu, więc aplikacji nie wolno jeszcze uruchamiać publicznie.

Nie zmieniono Neon, domeny ani płatności produkcyjnych.
