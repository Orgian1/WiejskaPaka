# B/1321–B/1380 — spójność anulowania i symulacji płatności

Wdrożono zabezpieczenia transakcyjne:
- anulowanie całej przesyłki odrzuca zamówienia z płatnością w stanie innym niż `awaiting_payment`;
- anulowanie pojedynczego starszego zamówienia stosuje identyczną zasadę;
- API symulacji nie przyjmuje nowych zdarzeń płatności dla zamówień anulowanych lub innych niż oczekujące na płatność;
- test regresyjny sprawdza zablokowanie anulowania częściowo opłaconej przesyłki, brak zmiany stanów magazynowych i brak możliwości zapłacenia po anulowaniu.

To celowo konserwatywna blokada: osobny proces anulowania **po płatności** i zwrotu testowego nie został jeszcze wdrożony. Wszystko pozostaje w trybie offline/testowym. Nie zmieniano konfiguracji Neon ani migracji bazy danych.
