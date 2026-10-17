# WiejskaPaka — B/241–B/250: audyt spójności zamówień (zakres roboczy)

Dodano moduł `backend/order_integrity.py`, który wyłącznie odczytuje dane i zgłasza niespójności zamówień, przypisania produktu do sprzedawcy, kwot, metody realizacji, adresu/punktu odbioru, PIN i potwierdzenia odbioru oraz stanu magazynowego. Raport nie ujawnia danych osobowych.

Uruchom testy: `python -m unittest discover -s tests -p 'test_order_integrity_b241.py' -v`.

9 testów jednostkowych zaliczonych w środowisku lokalnym. Nie wykonano pełnej regresji ani testów integracyjnych PostgreSQL/Neon. Moduł nie został jeszcze podłączony do panelu administracyjnego ani harmonogramu. Nie modyfikuje zamówień i nie realizuje płatności.

Numeracja B/241–B/250 identyfikuje pakiet roboczy, a nie 10 niezależnych wdrożonych funkcji.
