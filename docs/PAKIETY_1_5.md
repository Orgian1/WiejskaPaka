# WiejskaPaka — plan 5 dużych pakietów

1. **Finanse i kontrola płatności (ten pakiet)**: bezpieczny, tylko odczytowy moduł uzgadniania testowych zapisów płatności z ręcznie podanymi danymi przypominającymi raport operatora. Endpoint `POST /test/admin/finance/reconcile` wymaga administratora i `WP_ENABLE_TEST_PAYMENTS=1`. Przykładowe JSON: `[{"order_id":1,"amount_grosze":10000,"status":"paid"}]`. Statusy: `paid`, `refunded`, `pending`. Limit 500 pozycji, duplikaty są odrzucane, brak dostępu do prawdziwego PSP.
2. **Panele i proces zamówienia**: spójne ekrany klienta, rolnika, dostawcy, administratora i proces PIN.
3. **Rejestracja, bezpieczeństwo i zgodność**: dane rolników, DAC7, uprawnienia, RODO, regulaminy do przeglądu prawniczego.
4. **Baza danych i testy przekrojowe**: prawdziwe testy PostgreSQL, migracje, transakcje i testy zamówienie–dostawa–rozliczenie.
5. **Testy końcowe i przygotowanie wdrożenia**: UX mobile, procedury wdrożeniowe, integracje zewnętrzne jako adaptery testowe; produkcyjne płatności dopiero po osobnym uruchomieniu.

**Zakres tego wydania:** pierwszy pakiet jest rozpoczęty i zawiera konkretny moduł uzgodnień. Nie oznacza to, że cała część finansowa jest ukończona lub gotowa produkcyjnie. Raporty finansowe nadal są symulacją; wymagają potwierdzenia księgowego. Publiczna strona bez zmian.
