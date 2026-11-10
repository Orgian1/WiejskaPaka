# WiejskaPaka B/11311 — brama pustej bazy testowej

- Dodano `database/validate_migration_target.py`: preflight wyłącznie odczytowy, sprawdza ustawienia środowiska testowego, faktyczną nazwę bazy, nieuprzywilejowaną rolę PostgreSQL i brak obiektów w publicznym schemacie.
- Plan `database/test_schema_sequential.py` uruchamia bramę **przed** pierwszym plikiem SQL; plan nie wykonuje migracji automatycznie.
- Dodano testy dla niewłaściwej bazy, uprzywilejowanej roli i niepustego schematu.
- Testy: `python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b1131*.py`: **175 passed**.

## Ograniczenia
- Brak uruchomionego serwera PostgreSQL i testu prawdziwego wykonania migracji.
- Istnieje okno między kontrolą pustej bazy a wykonaniem SQL; uruchamiać wyłącznie na odizolowanej, nowej bazie testowej, bez innych użytkowników.
- Migracje nie są globalnie atomowe; przy błędzie odtworzyć bazę testową od zera.
- Brak testów obciążeniowych i prawdziwych płatności. Docelowy limit: 30 000 opłaconych zamówień/miesiąc.
