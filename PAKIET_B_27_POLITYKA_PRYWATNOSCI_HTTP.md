# Pakiet B/27 — polityka prywatności odpowiedzi HTTP

- `Referrer-Policy: no-referrer` ogranicza przekazywanie adresu odwiedzanej strony do innych witryn.
- `Permissions-Policy` wyłącza nieużywane funkcje przeglądarki: kamerę, mikrofon, lokalizację i Payment Request API.
- CSP ogranicza połączenia sieciowe (`connect-src`) i wysyłanie formularzy (`form-action`) do własnego originu.
- Nowe testy sprawdzają nagłówki na odpowiedziach publicznych, prywatnych i 404.

To dodatkowa warstwa ochrony; nie zastępuje autoryzacji, RLS, testów przeglądarkowych ani testów na telefonie.
Neon, domena i prawdziwe płatności pozostają bez zmian.
