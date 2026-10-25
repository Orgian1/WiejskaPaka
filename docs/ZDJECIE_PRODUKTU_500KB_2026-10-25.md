# Zdjęcie produktu i magazyn sprzedawcy

Formularz Dodaj produkt po włączeniu WP_ENABLE_USER_PHOTOS wymaga jednego zdjęcia JPEG, PNG lub WebP. Źródło do 20 MB jest oczyszczane z metadanych i zmniejszane na serwerze do maksymalnie 500 000 bajtów. Nowy POST /products/with-photo zapisuje produkt, jednostkę i zdjęcie w jednej transakcji. Niepoprawny obraz ani błąd zapisu zdjęcia nie pozostawia produktu. Dotychczasowe API /products pozostaje zgodne ze starszymi integracjami i przyjmuje produkty bez zdjęcia; nie wprowadzamy automatycznie zdjęć do istniejących produktów.

Aktualizacja zdjęcia produktu w istniejącym edytorze również stosuje limit 500 KB. Klucz (kind,subject_id) gwarantuje jedno zdjęcie na produkt; kolejny zapis zastępuje poprzednie. Profil i gospodarstwo zachowują limit 1 MB. Oryginały nie są przechowywane.

Panel sprzedawcy pokazuje własne produkty, zdjęcia, dostępne ilości z jednostką oraz ceny. Po dodaniu produktu lista odświeża się automatycznie. Zakupy innych kont nie są źródłem danych magazynu.

Wdrożenie wymaga sprawdzenia istniejącej tabeli user_photos, migracji database/optional_user_photos.sql wyłącznie gdy tabela nie istnieje, nadania roli aplikacji uprawnień SELECT,INSERT,UPDATE,DELETE oraz ustawienia WP_ENABLE_USER_PHOTOS=1. Nie uruchamiać ponownie migracji na istniejącej tabeli. Istniejącej migracji ani jej sumy nie zmieniano. Starsze zdjęcia nie są przepisywane; wymiana stosuje nowy limit.

Weryfikacja lokalna: 27 testów API, kompresji, uprawnień i audytu tras przeszło; obejmuje obraz z szumem, niedozwolone dane, magazyn i wycofanie produktu przy błędzie zapisu zdjęcia. Składnia JS sprawdzona. Test przeglądarkowy rozszerzony o dodanie produktu ze zdjęciem i widoczny stan 12 szt.; lokalnie Chromium niedostępny, wynik wymaga CI. VPS nie został zmodyfikowany.
