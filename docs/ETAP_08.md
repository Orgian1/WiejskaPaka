# Backend etap 8 — transakcje i współbieżność

- Zamówienia blokują wiersz produktu (`SELECT ... FOR UPDATE`) w PostgreSQL i dodatkowo wykonują warunkowe `UPDATE stock>=quantity`; zmiana ilości jest atomowa.
- Potwierdzanie PIN, anulowanie i przejście do gotowości blokują wiersz zamówienia w PostgreSQL, aby dwa żądania nie wykonały zmiany stanu równocześnie.
- Próby logowania do tego samego e-maila są serializowane w PostgreSQL przez transakcyjną blokadę advisory.
- Adapter PostgreSQL udostępnia `rowcount`, potrzebny do sprawdzenia skutku warunkowego UPDATE.
- Test SQLite z równoległymi rezerwacjami sprawdza, że ostatnia sztuka nie może zostać sprzedana dwa razy.

## Granice ukończenia

Nie wykonano testu integracyjnego z uruchomionym PostgreSQL (wymaga osobnej instancji). Nie ma jeszcze pełnego modelu zdarzeń, dostawców ani płatności produkcyjnych. Zwracanie PIN klientowi w odpowiedzi API jest wyłącznie rozwiązaniem testowym. Wdrożenie publiczne pozostaje zablokowane.
