# Demo wszystkich ról i czytelne rozliczenia — 18.10.2026

Uruchomienie: `python scripts/run_phone_demo.py --sample-data`.
Instrukcja i scenariusz ręcznego odbioru: `DEMO_Z_DANYMI.md`.

## Zachowanie aplikacji

- Nowy prywatny katalog SQLite zawiera cztery fikcyjne konta (klient, rolnik,
  dostawca i administrator), dwie oferty, punkt i dwie wieloproduktowe przesyłki.
  Jedna jest gotowa do odbioru, druga w drodze. Dostawa kosztuje raz 501 groszy.
- Konta mają oddzielne losowe hasła wypisywane tylko do lokalnego terminala.
  Nie zapisuje się pliku z hasłami. Sesje przygotowawcze są usuwane. Publiczna
  rejestracja nadal nie nadaje uprawnień administratora.
- Przygotowanie działa tylko w nowym procesie i nieistniejącym katalogu,
  odrzuca istniejący cel i odziedziczone połączenia do baz zewnętrznych.
  Nie otwiera starej bazy ani jej klucza. Błąd usuwa własny nowy katalog.
- Rolnik widzi czytelne kwoty, liczbę pozycji zamówień, prowizje i termin
  podglądu tygodniowego. Formatowanie groszy używa BigInt po sprawdzeniu
  bezpiecznej liczby całkowitej; nie przelicza zasad podziału z backendu.
  Nieprawidłowe kwoty i daty nie są wyświetlane jako poprawne rozliczenie.
- Po odbiorze opłaconej testowo pozycji rolnik może jawnie przekazać ją do
  rozliczenia testowego. Przycisk używa istniejącego chronionego API i sprawdza
  aktualny stan przed ponowieniem. Identyfikator zdarzenia pozostaje ten sam
  przy ponowieniu w tym widoku. Operacja nie wykonuje przelewu.
- Wersja decyzji o profilu rośnie co najmniej o mikrosekundę względem
  poprzedniej. Zatrzymany lub cofnięty zegar nie odtwarza starej wersji.
  PostgreSQL blokuje profil przed odczytem daty; HTTP SQLite używa istniejącej
  transakcji BEGIN IMMEDIATE. Test z zatrzymanym zegarem odtwarzał błąd starego
  kodu i teraz odrzuca stary widok po powrocie statusu do poprzedniej wartości.

## Potwierdzone kontrole

Kod badany: `da3ca749b069a7fe23dfb0e3323776bc46e35a62`.
Przebieg: https://github.com/Orgian1/WiejskaPaka/actions/runs/39105133009

| Kontrola | Wynik |
| --- | --- |
| Pełna regresja Linux | 302/302 moduły; 3727 zaliczonych, 0 błędów, 35 pominiętych; razem 3762 przypadki |
| Zestaw celowany | 81 zaliczonych, 0 błędów, 10 pominiętych (lokalnie brak Chromium) |
| Natywna szybka kontrola Windows | 80/80, bez pominięć |
| Natywny PostgreSQL z ograniczoną rolą i rzeczywistym HTTP | 17/17, bez pominięć |
| Natywne Chromium | 23/23, bez pominięć; ponadto HTTP przy pięciu szerokościach okna |
| Pełna regresja Windows | Uruchomiona po zaliczeniu szybkiej kontroli; w chwili zapisu jeszcze trwa |

Chromium sprawdza osiem widoków wszystkich ról przy 320/1280 px na rzeczywistym
serwerze i danych demo oraz dwa pełne scenariusze: odzyskanie PIN-ów, odbiór
u rolnika, odbiór od dostawcy, licznik dwóch zakończonych transakcji,
przekazanie pozycji do testowego rozliczenia z dodatnią kwotą w podsumowaniu
oraz decyzję administratora. Testy jawnie czekają na odpowiedzi odczytu,
logowania i odświeżonego raportu; sprawdzają treść i stan interfejsu.

Szybki Windows obejmuje nowe demo, przegląd profilu, interfejs rozliczeń,
kopie/odtworzenie i reset hasła. Jego wynik jest oddzielny od pełnej regresji.
Pełne zadanie powtarza te przypadki i uruchamia wszystkie moduły. Nie sumować
podzbiorów i ponownych wykonań jako nowych testów. Wszystkie etapy nadal
wymagają braku błędów; szybkie bramy odrzucają także pominięcia.

Odciski źródeł, testów, zależności i workflow porównano z lokalnym kodem.
Archiwa artefaktów zweryfikowano z digestami GitHub. Oczyszczone dowody:
`audits/sample_demo_linux_2026-10-18.json`,
`audits/sample_demo_targeted_2026-10-18.json`,
`audits/sample_demo_ci_2026-10-18/`.
Nie publikowano kont, haseł, baz, kluczy, PIN-ów ani surowych logów.

## Zakres i ograniczenia

To jednorazowe demo na 127.0.0.1. Zamknięcie usuwa fikcyjne dane; po awarii
systemu sprzątanie nie jest gwarantowane. Kod jest niezależnie zapisany
w GitHubie. Brak rzeczywistych płatności, wypłat, hostingu, domeny i Neon.
Windows ACL nie są potwierdzone. Odbiór i rozliczenie testowe nie stanowią
produkcyjnej weryfikacji tożsamości ani uruchomienia automatu wypłat.
Gałąź `main` pozostała bez zmian.

Wcześniejszy przebieg kolejki miał jeden niezaliczony test modułu profilu;
odtworzono następnie problem powtarzanej daty wersji. Podczas tej paczki
szybka kontrola wykryła także otwarte połączenie SQLite w teście launchera;
przed sprzątaniem jest teraz jawnie zamykane. Nie zmniejszono liczby asercji
lub wymagań bram. Powyższa tabela dotyczy końcowego commitu i zweryfikowanych
artefaktów, a nie wcześniejszych nieudanych przebiegów.
