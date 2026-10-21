# Publiczny login i wyszukiwanie sprzedawców

Dodano przełącznik „Szukaj produktu / Szukaj sprzedawcy” w katalogu.
W trybie sprzedawcy można szukać po publicznym loginie lub nazwie gospodarstwa.
Wpisanie @ ogranicza wyszukiwanie do loginów. Wielkość liter nie ma znaczenia;
nazwy gospodarstw są wyszukiwane także bez polskich znaków. Dokładny login
jest pierwszy, następnie loginy zaczynające się od zapytania i inne dopasowania.
Wyniki są stronicowane po 24; API dopuszcza maksymalnie 100 i offset 10000.
Znaki % i _ są literalne, a nie wzorcami przeszukującymi całą bazę.

Rolnik ustawia publiczny login w profilu gospodarstwa, w osobnym formularzu.
Login ma 3–30 znaków a–z, cyfr i podkreśleń, zaczyna się od litery, jest
zapisywany małymi literami i unikalny w bazie. Zastrzeżono nazwy obsługi,
np. admin i wiejskapaka. Nieudana zmiana nie usuwa dotychczasowego loginu.
Równoczesne próby zajęcia tego samego loginu mają jednego zwycięzcę.

To nie zmienia logowania: nadal obowiązuje prywatny e-mail i hasło. Login
publiczny nie jest automatycznie tworzony z e-maila. Sprzedawca pojawia się
w tej wyszukiwarce dopiero po świadomym ustawieniu loginu; formularz informuje
o publikacji loginu, nazwy gospodarstwa i miejscowości. Wyniki zwracają tylko
farmer_id, login, farm_name i city — bez e-maila, telefonu, adresu ani danych
formalnych. Klient i dostawca nie mogą ustawić loginu sprzedawcy.

Przycisk „Zobacz produkty sprzedawcy” przełącza na produkty i filtruje po
stałym farmer_id. Zmiana loginu nie zmienia właściciela produktów ani zamówień.
Filtr można wyczyścić przyciskiem pokazującym produkty wszystkich sprzedawców.
Stare wyniki są usuwane przy zmianie trybu/wyborze sprzedawcy, a spóźnione
odpowiedzi nie mogą zastąpić nowego trybu. Zmiana konta czyści prywatny
formularz i filtr; dane poprzedniej sesji nie wracają po spóźnionej odpowiedzi.

Funkcja opt-in: WP_ENABLE_SELLER_SEARCH=1, domyślnie wyłączona. PostgreSQL
wymaga sprawdzenia i wykonania optional_seller_directory.sql przez właściciela
schematu. Start z flagą i bez tabeli kończy się błędem. Przy starcie indeks
nazw gospodarstw jest odświeżany, także po edycjach dokonanych przy wyłączonej
funkcji. Edycja profilu przy włączonej funkcji aktualizuje indeks atomowo.
Dotychczasowe konta i zakupy nie wymagają nowych pól. VPS pozostaje bez zmian.
Wyszukiwanie lokalnych punktów „Produkty blisko mnie” nadal dotyczy produktów;
nowy przełącznik znajduje się w głównym katalogu.

Testy skupione: 19 testów API/logiki, 1 kontrola UI spóźnionych odpowiedzi
oraz 19 kontroli integracji UI/schematu zaliczone lokalnie. Dodano dwa
scenariusze rzeczywistego Chromium (320 i 1280 px, obrót widoku, ustawienie
loginu, wyszukiwanie, produkty sprzedawcy i koszyk) oraz dwa natywnego
PostgreSQL (restart/indeks i równoczesne zajęcie loginu).
Wynik pełnej regresji i natywnego CI należy potwierdzić osobno.

Uzupełniono izolowany test katalogu o nowy stan catalogSellerId (domyślnie null) i kontrolę parametru farmer_id. Dotychczasowe asercje paginacji, błędnych odpowiedzi i zmian sesji pozostają zachowane; 17/17 przypadków zaliczonych.
