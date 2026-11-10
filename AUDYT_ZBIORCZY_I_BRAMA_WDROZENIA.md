# WiejskaPaka — audyt zbiorczy i przejście do następnego etapu

## Zakres wykonany
- Przejrzano kod inicjalizacji bazy, tworzenia i anulowania zamówień oraz adapter PostgreSQL.
- Uruchomiono pełny zestaw testów lokalnych na **nowej, izolowanej bazie SQLite**: **2371 passed, 4 skipped, 16 subtests passed**.
- Dodano moduł `backend/release_readiness.py` i skrypt `python -m scripts.release_gate`, który **odmawia oznaczenia projektu jako gotowego do produkcji**, dopóki wszystkie osiem obszarów nie uzyskają pozytywnych, udokumentowanych wyników.
- Dodano trzy testy bramy wdrożeniowej, w tym kontrolę każdego wymogu osobno.

## Wyniki przeglądu i zagrożenia wymagające zamknięcia
1. **RLS nie jest wdrożony**; współdzielone konto PostgreSQL ma szerokie uprawnienia. Sam kontekst transakcyjny użytkownika nie stanowi niezależnej granicy bezpieczeństwa wobec przejętego konta DB.
2. **Brak uruchomionych testów integracyjnych Neon/PostgreSQL**; zgodność SQL i współbieżność wymagają potwierdzenia na PostgreSQL.
3. **Płatności, zwroty i wypłaty są symulowane**. Nie wolno uruchamiać prawdziwych obciążeń na tej podstawie.
4. **Tworzenie zamówień** ma blokadę wiersza produktu na PostgreSQL i warunkowe zmniejszenie stanu magazynowego; wymaga testów współbieżności na rzeczywistej bazie.
5. **Anulowanie zamówień** dopuszcza tylko status `oczekuje_na_platnosc_testowa` i przywraca stan produktu w transakcji; konieczne są testy współbieżnego anulowania i płatności na PostgreSQL.
6. **Endpointy i dane osobowe** wymagają kompletnego ręcznego przeglądu autoryzacji, retencji i minimalizacji danych. Zielony zestaw testów jednostkowych nie jest certyfikacją bezpieczeństwa.
7. **Przepisy**: przed wdrożeniem konieczna weryfikacja obowiązków podatkowych, DAC7, praw konsumenta, regulaminu i RODO przez właściwych specjalistów.
8. **Operacje produkcyjne**: brak potwierdzonych kopii zapasowych, odzyskiwania, monitoringu, konfiguracji sekretów i procedury incydentów.

## Następny etap
Uruchomić odizolowane testy PostgreSQL (bez danych klientów), naprawić ujawnione niezgodności, przeprowadzić testy współbieżności i przegląd polityk dostępu; dopiero potem podłączać operatora płatności i infrastrukturę produkcyjną.

## Bezpieczne uruchomienie bramy
`python -m scripts.release_gate` zwraca kod 2, dopóki brakuje wymaganych dowodów. Nie należy zmieniać flag ręcznie tylko po to, aby uzyskać pozytywny wynik.

Nie modyfikowano bazy Neon ani publicznej strony wiejskapaka.pl.
