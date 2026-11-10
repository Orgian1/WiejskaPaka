# Pakiet B/20 — komunikaty interfejsu

Naprawiono wyścig czasowy w komunikatach (`web/app.js`). Wcześniejszy licznik czasu mógł ukryć nowszy komunikat przed upływem jego 6,5 sekundy. Każdy komunikat ma teraz numer wersji; starsze liczniki nie zmieniają widoczności aktualnego powiadomienia.

Dodano `tests/test_web_notice_timing.py`, test wykonywany w Node.js z symulacją upływu czasu. Mechanizm nie wymaga `clearTimeout`, co zachowuje zgodność z istniejącym środowiskiem testowym.

Testy lokalne: 2462 zaliczone, 6 pominiętych, 16 podtestów zaliczonych. Bez rzeczywistych testów PostgreSQL, fizycznego telefonu ani płatności produkcyjnych. Nie modyfikowano Neon i strony wiejskapaka.pl.
