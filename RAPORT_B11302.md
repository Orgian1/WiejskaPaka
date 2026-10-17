# WiejskaPaka — B/11302

Dodano do startowej kontroli rzeczywistego PostgreSQL sprawdzanie uprawnień roli aplikacyjnej. Serwer prywatny nie startuje, gdy rola ma SUPERUSER, BYPASSRLS, CREATEROLE lub CREATEDB albo odczyt metadanych jest niejednoznaczny. Kontrola jest tylko do odczytu i zawsze zamyka połączenie. Zaktualizowano atrapy w testach wcześniejszych etapów oraz dodano 10 scenariuszy nowej bramy.

Weryfikacja: `python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py` — 136 passed, 0 failed. Testy z atrapą PostgreSQL; nie jest to weryfikacja realnego VPS, konfiguracji RLS ani pełny audyt uprawnień.

Następnie: migracje i testy rzeczywistego PostgreSQL, izolacja danych, pomiary obciążenia. Bez płatności produkcyjnych.
