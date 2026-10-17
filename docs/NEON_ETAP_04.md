# WiejskaPaka — Neon, etap 04

Dodano `backend/neon_permissions.py`: diagnostykę **tylko do odczytu** uprawnień roli aplikacji oraz ekspozycji sześciu tabel zawierających wrażliwe dane. Raport nie pobiera rekordów klientów ani nie drukuje hasła. Moduł nie zmienia schematu i nie włącza RLS bez reguł autoryzacji.

## Uruchomienie po stronie backendu

`python -m backend.neon_permissions` po ustawieniu prywatnej zmiennej `DATABASE_URL` (TLS). Do czasu wdrożenia weryfikowanej tożsamości, polityk RLS, testów wieloużytkownikowych i audytu uprawnień **nie uruchamiać aplikacji publicznie**.

## Znany stan z testów ręcznych użytkownika

RLS dla `users`, `orders`, `order_locations`, `delivery_assignments`, `seller_compliance` = false; konto `wiejskapaka_app` ma SELECT do tych tabel. To **nie jest** jeszcze izolacja danych użytkowników. Hasła i dane połączenia nie powinny być wysyłane do rozmowy. Płatności pozostają testowe. Publiczna strona bez zmian.
