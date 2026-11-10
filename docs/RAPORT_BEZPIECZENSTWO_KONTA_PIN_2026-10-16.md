# WiejskaPaka — bezpieczeństwo konta i odzyskanie PIN-u, 16 października 2026

Commit kodu i testów: `27980612c9fdaa9f0f9b59689b0a685055337dad`. Odcisk kodu, skryptów, SQL i zadeklarowanych
zależności: `3e56293b6b7bcf49cc4fc8f75d7c40c6e1f603ba289aa3b369044c38c1af4041`.

## Wynik

Dodano odzyskanie PIN-u istniejącego zakupu po ponownym podaniu hasła oraz
atomową zmianę hasła z cofnięciem wszystkich sesji. Wykonano **3250 zaliczonych
przypadków pytest, 0 niezaliczonych i 18 pominiętych**, w tym **122 nowych
zaliczonych przypadków**. Dwa nowe przypadki PostgreSQL mają SKIP.

Prace i lokalne commity wykonano bez GitHub, publikacji, GitHub Actions,
produkcyjnych płatności, hostingu, domeny, Neon i usług płatnych. Numeracja
B/10921–B/11280 jest oznaczeniem trwającej paczki; nie oznacza wykonania
wszystkich jej pozycji ani liczby testów. Nie potwierdzamy szacunku 90% ukończenia.

## Naprawione problemy i dodane funkcje

1. **Utrata PIN-u po odświeżeniu strony lub utracie odpowiedzi.** Klient może
   odczytać ten sam kod w historii zamówienia lub przesyłki po ponownym podaniu
   hasła. Nie potrzebuje pierwotnego żądania, adresu ani klucza operacji.
   Odczyt nie tworzy zamówienia, nie zmienia kodu, magazynu, kwot ani rezerwacji.
2. **Brak bezpiecznego powiązania historii z szyfrogramem.** Nowa tabela
   wskazuje cache konkretnego zakupu. Zapis jest częścią transakcji checkoutu.
   Start odtwarza powiązania starszych uwierzytelnionych odpowiedzi, sprawdzając
   kupującego, bez wydłużania retencji. Podczas odzyskania ponownie porównujemy
   zestaw zamówień, przesyłkę i skróty PIN-u. Podmiana powiązania daje odmowę.
3. **Brak zmiany hasła i cofnięcia wszystkich sesji.** Nowy formularz i API
   wymagają obecnego hasła, zapisują Argon2id i usuwają wszystkie tokeny konta
   w jednej transakcji. Nie cofają sesji innych użytkowników. Ponowne logowanie
   wymaga nowego hasła. Zakupy, klucz szyfrowania i pierwotny PIN pozostają te same.
4. **Rozbieżność PostgreSQL z długością klucza.** Publiczne API przyjmuje do
   100 znaków, a prefiks `direct:` dodaje siedem. Nowa migracja podnosi limit
   istniejącego ograniczenia SQL do 107. To naprawa stwierdzona z kodu;
   wykonanie na natywnym serwerze nadal wymaga osobnej bramy.
5. **Bezpieczeństwo nowych przepływów.** Każdy ma niezależny, trwały limit
   pięciu prób na konto w 15 minut, wspólny dla tokenów i odporny na restart.
   Błędne hasło nie wycofuje licznika. Limit daje 429 i `Retry-After`.
   Sesja i rola są sprawdzane ponownie w transakcji. Awaria szyfrowania,
   powiązania, haszowania lub usuwania sesji nie zostawia częściowego zapisu.
6. **Pozostawianie hasła w formularzu logowania/rejestracji.** Wartość pola
   jest teraz usuwana przed żądaniem, również przy późniejszej odmowie. Zmiana
   konta i wylogowanie też czyszczą pole. Cztery nowe przypadki wykonują
   rzeczywiste handlery JavaScript, sprawdzając sukces i błąd obu operacji.
7. **Pozostawanie sekretu w widoku.** Odzyskany PIN znika po 30 sekundach,
   zamknięciu, ukryciu karty lub zmianie konta. Pola haseł są czyszczone przed
   żądaniem. Spóźnione odpowiedzi nie przywracają PIN-u ani nie wylogowują
   nowszego konta. Odpowiedzi są `no-store`; nie zapisujemy haseł, PIN-u,
   tokenu ani adresu w localStorage/sessionStorage.

Cztery dotychczasowe testy struktury UI dostosowano do dodatkowego czyszczenia
widoku oraz nowych skryptów. Zachowano sprawdzenia wcześniejszych blokad
zakupów i kolejności `defer`; działanie nowych formularzy wykonuje także Node.
Ochrony wprowadzone dla nowych funkcji opisujemy jako ich projekt i testy,
a nie jako wcześniej odtworzone luki starego endpointu, którego nie było.

## Faktycznie uruchomione bramy

| Brama | Wynik |
|---|---|
| Pełna regresja z czystej kopii, osobny proces i baza na moduł | **254 moduły; 3250 PASS, 0 FAIL, 18 SKIP** |
| Nowe przypadki odzyskiwania PIN-u | **85 PASS**: 48 API, 13 polityka, 17 Node, 7 rzeczywisty HTTP |
| Nowe przypadki haseł i formularzy konta | **37 PASS**: 21 API, 12 Node, 4 rzeczywisty HTTP |
| Test długotrwały rzeczywistego HTTP | **PASS**, 1500.33 s; 12249 rund, 113627 żądań, 282459 sprawdzeń |
| Odzyskiwanie PIN-u w teście długotrwałym | 2450 żądań: 10 udanych odczytów i 2440 odpowiedzi limitu |
| Wyścigi zmiany hasła z logowaniem starym hasłem w teście długotrwałym | **122 PASS** |
| Osobny rzeczywisty HTTP historii zakupu i pełnego zwrotu | **50 żądań, 187 sprawdzeń, PASS** |
| Pakiet akceptacyjny HTTP | **4 zadania PASS** |
| Anonimowe żądania do prywatnych tras | **86/86 zablokowanych**, bez wyniku niejednoznacznego |
| Właściwości finansowe z niezależnym wzorcem Decimal | **20 001 kwot, 100 002 sprawdzenia, PASS** |
| Składnia i zależności | **366 plików Python, 10 JavaScript, pip check PASS** |
| Natywny PostgreSQL | **NIE URUCHOMIONO; 16 SKIP**, nie PASS |
| Chromium | **NIE URUCHOMIONO; 2 SKIP**, nie PASS |

Liczby żądań, właściwości i powtórzeń nie zwiększają liczby odrębnych przypadków
pytest. Obecna pełna regresja i końcowy test długotrwały dotyczą tego samego
odcisku. Wcześniejsze kontrole rozwojowe i wyniki poprzednich paczek nie są
dowodem końcowego kodu. Przebiegi rozwojowe przerwane przy zmianach kodu nie są wliczane jako
zaliczone końcowe testy stabilności.

Testy wykonano Pythonem 3.12.14 i Node v24.19.0. Szczegóły wersji bibliotek
zapisano w `audit_security_final_syntax_dependencies.json`.

## Finanse i obowiązkowe zasady

Rzeczywiste HTTP obejmuje zarówno pojedynczą dostawę, jak i wielopozycyjną
przesyłkę. Używa odzyskanego PIN-u, odrzuca potwierdzenie bez sprawdzenia towaru,
liczy błędne próby, dopuszcza odbiór tylko raz i następnie symuluje wypłatę.
Druga ścieżka zgłasza winę dostawcy, zwraca całą wpłatę łącznie z dostawą,
sprawdza idempotencję zwrotu i zerową wypłatę. Po zakończeniu kod nie jest
odzyskiwany, a kurier traci dostęp do aktywnego adresu.

Kwoty i obliczenia finansowe są całkowitymi groszami. Dodatnia opłata za adres
jest naliczana raz na przesyłkę; odbiór w punkcie pozostaje dostępny. Nowe
funkcje nie zbierają numerów telefonów. Informacja o ustawowych prawach
konsumenta pozostaje w interfejsie; PIN potwierdza odbiór, nie uchyla reklamacji.
Podział 75/20/5 pozostaje testową funkcją, nie zatwierdzonym modelem rozliczeń.
Nie wykonano przelewów ani rzeczywistych płatności.

## Migracja, uruchomienie i odtworzenie

ZIP zawiera pełny projekt, testy, instrukcje, SQL, końcowe raporty JSON,
lokalną historię Git w bundle i manifest SHA256. Nie zawiera bazy aplikacji,
klucza checkoutu, plików środowiska, venv ani cache. Nowe lokalne demo tworzy
własną jednorazową bazę oraz klucz. Zależności opisuje `requirements-lock.txt`.

SQLite tworzy nowe tabele automatycznie. Dla PostgreSQL przygotowano
`upgrade_z_checkout_pin_recovery.sql` i `upgrade_z_password_change.sql`;
trzeba zastosować je po dotychczasowych migracjach, przed uruchomieniem API.
Brak tabel blokuje start, również przy pustym cache. Nie zastosowano SQL na
żadnym serwerze produkcyjnym. Przed aktualizacją własnej instalacji zatrzymaj
starą instancję i zachowaj spójną kopię bazy wraz z osobno chronionym kluczem.

Odtworzenie lokalnej historii nie wymaga GitHub:

```bash
git clone WiejskaPaka_git.bundle WiejskaPaka_odtworzona
```

Instrukcje funkcji i ograniczeń: `docs/ODZYSKIWANIE_PIN.md`,
`docs/BEZPIECZENSTWO_KONTA.md`, `docs/SZYFROWANIE_ODPOWIEDZI_ZAKUPU.md`,
`docs/POSTGRESQL_TESTY_LOKALNE.md`. Starsze dokumenty i raporty są historią;
nie zastępują obecnych końcowych dowodów.

## Stan projektu i pozostałe prace

To nadal aplikacja demonstracyjna. PostgreSQL nie został uruchomiony:
środowisko ma wyłącznie mapowanie UID 0 i nie ma Docker. Chromium również nie
zaliczyło bramy; wykonywane testy Node z kontrolowanym DOM nie zastępują przeglądarki.
Wcześniejsze odmowy startu i niedostępność lokalnego HTTP z przeglądarki są
udokumentowanymi ograniczeniami, a nie zaliczonymi obecnie próbami.

Odzyskanie dotyczy zakupów z zapisanym cache i okresu do 24 godzin. Starszych
zakupów bez cache ani usuniętego PIN-u nie odtwarzamy. Zablokowanego kodu nie
resetujemy. Produkcyjny kanał przekazania PIN-u oraz procedura po utracie kodu
po retencji pozostają do zaprojektowania; nie należy tworzyć drugiego zakupu.

Pozostają m.in. odzyskanie zapomnianego hasła, weryfikacja sprzedawcy,
uzgodnienie opłat punktów i dostawców, pełny odbiór mobilny oraz niezależny
audyt wdrożenia, podatków, rozliczeń i procedur konsumenckich. Szyfrowanie cache
PIN-u nie oznacza szyfrowania całej bazy; adresy dostaw w lokalnym demo nadal
są w tabeli lokalizacji. Nie deklarujemy gotowości do produkcji.
