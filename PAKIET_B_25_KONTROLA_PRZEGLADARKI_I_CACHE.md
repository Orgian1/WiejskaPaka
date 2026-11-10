# Pakiet B/25 — kontrola przeglądarki i poufności odpowiedzi

- Rozszerzono opcjonalny test Chromium o rzeczywiste kliknięcie nawigacji, sprawdzenie docelowej sekcji, fokusu formularza i pól logowania dla ekranów 320, 390 i 1280 px.
- Poprawiono nagłówek `Cache-Control: no-store` dla prywatnych tras `/couriers/` i `/products/mine`. Wcześniej zwracany był `no-cache` (wykrył to istniejący test regresyjny).
- Dodano dwa testy kontraktu narzędzia przeglądarkowego.
- Pełny lokalny zestaw: 2478 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych. Test Chromium na rzeczywistym silniku oraz PostgreSQL nie został tu potwierdzony.
- Nie zmieniano Neon, wiejskapaka.pl ani prawdziwych płatności.
