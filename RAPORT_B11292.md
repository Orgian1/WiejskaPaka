# WiejskaPaka B/11292 — kontrola transportu PostgreSQL

- Dodano walidację zdalnego DSN PostgreSQL: `sslmode=verify-full` jest obowiązkowe dla hostów innych niż loopback/localhost.
- Odrzucane są sprzeczne parametry `sslmode`, błędne porty i fragmenty adresu URL.
- Lokalne bazy loopback mogą działać bez TLS, wyłącznie w prywatnym środowisku testowym.
- Dodano 10 testów w `tests/test_b11292_postgres_transport.py`.
- Wspólny wynik: **47 passed, 0 failed**.
- Ograniczenie: bez rzeczywistego PostgreSQL i bez testów certyfikatów TLS. Kontrola dotyczy ścieżki `backend.test_server_launcher`, nie wszystkich możliwych metod uruchomienia API.
- Prawdziwe płatności pozostają wyłączone.
