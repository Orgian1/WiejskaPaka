# Kontakt i zgłoszenia — skrzynka demonstracyjna

Uruchom `START_DEMO_WINDOWS.cmd` lub `python scripts/run_phone_demo.py --full-demo`.

1. W stopce wybierz „Kontakt” lub „Zgłoś problem”. Oba linki prowadzą do tego samego formularza, zachowując wpisany tekst.
2. Podaj fikcyjny e-mail, temat od 3 do 160 znaków i wiadomość od 10 do 4000 znaków.
3. Kliknij „Wyślij wiadomość (TEST)”. Potwierdzenie oznacza zapis w testowej skrzynce administratora. Nie oznacza dostarczenia e-maila.
4. Zaloguj administratora z kont podanych przez launcher. Wybierz „Kontakt (TEST)” w górnej nawigacji; możesz odświeżać i przeglądać kolejne strony wiadomości.
5. Wylogowanie usuwa odczytane wiadomości i szkic formularza z interfejsu. Klient, rolnik i osoba niezalogowana nie mają dostępu do listy wiadomości.

Po utracie odpowiedzi możesz ponowić wysłanie niezmienionej wiadomości. Ten sam identyfikator nie tworzy drugiej kopii. Nie zmieniaj treści przed ponowieniem, jeśli chcesz sprawdzić poprzedni zapis.

Skrzynka przyjmuje do 5 nowych wiadomości z jednego adresu w ciągu godziny bieżącego procesu demo. Powtórzenie tego samego żądania nie zużywa limitu. Maksymalnie przechowuje 1000 wiadomości. Ctrl+C kończy demo i usuwa skrzynkę wraz z pozostałymi danymi próbnymi.

## Izolacja

Launcher tworzy osobny katalog poza projektem. Włącza `WP_ENABLE_TEST_CONTACT=1` i ustawia `WP_TEST_CONTACT_OUTBOX` wyłącznie dla własnego procesu lokalnego demo. Nie przejmuje ścieżki ani usług pocztowych z otoczenia. Domyślnie funkcja jest wyłączona; przy PostgreSQL i w trybie produkcyjnym nie rejestruje zapisu ani odczytu skrzynki.

To lokalny scenariusz do testowania. Nie podłączono SMTP/SES, nie wykonuje się połączeń z dostawcą poczty ani nie zmienia konfiguracji VPS. Nie używaj prawdziwych danych.
