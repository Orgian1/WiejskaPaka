# Pakiet B/29 — rzeczywisty rendering offline w Chromium

Nowy skrypt `python -m scripts.check_mobile_offline --screenshots /tmp/wp_mobile` uruchamia prawdziwy silnik Chromium, wczytuje lokalnie HTML, CSS i JavaScript i przechwytuje `fetch`, zwracając **syntetyczne puste dane**. Dzięki temu nie potrzebuje serwera HTTP, połączenia z Neon ani dostępu do Internetu. Sprawdza szerokości 320, 390 i 1280 px, brak poziomego przewijania, widoczność publicznych i ukrycie prywatnych paneli, cele nawigacji, fokus formularza oraz błędy JavaScript. Zapisuje trzy zrzuty **publicznego** widoku.

To prawdziwy test renderowania w Chromium, ale **nie** test połączenia przeglądarki z działającym backendem, autoryzacji API, telefonu fizycznego ani wszystkich scenariuszy użytkownika. Nadal wymagane są testy integracyjne PostgreSQL, audyt RLS i testy na urządzeniu.
