# Pakiet B/02 — wyścigi podczas logowania i wylogowania

- Żądania logowania mają licznik prób `loginAttempt`. Spóźniona odpowiedź ze starej próby nie może nadpisać nowszej sesji.
- Wylogowanie unieważnia oczekujące próby logowania, również gdy użytkownik wyloguje się zanim serwer odpowie na żądanie logowania.
- Niepowodzenie `/auth/me` po otrzymaniu tokenu powoduje usunięcie tokenu i wyczyszczenie widoków prywatnych.
- Dodano test symulujący opóźnione logowanie w Node.js bez sieci i test regresyjny zabezpieczeń.

Granice: test przeglądarkowy używa uproszczonego DOM, a nie prawdziwego telefonu. Nie wykonano testów PostgreSQL na serwerze. Nie zmieniono Neon, domeny ani płatności.
