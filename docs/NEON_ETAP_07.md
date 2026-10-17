# Neon etap 07 — izolacja odczytu zamówień i adresów

Dodano `backend/neon_order_access.py` oraz testy.

- Zapytania klienta i rolnika filtrują zamówienia po identyfikatorze aktora przekazanym przez **zaufaną warstwę serwera**.
- Zapytanie adresowe dostawcy wymaga przypisania, typu dostawy, aktywnego statusu, niewykorzystanego PIN i braku potwierdzenia.
- Zapytania parametryzowane; nie pobierają numerów telefonów.

**Ograniczenia:** Funkcje nie są jeszcze podłączone do FastAPI ani przetestowane na rzeczywistym Neon. RLS jest nadal wyłączony, a rola aplikacji nadal ma szerokie prawa SELECT. Ochrona wymaga wywoływania funkcji wyłącznie po `verified_actor` i późniejszego wdrożenia reguł RLS. Status `w_dostawie` należy uzgodnić z faktyczną maszyną stanów aplikacji przed użyciem. Nie uruchamiać produkcyjnie. Żadne zmiany nie zostały wykonane na Neon ani na stronie publicznej.
