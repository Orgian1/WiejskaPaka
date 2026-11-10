# Paginowany katalog produktów

Główny widok korzysta z istniejącego `GET /catalog/search` zamiast pobierać
cały `/products`. Jedno odświeżenie renderuje najwyżej 24 karty.

- Wpisz nazwę i wybierz „Szukaj produktów”. Wyszukiwanie rozpoczyna się
  od pierwszej strony, również gdy wcześniej otwarto dalszą stronę.
- „Następne produkty” i „Poprzednie produkty” poruszają się po stronach.
  Przycisk jest niedostępny podczas pobierania albo na końcu wyników.
- „Odśwież katalog” wraca do pierwszej strony z bieżącą nazwą.
- Puste wyszukiwanie pokazuje dostępne produkty. Brak dopasowania nie jest
  błędem i pokazuje komunikat zamiast kart.
- Nazwa może mieć do 120 znaków. Filtry ceny i odległości pozostają
  dostępne w osobnym panelu „Produkty blisko mnie”.
- Po limicie przesunięcia API 10000 trzeba zawęzić nazwę; interfejs pokazuje
  tę informację i nie wysyła żądania poza limitem.

Nazwa jest kodowana jako parametr, a nie składana do URL ręcznie. API zachowuje
istniejącą obsługę polskich znaków oraz dosłowne traktowanie wildcardów.
Nie zmieniono reguł ceny, dostępności ani zakupu. Karta nadal umożliwia
zamówienie testowe i dodanie do koszyka; serwer ponownie weryfikuje zakup.

Nowe żądanie unieważnia starszą odpowiedź. Zmiana konta lub wylogowanie
unieważnia pobranie rozpoczęte w poprzedniej sesji. Nieprawidłowe metadane,
zbyt duża strona lub wadliwe kwoty nie są renderowane jako poprawny katalog.
Po błędzie można ponowić wyszukiwanie. Dotychczasowy endpoint `/products`
pozostaje dostępny dla zgodności istniejących integracji testowych; nie jest
już źródłem głównego widoku przeglądarki.

## Odbiór

1. Utwórz co najmniej 50 ofert na fikcyjnym koncie rolnika.
2. W katalogu sprawdź najwyżej 24 karty, kolejną stronę i ostatnią krótszą
   stronę. Przejdź wstecz.
3. Wyszukaj dokładną nazwę jednej oferty, a następnie tekst bez dopasowania.
   Wyczyść nazwę i ponów wyszukiwanie.
4. Zaloguj klienta, dodaj produkt z katalogu do koszyka i sprawdź jego nazwę.
5. Wyloguj się i potwierdź brak kontrolek zakupu. Powtórz przy 320 i 1280 px.

Test natywnej przeglądarki przygotowuje 52 rzeczywiste oferty i sprawdza
strony 24/24/4, filtr, pusty wynik oraz koszyk przez HTTP. Kontrole JavaScript
obejmują najnowszą odpowiedź, zmianę konta, błąd sieci, kodowanie parametrów,
limit przesunięcia i odrzucanie wadliwych danych. Makiety offline aktualizują
kształt odpowiedzi do kontraktu paginowanego; nie zastępują testu serwera.

Paginacja ogranicza wielkość renderowanej strony. Sama nie potwierdza
wydajności całego systemu, PostgreSQL ani obsługi 5000 kupujących dziennie.
