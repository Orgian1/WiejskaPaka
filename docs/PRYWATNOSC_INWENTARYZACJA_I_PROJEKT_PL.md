# Prywatność WiejskaPaki — inwentaryzacja i projekt do uzupełnienia

Stan techniczny: 18.10.2026, kod `aa0f7f6573ce3c418b5cf113975a7ecc1d846acd`.
Dokument roboczy do przygotowania docelowej polityki. Nie opublikowano go
w interfejsie i nie zastępuje kompletnej informacji dla użytkownika.

## Podmiot i kanał kontaktu — pola do ustalenia

- Administrator danych: [PEŁNA NAZWA I DANE PODMIOTU].
- Adres kontaktowy w sprawach danych: [E-MAIL I ADRES].
- Podział ról operatora i niezależnych sprzedawców: [DO USTALENIA].
- Inspektor ochrony danych, jeżeli właściwe: [DO USTALENIA].
- Dostawcy hostingu, poczty, kopii i płatności oraz ich lokalizacje:
  [DO WYBORU I WERYFIKACJI; NIE ZOSTALI PODŁĄCZENI W TYM PAKIECIE].

Nie wypełniać tych pól przypadkową nazwą właściciela konta GitHub. Tożsamość
podmiotu prowadzącego serwis wymaga rzeczywistej decyzji organizacyjnej.

## Dane i rzeczywiste zachowanie obecnej aplikacji

| Obszar | Co przetwarza kod | Dostęp i zapis |
| --- | --- | --- |
| Konto | E-mail, rola, skrót hasła Argon2, wewnętrzny identyfikator | Baza aplikacji; publiczna rejestracja nie nadaje administratora |
| Sesje | Skrót tokenu, użytkownik, termin wygaśnięcia | Token autoryzacji tylko w pamięci strony; w bazie skrót; użytkownik może cofnąć sesje |
| Ochrona logowania i resetu | Liczniki prób, okna limitów, blokady, skróty tokenów resetu i wersja hasła | Baza; limity nie są listą publiczną; reset ma jednorazowy token |
| Profil gospodarstwa | Nazwa, miejscowość, swobodny opis | Informacje oferty mogą być publiczne; nie wpisuj do opisu prywatnych danych |
| Punkt odbioru | Nazwa, adres, godziny, aktywność, współrzędne | Publiczne informacje punktu; to inny zakres niż pozycja klienta |
| Wyszukiwanie w okolicy | Współrzędne wpisane lub pobrane po kliknięciu lokalizacji | Używane przy wyszukiwaniu; kod nie zapisuje pozycji klienta w profilu ani trwałej pamięci przeglądarki |
| Zakup | Produkty, ilości, ceny w groszach, strony zakupu, realizacja, historia | Baza i zapis pierwotnych warunków; powiązanie wieloproduktowej przesyłki |
| Dostawa | Miejscowość, ulica, kod pocztowy | Dostawca uzyskuje dostęp do aktywnego przydzielonego zakupu; zakończenie dostawy odbiera ten dostęp, ale nie usuwa automatycznie historii z bazy |
| PIN odbioru | Skrót PIN-u oraz ograniczona czasowo zaszyfrowana odpowiedź zakupowa | Ograniczony przepływ klienta, odzyskanie po haśle; PIN nie jest wysyłany przez e-mail ani SMS |
| Płatności | Wyłącznie symulacje stanów i kwot, zdarzenia, rozliczenia testowe | Brak danych kart i prawdziwych rachunków odbiorców wypłat |
| Profil sprzedawcy | Potwierdzenie wersji zasad, decyzja testowego przeglądu i jej historia | Rolnik i administrator; nie jest weryfikacją tożsamości; brak pól zbierających PESEL lub rachunek |
| Zgłoszenie problemu | Kategoria, opis, odpowiedzi, stan obsługi, wersje, role i identyfikatory autorów w bazie | Kupujący, sprzedawca tego zakupu, administrator; brak dostępu dostawcy i obcych kont |
| Powiadomienia | Wpisy i stan przeczytania w panelu | Tylko właściwy użytkownik; rzeczywista poczta nie jest podłączona |
| Kopie | Baza i klucz sejfu zakupów według wybranego narzędzia | Osobne pliki operatora demo; szyfrowana kopia jest odrębnym narzędziem |

Nie ma osobnego pola telefonu. Swobodne opisy nie są automatycznie
anonimizowane: numer, hasło lub PIN wpisany w opis sprawy trafi do jej
uczestników. Formularze ostrzegają przed takimi wpisami i wymagają danych
fikcyjnych. Ta dokumentacja nie deklaruje filtracji, której nie ma w kodzie.

## Przeglądarka, skrzynka i logi

- Kod nie zapisuje tokenu logowania, PIN-u, adresu dostawy ani treści sprawy
  do localStorage/sessionStorage. Odświeżenie strony usuwa token z jej pamięci.
- sessionStorage jest jednak używany: przechowuje techniczne znaczniki
  nierozstrzygniętego zakupu i klucz ponowienia zamówienia, powiązane z
  wewnętrznym identyfikatorem konta. Nie jest to token autoryzacji. Nie należy
  opisywać aplikacji jako zupełnie niekorzystającej z pamięci przeglądarki.
- Przejrzane skrypty aplikacji nie ustawiają document.cookie ani nie ładują
  analityki reklamowej. Zachowania przyszłego hostingu i usług zewnętrznych
  nie zostały jeszcze ustalone ani zweryfikowane.
- Zgoda przeglądarki na geolokalizację pojawia się po kliknięciu przycisku.
  Możliwe jest ręczne wpisanie współrzędnych; nie trzeba włączać GPS.
- Lokalna skrzynka resetu zawiera fikcyjny adres odbiorcy i link z tokenem.
  To prywatny plik poza API. Nie ma operatora rzeczywiście wysyłającego pocztę.
- Launcher demo wyłącza access log uvicorna. Nie stanowi to gwarancji, że
  przyszły reverse proxy, system hostingu lub dostawca nie zapisze logów.
- Odpowiedzi prywatnych endpointów mają no-store; błędy walidacji nie
  dołączają wejściowych wartości hasła, PIN-u lub adresu do odpowiedzi.

## Okresy techniczne i nieustalona retencja

| Element | Obecne ograniczenie | Czego to nie oznacza |
| --- | --- | --- |
| Sesja logowania | Ważność 12 godzin, możliwość wcześniejszego cofnięcia | Automatycznego usunięcia całego konta lub wszystkich historycznych rekordów |
| Link resetu | Ważność 15 minut, jednorazowe zużycie; po zmianie hasła cofnięcie sesji | Gwarancji natychmiastowego wymazania lokalnych wiadomości z dysku |
| Odtwarzalny PIN w sejfie | Retencja odpowiedzi z PIN-em 24 godziny i zadanie czyszczenia działającej aplikacji | Usunięcia wszystkich skrótów PIN-u, zamówień i zapisów zakupu |
| Jednorazowe demo | Ctrl+C kończy serwer i sprząta jego katalog tymczasowy | Gwarancji sprzątania po awarii zasilania lub bezpiecznego wymazania nośnika |
| Opisy spraw, konta, zakupy i kopie | Brak zatwierdzonego ogólnego okresu retencji dla wdrożenia | Przyjęcia domyślnego okresu 5/6 lat ani zgodności z kompletną polityką usuwania |

Szyfrowany sejf PIN-u nie szyfruje całej bazy. Zwykła kopia i szyfrowana kopia
są różnymi narzędziami. Terminy usuwania kopii, skrzynek, historii spraw i
logów wymagają osobnego zaprojektowania przed użyciem rzeczywistych danych.

## Elementy docelowej informacji prawnej

Docelowa informacja powinna określać administratora, kontakt, cele i podstawy
przetwarzania, odbiorców, retencję oraz właściwe informacje o transferach,
wymagalności podania danych i decyzjach automatycznych. Trzeba opisać prawa
dostępu, sprostowania, usunięcia, ograniczenia, sprzeciwu, przenoszenia danych,
cofnięcia zgody tam, gdzie jest podstawą, oraz skargi do organu nadzorczego.
Zakres praw zależy od przesłanek; usunięcie ma ustawowe wyjątki. Zabezpieczenia
należy dobrać do ryzyka i weryfikować. Podstawy przetwarzania dla konkretnych
procesów oraz role stron pozostają do zatwierdzenia.

Źródło sprawdzone 18.10.2026: [RODO, art. 13, 15–22 i 32, oficjalny EUR-Lex](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:02016R0679-20160504).
Powyższa krótka lista nie jest kompletną analizą prawną modelu platformy.

## Prace do zamknięcia przed publikacją

1. Uzupełnić rzeczywisty podmiot, kontakty, role stron i podstawy procesów.
2. Ustalić dostawców, lokalizacje, umowy i przepływy danych.
3. Zatwierdzić okresy retencji wraz z mechanizmem czyszczenia oraz kopii.
4. Zaprojektować obsługę żądań dotyczących danych; obecny eksport zakupu
   obejmuje tylko warunki konkretnego zakupu, nie całe konto i wszystkie sprawy.
5. Określić weryfikację tożsamości zgłaszającego oraz ochronę danych innych osób
   przy udzielaniu odpowiedzi. Nie tworzyć publicznego endpointu eksportu po e-mailu.
6. Sprawdzić rzeczywisty hosting, logi, pocztę i dodatkowe skrypty, a następnie
   po zatwierdzeniu opublikować dokument oraz odpowiednie informacje w UI.

Podstawa techniczna: `web/app.js`, `web/nearby.js`, `web/support-cases.js`,
`backend/app.py`, `backend/password_reset.py`, `backend/checkout_vault.py`,
`backend/support_cases.py` oraz narzędzia kopii. Nie uruchomiono zmian
konfiguracyjnych ani zewnętrznych usług podczas sporządzania inwentaryzacji.
