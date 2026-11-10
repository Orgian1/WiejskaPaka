# WiejskaPaka — B/581–B/600: wspólny PIN przesyłki (wersja testowa)

- Checkout koszyka generuje jeden 6-cyfrowy PIN dla całej przesyłki, zwracany tylko w odpowiedzi testowej jako `shipment_pin_test_only`.
- Każdy wiersz zamówienia przechowuje hash tego samego PIN-u; PIN nie jest przechowywany jawnie w bazie.
- `POST /shipments/{shipment_id}/confirm` atomowo potwierdza wszystkie pozycje przesyłki, dopiero po zaznaczeniu kontroli towaru.
- Próba potwierdzenia pojedynczego zamówienia powiązanego z przesyłką jest blokowana kodem 409.
- Dostęp ma wyłącznie właściciel gospodarstwa (odbiór osobisty) lub dostawca przypisany do **wszystkich** pozycji (dostawa na adres).
- Błędny PIN zwiększa licznik prób we wszystkich pozycjach, limit 5; ponowne potwierdzenie jest blokowane.
- Koszt dostawy pozostaje jednokrotny na przesyłkę.
- Dla starych zamówień niepowiązanych z przesyłką nadal działa endpoint potwierdzania pojedynczego zamówienia.

## Ograniczenia
- Nadal brak produkcyjnych płatności i pełnej integracji z Neon.
- Interfejs użytkownika dla wspólnego PIN-u wymaga dostosowania.
- Zestawy testowe współdzielą globalne ustawienia bazy, dlatego uruchamiaj je w osobnych procesach do czasu naprawy izolacji.
- Numeracja pakietu jest robocza, nie oznacza 20 odrębnych funkcji.
