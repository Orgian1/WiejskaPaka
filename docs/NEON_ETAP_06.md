# Neon — etap 06: weryfikacja sesji

Dodano `backend/neon_session_bridge.py` i testy jednostkowe.

- Identyfikator użytkownika pochodzi wyłącznie z sesji zweryfikowanej w bazie.
- Token Bearer jest haszowany SHA-256 przed odpytywaniem tabeli `sessions`.
- Sprawdzana jest data wygaśnięcia sesji (ze strefą czasową).
- Kontekst `wiejskapaka.actor_id` ustawiany jest lokalnie w transakcji i czyszczony po operacji.

## Granice etapu

Moduł nie jest jeszcze podłączony do endpointów FastAPI. Nie uruchomiono rzeczywistego połączenia z Neon, nie włączono RLS i nie wprowadzono żadnych zmian w bazie użytkownika. Wymagana jest kontrola zgodności formatu sesji między backendem SQLite a PostgreSQL oraz pełna integracja po stronie API. Nie wolno przekazywać `actor_id` bezpośrednio z żądania klienta. Nie udostępniać danych po samym ustawieniu kontekstu, zanim nie zostaną wdrożone reguły RLS.
