# WiejskaPaka — wersja testowa B/10921–B/11280

Marketplace rolnik–klient. Hasło: **Z pola pod Twój dom.**

Bieżący pakiet zarządzania sesjami opisuje `docs/ZARZADZANIE_SESJAMI.md`.
Dowody aktualnego wydania: `docs/RAPORT_SESJE_2026-10-16.md` oraz
`audit_sessions_final_*.json`. Poprzednie pakiety bezpieczeństwa opisują
`docs/ODZYSKIWANIE_PIN.md` i `docs/BEZPIECZENSTWO_KONTA.md`.
Aktualne poprawki są rozwijane na gałęzi GitHub `wiejskapaka-import`.
Bieżący raport: `docs/RAPORT_ZWROTOW_2026-10-17.md`.
Poprzednia paczka powiązań przesyłek: `docs/RAPORT_PRZESYLEK_2026-10-17.md`.
Poprzednia paczka integralności PIN-u: `docs/RAPORT_HASHY_2026-10-17.md`.
Poprzednia paczka transakcyjna: `docs/RAPORT_TRANSAKCJI_2026-10-17.md`.
Poprzednia kontynuacja: `docs/RAPORT_KONTYNUACJI_2026-10-17.md`.
Poprzednia paczka: `docs/RAPORT_NAPRAW_2026-10-17.md`.
Starsze raporty i nazwy pakietów w archiwum są historią projektu, a nie dowodem
zaliczenia testów obecnego kodu. Numeracja B nie jest liczbą wykonanych testów.

**To środowisko demonstracyjne. Nie jest gotowe do rzeczywistych płatności.**
Nie podłączono Neon, domeny, hostingu ani produkcyjnego operatora płatności.
Tryb produkcyjny blokuje `backend/deployment_guard.py`.

## Start lokalny

Wymagane Python 3.12 oraz, do części testów interfejsu, Node.js.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/python scripts/run_phone_demo.py
```

Otwórz adres pokazany przez skrypt, domyślnie `http://127.0.0.1:8765`.
Podgląd tworzy jednorazową bazę SQLite i usuwa ją po zamknięciu. Nie używaj
prawdziwych danych osobowych. Numery telefonów nie są zbierane w formularzach.
W Windows zamiast `.venv/bin/python` użyj `.venv\Scripts\python.exe`.

## Testy

```bash
.venv/bin/python scripts/run_tests_per_file.py --report moj_raport_regresji.json
.venv/bin/python scripts/run_http_acceptance_suite.py --output moj_raport_http.json
.venv/bin/python scripts/soak_local_http.py --seconds 60 --report moj_raport_stabilnosci.json
```

Pełna regresja izoluje każdy moduł w nowym procesie i bazie. W jednym procesie
stare testy modyfikują stan globalny, dlatego zwykłe `pytest` dla całego katalogu
nie jest miarodajną bramą wydania. Wynik rozróżnia testy zaliczone i pominięte.
Zmiana kodu podczas regresji unieważnia końcowy raport.

Natywne testy PostgreSQL opisuje `docs/POSTGRESQL_TESTY_LOKALNE.md`.
Dostarczony Compose nie uruchamia GitHub Actions ani usług płatnych.
Do rzeczywistych testów przeglądarkowych potrzebne są lokalne Chromium/Chrome
i Playwright. Ich obecność nie oznacza automatycznie zaliczenia testu.

## Wyszukiwanie lokalne

Sekcja **Blisko mnie** wyszukuje dostępne produkty i aktywne punkty w promieniu
100 m, 500 m, 1 km lub 5 km, z filtrem ceny. Wpisz współrzędne albo samodzielnie
uruchom lokalizację urządzenia. Pozycja klienta nie jest zapisywana w bazie ani
pamięci przeglądarki. Rolnik ustawia współrzędne i aktywność punktu w swoim panelu.
Opis migracji, ochrony istniejących odbiorów i granic pomiaru:
`docs/WYSZUKIWANIE_LOKALNE.md`.

## Ochrona odpowiedzi i PIN-u

Odpowiedzi zakupowe w bazie są szyfrowane. PIN z ponowienia jest dostępny przez
24 godziny; po tym czasie zakup nadal pozostaje ten sam, bez ponownego naliczenia.
Klucza nie ma w archiwum. Nowe lokalne demo tworzy własny klucz. PostgreSQL
wymaga jawnego pliku klucza. Przed aktualizacją własnej bazy przeczytaj opis
migracji, kopii zapasowych i ograniczeń: `docs/SZYFROWANIE_ODPOWIEDZI_ZAKUPU.md`.

## Zmiana hasła

Sekcja Bezpieczeństwo konta zmienia hasło po ponownym podaniu obecnego hasła
i cofa wszystkie sesje konta. Trzeba ponownie się zalogować. Limit: 5 prób
w 15 minut; hasła i token nie są zapisywane w pamięci trwałej przeglądarki.
Migracja i zakres: `docs/BEZPIECZENSTWO_KONTA.md`.

## Odzyskanie PIN-u po odświeżeniu strony

W historii zamówień i panelu przesyłek klienta można odzyskać ten sam testowy
PIN po ponownym podaniu hasła. Limit wynosi 5 prób na konto w 15 minut; kod
zniknie z ekranu po 30 sekundach. Operacja nie tworzy zamówienia, nie resetuje
PIN-u i nie przedłuża rezerwacji ani 24-godzinnej retencji. Starsze zakupy bez
cache nie mają tej możliwości. Migracja PostgreSQL i ograniczenia:
`docs/ODZYSKIWANIE_PIN.md`.

## Pierwotne warunki zakupu

Karty nowych zamówień i przesyłek klienta oraz rolnika umożliwiają odczyt
pierwotnej nazwy produktu, ceny i punktu oraz pobranie JSON. Późniejsze zmiany
oferty nie przepisują historii. Stare zakupy bez zapisu pokazują brak danych.
Opis dostępu, migracji, testów i ograniczeń: `docs/HISTORIA_ZAKUPOW.md`.

## Rezerwacje magazynu

Nowe zakupy rezerwują zapas przez 30 minut. Automat działa przy starcie serwera
i co 30 sekund. Konto może mieć maksymalnie 10 nieopłaconych zakupów. Opłacone
i częściowo opłacone przesyłki są chronione przed automatycznym zwolnieniem.
Szczegóły aktualizacji bazy, zachowania i ograniczeń: `docs/REZERWACJE_MAGAZYNU.md`.

## Reguły finansowe i odbiór

- Kwoty API, bazy i rozliczeń są całkowitymi groszami. Pola wejściowe nie
  przyjmują wartości float, bool ani kwot jako tekstu.
- Jedna przesyłka od jednego sprzedawcy ma jedną opłatę za dostawę. Obecna
  taryfa testowa wybiera największą stawkę dostawy spośród jej produktów.
- Odbiór w punkcie nie nalicza dostawy na adres. Dostawa ma stawkę sprzedawcy.
- PIN potwierdza odbiór; pięć błędnych prób blokuje użycie kodu. Nie wolno
  osobno potwierdzać pozycji należącej do przesyłki wieloproduktowej.
- Niedostarczenie z winy dostawcy oznacza w symulacji zwrot 100% wpłaty,
  razem z dostawą. Nie wykonujemy żadnego przelewu.
- Prowizja jest zaokrąglana całkowitoliczbowo half-up na poziomie zamówienia;
  opłata za dostawę jest przypisana do jednej pozycji przesyłki.
- PIN i kontrola towaru nie ograniczają ustawowych praw konsumenta.

Nie deklarujemy ukończenia wszystkich 360 numerowanych pozycji B/10921–B/11280
ani procentu ukończenia bez sprawdzonej listy wymagań. Pozostałe bramy i braki
funkcjonalne są jawnie opisane w raporcie.
