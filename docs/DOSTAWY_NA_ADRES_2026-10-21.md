# Terminy i akceptacja dostaw na adres

Implementacja testowa, domyślnie wyłączona: `WP_ENABLE_ADDRESS_DELIVERY=1`.
Na PostgreSQL wymaga migracji `optional_address_delivery.sql` i uprawnień
ograniczonej roli aplikacji do dwóch nowych tabel. Nie wdrożono jej na VPS.

## Sprzedawca

Sekcja „Dostawy na adres” ma zakładki „Zamówienia i akceptacja” oraz
„Dni i miejsca dostaw”. Sprzedawca dodaje miejscowość, kod pocztowy,
dzień tygodnia i godziny. Może wyłączyć termin dla nowych zamówień;
nie zmienia to wcześniej zapisanych warunków dostawy.

Sprzedawca akceptuje lub odrzuca całą przesyłkę (również wieloproduktową).
Decyzja jest transakcyjna, weryfikuje właściciela i rewizję, a ponowienie
tej samej decyzji nie zwraca towaru drugi raz. Odrzucenie anuluje zamówienia
i zwalnia ich rezerwacje. Płatność i wysyłka są blokowane przed akceptacją.
Zakładka pokazuje produkty, adres, datę, godziny klienta i wspólny przedział.
Stronicowanie obejmuje całe przesyłki, po 20 grup, bez ucinania ich produktów.

## Klient

W formularzu zamówienia i koszyka klient podaje istniejący adres oraz wybiera
opublikowany termin sprzedawcy, datę, godziny dostępności w domu i telefon.
Serwer sprawdza miejscowość i kod pocztowy, dzień tygodnia oraz przecięcie
godzin sprzedawcy i klienta. Daty: dziś do 90 dni naprzód, według Europe/Warsaw.
Terminy nie przechodzą przez północ. Dla dzisiejszej dostawy nie dopuszcza się
wyłącznie minionych godzin. Zapisuje się preferencje i wspólny przedział;
akceptacja nie oznacza automatycznie dokładnej minuty przyjazdu.

Dotychczasowa rezerwacja bez płatności nadal trwa 30 minut, także podczas
oczekiwania na akceptację. Wygaśniętej rezerwacji nie można zaakceptować.
Formularz i zakładka informują o tym terminie. Nie pobieramy rzeczywistych opłat.

## Numer telefonu i prywatność

Zgodnie z wcześniejszą zasadą numer nie jest udostępniany sprzedawcy ani
dostawcy. Zapisywany jest szyfrowany AES-GCM przy użyciu osobnego istniejącego
klucza checkoutu, z powiązaniem do zamówienia i kupującego. Listy dostaw,
publiczne terminy i powiadomienia nie zawierają numeru ani zaszyfrowanego pola.
Nie dodano wysyłki SMS ani połączeń telefonicznych.

Formularze i odpowiedzi pozostają prywatne, nie zapisują telefonu do pamięci
przeglądarki ani do URL. Zmiana konta usuwa formularze i widoki; spóźnione
odpowiedzi nie mogą przywrócić danych poprzedniej sesji. Retencja numerów,
zmiana i odczyt kontaktu przez właściciela wymagają dalszej polityki przed
produkcją; nie dodano endpointu udostępniającego numery.

## Zgodność i walidacja

Stare zamówienia bez nowych danych zachowują poprzedni przebieg. Oryginalne
hashowanie kluczy idempotencji dla payloadów bez terminu pozostaje zgodne;
nowe dane terminu/telefonu są objęte hashem, więc zmiana ich przy tym samym
kluczu nie tworzy drugiego zakupu. Nie można wyłączyć funkcji przy aktywnych
zamówieniach nowego typu. Odbiór w punkcie nie wymaga terminu dostawy na adres.

Zaliczone lokalnie: testy HTTP decyzji, szyfrowania kontaktu, ról, dopasowania
terminów, anulowania, wygaśnięcia i idempotencji oraz izolowane kontrole DOM.
Dodano trzy scenariusze realnego HTTP/PostgreSQL do istniejącej macierzy 16/17
(zakup bezpośredni, przesyłka zaakceptowana i przesyłka odrzucona z restartem).
Wynik pełnej regresji i nowej macierzy należy odczytać osobno; nie zastępują
testu konfiguracji i danych na VPS. Funkcja nie jest gotowością produkcyjną.

Pełna regresja lokalna commitu 4a59fad (na GitHub bb9133b): 4238 passed, 0 failed, 74 skipped; 336/336 modułów. Wszystkie części mają zgodny fingerprint i sources_unchanged=true. Raporty w docs/audits/address_delivery_2026-10-21/. 

CI GitHub Actions 39612932781 dla bb9133b: PostgreSQL 16 i 17 — po 50/50 testów; Windows recovery — 80/80; Chromium — 36/36 i kontrola viewportów zaliczone. Raporty JSON zapisano w native_bb9133b/. Pełna regresja Windows zakończona: 4154 passed, 0 failed, 158 skipped (4312 łącznie); bez błędnych, niekompletnych ani przekroczonych czasowo modułów. Wszystkie pięć zadań CI zakończone sukcesem. Źródła pozostały niezmienione; fingerprinty dowodów zgodne z pozostałymi zadaniami CI. Pominięte testy nie są liczone jako zaliczone. Raport windows-summary.json zawiera szczegóły.

## Rozszerzenie testów przeglądarkowych

Dodano cztery scenariusze rzeczywistego HTTP/Chromium z włączoną funkcją: akceptacja i odrzucenie, szerokości 320 i 1280 px, obrót do 844×390, formularz terminów sprzedawcy, formularz klienta, prywatność telefonu i czyszczenie po wylogowaniu. Scenariusze są częścią bramki browser w CI. Lokalna instalacja Chromium nie powiodła się (uszkodzona odpowiedź pobierania); nowe przypadki nie są objęte wcześniejszymi wynikami. Nowy przebieg CI 39646719218 dla commitu 4447348 potwierdził Chromium 40/40, 0 błędów, 0 pominięć oraz kontrolę viewportów. Zaliczone także PostgreSQL 16/17 i Windows recovery; pełny Windows dla tego commitu w chwili zapisu nadal trwa. Raport: native_4447348/chromium-summary.json.
