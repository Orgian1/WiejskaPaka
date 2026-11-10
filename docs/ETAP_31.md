# Etap 31 — eksport CSV raportu operacyjnego

`GET /test/admin/finance/monthly/{RRRR-MM}/export.csv` zwraca CSV UTF-8 z BOM,
separatorem średnikowym i nagłówkiem pobrania. Dostęp wyłącznie dla administratora,
przy `WP_ENABLE_TEST_PAYMENTS=1`; bez tej flagi odpowiedź 404. Wykorzystuje
te same wyliczenia co endpoint JSON etapu 30. Kwoty pozostają całkowitymi groszami,
nie są konwertowane na float. Włączono ochronę pól tekstowych przed formułami
arkuszy kalkulacyjnych, `Cache-Control: no-store` i walidację miesiąca.

**Nie jest to rejestr VAT, ewidencja księgowa ani dokument podatkowy.** Raport
odzwierciedla bieżący stan symulacji; zmiana statusu lub zwrot może zmienić
wyniki dla wcześniejszego miesiąca. Nie uzgadnia się jeszcze danych z operatorem
płatności. Brak połączenia z KSeF i prawdziwych transakcji.
