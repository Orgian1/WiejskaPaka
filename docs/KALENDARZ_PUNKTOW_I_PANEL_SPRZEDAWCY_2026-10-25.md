# Kalendarz punktów i panel sprzedawcy

## Zakres

- Publiczne konto sprzedawcy (`rolnik`) służy sprzedaży: katalog zakupowy, wyszukiwanie w okolicy i koszyk są ukryte. API zakupów już wcześniej dopuszczało tylko `klient`; dodano testy rzeczywistych prób zakupu przez sprzedawcę, oczekiwane 403.
- Aktualne zamówienia sprzedawcy są na górze, nad formularzem produktu. Każde ma zwinięte szczegóły. Stany końcowe pozostają w historii panelu; dodatkowe karty przesyłek i historii sprzedawcy też są zwijane.
- Dodanie i edycja punktu mają kalendarz z wielokrotnym wyborem dat, zmianą miesiąca i zaznaczeniem wybranych dni. Daty od dzisiaj w strefie Europe/Warsaw do 365 dni naprzód, maksymalnie 90. Formularz z aktywnym kalendarzem wymaga co najmniej jednej daty. Godziny są wspólne dla zaznaczonych dni.
- `attendance_dates` są zapisywane transakcyjnie w osobnej tabeli i widoczne przez publiczną listę aktywnych punktów. To obecność sprzedawcy; nie stanowi jeszcze wyboru dnia konkretnego zamówienia przez klienta, nie zmienia rezerwacji/historycznych zamówień. Dawne punkty bez dat zachowują dotychczasowe działanie.
- Zmiana dat punktu z niezakończonym zamówieniem jest blokowana tak jak zmiana godzin/adresu. Cudzy punkt: 404. Daty przeszłe nie są pokazywane jako przyszła dostępność.

## Wdrożenie

Przed włączeniem `WP_ENABLE_PICKUP_DATES=1` trzeba na dedykowanej bazie testowej wykonać `database/optional_pickup_dates.sql` i nadać wp_preview_app `SELECT,INSERT,DELETE` do `public.pickup_point_dates`. Wykonać preflight z dotychczasowymi flagami poczty i jednostek. Nie zmieniać działających workerów SMTP ani ich kluczy. Domyślnie nowa funkcja jest wyłączona.

VPS ostatnio wskazywał release dd12f1a7, ale operator podał tylko active po restarcie; ponownie sprawdzić WorkingDirectory przed zmianą. Wcześniejsze panele 9d7423e7 były potwierdzone. Cache URL jest wersjonowany hashami zawartości, zawarty także w tej gałęzi.

## Walidacja

37 testów lokalnych (kalendarz/API/JS, izolacja kont, nawigacja, schemat) oraz osobno 19 testów jednostek sprzedaży przechodzi. Nowy test rzeczywistego PostgreSQL dodany do istniejącego modułu (72 zebrane). Test kalendarza Chromium i układu sprzedawcy w 320/1280 px dodany do bramki browser. Wykonanie nowych testów PostgreSQL/Chromium i pełnego Windows wymaga CI.

CI poprzedniego dd12f1a7: PostgreSQL 16/17 i Windows recovery SUCCESS, pełny Windows 4529 passed/1 failed/225 skipped (kontrakt nawigacji), Chromium 43 passed/7 failed. Diagnostyka wskazała stałe oczekiwania starej nawigacji, starej nazwy panelu oraz limit wysokości sprzed dodania etykiety roli. Kontrakty zaktualizowane do nowego interfejsu; nie przedstawiać poprzedniego przebiegu jako udanej regresji.
