# Punkt wznowienia — WiejskaPaka

Aktualna gałąź: preview/mail-suppression-core-20261024. Zmiany są przygotowywane
w stosie draft PR, bez scalania i bez wdrożenia VPS. Nie zastępować lokalnych
niezacommitowanych zmian przy odtwarzaniu workspace.

Gotowe w kodzie: rejestr potwierdzeń adresu + uwierzytelnione API/panel,
szyfrowana kolejka linków, atomowe kolejkowanie potwierdzeń przy obu zakupach,
ograniczone procesy i jawne komendy SES, zaufana kwalifikacja adresata/PIN-u,
wspólna dzierżawa i kroczący limit 24 godzin, wstrzymanie wysyłki po restore,
prywatna lista blokad sprawdzana przez obie komendy.

Ostatni lokalny pakiet: 150/150, 0 błędów/pominięć, 14 izolowanych modułów;
raport docs/audits/mail_suppression_2026-10-24/local-summary.json.
CI poprzedniego PR #32: PostgreSQL 16/17, Chromium i szybki Windows zaliczone;
pełny Windows jeszcze trwał przy ostatnim sprawdzeniu. Nowy pakiet wymaga
własnego CI, szczególnie nowego natywnego testu blokad. Nie utożsamiać zaliczonych
wyników przodka z wynikami ostatniego commitu.

Kolejne zadania:
1. Sprawdzić CI tej gałęzi i pełną regresję Windows poprzedników.
2. Zbudować uwierzytelniony odbiór zdarzeń SES/SNS lub prywatny odbiór kolejki,
   z weryfikacją pochodzenia i idempotencją. Nie wystawiać block jako surowego API.
3. Powiązać zdarzenia bez jawnego adresu z identyfikatorem wiadomości dostawcy.
4. Dodać monitorowanie, kontrolę gotowości i ograniczone uruchamianie partii.
5. Dopiero po konfiguracji sekretów poza kodem wykonać test własnej skrzynki,
   następnie wdrożenie z kopią bezpieczeństwa i testami na VPS.

Nie mamy tutaj skonfigurowanych rzeczywistych danych SMTP. Użytkownik potwierdził
w SES domenę wiejskapaka.pl; region eu-north-1. Nie uznawać tego za potwierdzenie
trybu produkcyjnego/limitów konta ani własności adresów klientów. Wszystkie flagi
są domyślnie wyłączone. Nie zmieniać VPS bez aktualnej autoryzacji do wdrożenia.
