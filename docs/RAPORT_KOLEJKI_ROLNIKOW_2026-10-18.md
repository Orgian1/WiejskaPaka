# Kolejka przeglądu profili rolników — 18.10.2026

Dodano odczytywaną na żądanie kolejkę administratora z filtrem stanu i stronami
po 20 profili. Administrator wybiera decyzję testową i uzasadnienie. Dane
kolejki są ograniczone do ID, wersji zasad, stanu i dat. Brak danych kontaktu,
tożsamości, rachunków i wcześniejszych uzasadnień. Zmiana konta usuwa listę
i robocze uzasadnienia. Po zapisie lub błędzie zapisu panel wymaga odświeżenia.

Nowy formularz przesyła wersję zasad, stan i datę dotychczasowego przeglądu.
Warunkowy UPDATE odrzuca stary widok kodem 409, bez nadpisania nowszej decyzji
lub dodatkowego zdarzenia. Sprawdzono równoczesne żądania HTTP i powrót statusu
do poprzedniej wartości. Starsze żądania bez pól expected_* zachowują dawną
semantykę; ochrona starego widoku dotyczy nowego formularza i klientów
wysyłających kompletny stan. Niepełny zestaw expected_* jest odrzucany.

Nie dodano publicznego nadawania roli administratora, migracji, zbierania danych
tożsamości ani rzeczywistych wypłat. Decyzja nie jest produkcyjną weryfikacją.
Instrukcja i kontrakt API: `PROFIL_ROLNIKA_TESTOWY.md`.

Kod: `20a99898fe84ea12ee941f639df953990b2f5fc2`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39102124109

| Kontrola | Wynik |
| --- | --- |
| Pełna regresja Linux, 297/297 modułów | 3693 zaliczone, 0 błędów, 25 pominiętych; 3718 przypadków |
| Testy celowane | 70 zaliczonych, 0 błędów, 2 pominięte (lokalnie brak Chromium) |
| Natywny PostgreSQL, ograniczona rola i HTTP | 17/17, bez pominięć |
| Natywne Chromium | 13/13, bez pominięć; dodatkowo HTTP przy pięciu szerokościach |
| Windows dla tej paczki | Pełna regresja nadal trwa; brak deklaracji PASS |

Odciski lokalnego kodu i testów porównano z artefaktami PostgreSQL i Chromium;
pliki ZIP zweryfikowano z digestami GitHub. Oczyszczone dowody:
`audits/admin_seller_review_linux_2026-10-18.json`,
`audits/admin_seller_review_targeted_2026-10-18.json`,
`audits/admin_seller_review_ci_2026-10-18/`. Nie publikowano danych, kluczy,
uzasadnień ani surowych logów. Źródła nie zmieniły się podczas regresji.

Poprzedni przebieg Windows dla `6ef815dec3b4043c64ec1977ce892b453b61d57c`
zakończył się sukcesem: 3671 zaliczonych, 0 błędów, 27 pominiętych oraz
wstępny podzbiór 39/39. Dowód uzupełniono w raporcie profilu rolnika;
nie przenosimy tego wyniku na bieżący kod. Gałąź `main` bez zmian.
