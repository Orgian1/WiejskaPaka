# Pakiet B/22 — przygotowanie rzeczywistego testu mobilnej przeglądarki

Dodano `scripts/check_mobile_browser.py`: uruchamia tymczasowy serwer HTTP na
`127.0.0.1` z nową SQLite i sprawdza stronę w prawdziwym Chromium przy
szerokościach 320, 390 i 1280 px. Kontroluje błędy JavaScript, dostępność
podstawowych sekcji, brak wycieku prywatnych paneli przed zalogowaniem oraz
brak poziomego przewijania. Serwer i baza są usuwane po sprawdzeniu.

Uruchomienie (na komputerze z Chromium i Playwright):

    pip install playwright
    python -m scripts.check_mobile_browser

Playwright jest opcjonalną zależnością narzędzia testowego, nie aplikacji.

**Wynik w obecnym środowisku:** Chromium uruchamia się, lecz polityka
środowiska blokuje wejście przeglądarki na lokalny HTTP (`ERR_BLOCKED_BY_ADMINISTRATOR`).
Nie oznaczamy zatem testów wizualnych jako zaliczonych. Testy jednostkowe
samego runnera mogą przejść niezależnie od tej blokady.

Nie zmieniono Neon, publicznej strony ani integracji płatności.
