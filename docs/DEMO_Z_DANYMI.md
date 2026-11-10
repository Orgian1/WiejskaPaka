# Jednorazowe demo wszystkich ról

W katalogu projektu, po zainstalowaniu zależności według README:

```bash
python scripts/run_phone_demo.py --sample-data
```

Windows z istniejącym środowiskiem `.venv`:

```powershell
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --sample-data
```

Otwórz pokazany adres, domyślnie `http://127.0.0.1:8765`. Skrypt wypisze
cztery syntetyczne adresy `@example.invalid` i oddzielne losowe hasła:
klienta, rolnika, dostawcy i administratora. Skopiuj e-mail i hasło do formularza
logowania. Wybór roli w formularzu służy tylko rejestracji; podczas logowania
serwer rozpoznaje rolę istniejącego konta. Nie udostępniaj okna terminala.

Przygotowywane dane:

| Element | Stan początkowy |
| --- | --- |
| Rolnik | Fikcyjne gospodarstwo, potwierdzone zasady, profil oczekuje na przegląd |
| Produkty | Dwie oferty, ceny 3,49 zł i 2,99 zł, po 28 sztuk pozostałych po zakupach |
| Punkt | Demonstracyjny punkt w Legnicy, ze współrzędnymi do wyszukiwania |
| Klient | Dwie opłacone testowo przesyłki, każda z dwoma produktami |
| Odbiór | Przesyłka gotowa do odbioru, bez opłaty za dostawę |
| Dostawa | Przesyłka w drodze, przypisany dostawca; jedna opłata 5,01 zł |
| Administrator | Konto wyłącznie lokalne; w kolejce jeden oczekujący profil |

## Scenariusz odbioru

1. Zaloguj klienta i otwórz panel przesyłek. Dla przesyłki do odbioru wybierz
   odzyskanie testowego PIN-u i podaj hasło klienta z terminala. Nie zmieniaj
   ani nie regeneruj kodu. Zapisz go wyłącznie na czas sprawdzenia.
2. Wyloguj klienta, zaloguj rolnika. Potwierdź sprawdzenie towaru i odbiór
   całej przesyłki podanym PIN-em. Kilku pozycji przesyłki nie odbiera się osobno.
3. Dla dostawy odzyskaj PIN jako klient, następnie zaloguj dostawcę i potwierdź
   odbiór po sprawdzeniu towaru. Dostawca powinien utracić dostęp do adresu
   zakończonej dostawy. Nie wykonano rzeczywistego transportu ani płatności.
4. W panelu rolnika sprawdź stan profilu: dwa zakończone zakupy, po jednym
   za każdą przesyłkę. Cztery produkty nie oznaczają czterech transakcji. Po odbiorze przy pozycji
   zamówienia pojawi się „Przekaż pozycję do rozliczenia (TEST)”. To jawny
   krok symulacji finansowej; po jego wykonaniu podgląd rolnika pokaże
   dodatnią kwotę do testowej wypłaty. Nie wykonuje się przelewu.
5. Zaloguj administratora, pobierz kolejkę, wpisz fikcyjne uzasadnienie i zapisz
   decyzję testową. Po zapisie odśwież kolejkę. Zatwierdzenie nie włącza wypłat.
   Wybierz miesiąc i „Pokaż raport finansowy (test)”. Po przekazaniu jednej
   pozycji przez rolnika raport powinien wykazać jedną zakwalifikowaną pozycję
   i dodatnie kwoty. „Pobierz raport CSV (TEST)” zapisuje aktualny stan tego
   miesiąca z API. CSV używa średnika i kwot w groszach; widok pokazuje złote.
   Liczniki dotyczą pozycji produktów, nie całych przesyłek. Zmiana miesiąca
   usuwa poprzedni widok. Po wylogowaniu raport znika, ale wcześniej pobrany
   plik pozostaje w katalogu pobierania komputera.
6. Jako klient zgłoś fikcyjny problem z zakupem; odpowiedz jako rolnik,
   następnie zamknij sprawę testowo jako administrator. Szczegółowy odbiór:
   `ZGLOSZENIA_PROBLEMOW_TESTOWE.md`. Operacja nie zmienia płatności.
7. Możesz sprawdzić zmianę hasła, sesje oraz odzyskiwanie hasła. Ścieżkę
   prywatnej skrzynki resetującej skrypt pokazuje w terminalu. Instrukcja:
   `ODZYSKIWANIE_HASLA_TESTOWE.md`.

## Izolacja i zakończenie

Każdy start tworzy nowy prywatny katalog, bazę, klucz zakupów, konta i hasła.
Wcześniejsze sesje użyte do przygotowania danych są usunięte przed startem
serwera. Nie zapisujemy pliku z jawnymi hasłami. Dane logowania są wypisywane
wyłącznie lokalnie, dlatego nie dołączaj terminala do zrzutów i raportów.

Ctrl+C kończy demo i usuwa jego katalog. Kolejny start daje inne konta.
Nie używaj prawdziwych danych. Demo nie służy do zachowania pracy między
uruchomieniami. Kod projektu zapisany w GitHubie jest odrębny od tych danych.
Po awarii systemu sprzątanie katalogu tymczasowego nie jest gwarantowane;
usunięcie pliku nie oznacza bezpiecznego wymazania nośnika.

Opcja `--port 8766` zmienia port, ale nadal używa wyłącznie `127.0.0.1`.
Podgląd nie jest dostępny na innym telefonie lub komputerze. Nie zmieniono
hostingu, domeny, Neon ani produkcyjnych płatności. Windows ACL wymagają
oddzielnego sprawdzenia. Start bez `--sample-data` zachowuje puste demo.

Narzędzie przygotowawcze `scripts/prepare_sample_demo.py` wymaga nowego procesu
i nieistniejącego katalogu. Odmawia użycia istniejącego katalogu, pliku lub
zaimportowanej wcześniej aplikacji. To narzędzie nowej jednorazowej SQLite,
a nie importer do bazy użytkownika. Role administratora nie są dostępne przez
publiczną rejestrację HTTP. Nie dodano uniwersalnego hasła administratora.
