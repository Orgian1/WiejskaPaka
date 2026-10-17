# WiejskaPaka — stabilizacja, duży pakiet 02

## Potwierdzone zmiany

1. Naprawiono kontrolę dostępu do adresu dostawy w `GET /orders/{id}/location`: przypisany dostawca może zobaczyć adres niezbędny do realizacji dostawy. Nieprzypisany dostawca oraz osoby trzecie otrzymują HTTP 403.
2. Zwracany obiekt adresu zawiera wyłącznie informacje potrzebne do realizacji: typ realizacji, identyfikator punktu odbioru lub adres dostawy. Nie zawiera numeru telefonu ani adresu e-mail.
3. Dodano 6 testów regresyjnych: autoryzacja adresu, pełny przepływ dostawy i jednorazowość PIN, brak uwierzytelnienia, blokada PIN po 5 próbach, izolacja kupujących, zakaz potwierdzenia przed wysyłką.
4. Uruchomiono cały lokalny zestaw testów: **1202 passed, 1 skipped**.

## Środowisko i ograniczenia

- W tym środowisku nie znaleziono binariów `postgres`, `pg_ctl`, `psql`; nie wykonano testu migracji na rzeczywistej bazie PostgreSQL.
- Nie przeprowadzono automatycznych testów przeglądarkowych na fizycznych telefonach.
- Nie przeprowadzono niezależnego audytu bezpieczeństwa ani weryfikacji prawnej.
- Płatności, wypłaty i fakturowanie produkcyjne nadal NIE są uruchomione.
- Strona publiczna wiejskapaka.pl nie została zmieniona.

## Ważna uwaga wdrożeniowa

Zwracanie adresu dostawy dostawcy jest niezbędne operacyjnie, ale przed produkcją należy wdrożyć politykę ograniczenia dostępu po zakończeniu zlecenia, retencję danych i audyt dostępu. Obecnie przypisany dostawca ma dostęp także po zamknięciu zamówienia — nie jest to gotowe do produkcji.

## Następne blokery uruchomienia

- Testowa instancja PostgreSQL i rzeczywisty test migracji + porównanie rekordów.
- Testy przeglądarkowe i mobilne.
- Audyt bezpieczeństwa, w tym ograniczenie retencji danych adresowych.
- Weryfikacja dokumentów prawnych i procesów konsumenckich.
- Integracja operatora płatności dopiero po zakończeniu aplikacji i testów.
