# Punkt wznowienia — stan 2026-10-25

Aktualna gałąź: preview/ses-feedback-trust-config-20261025. Repo Orgian1/WiejskaPaka.
Zmiany są stosem draft PR, bez scalania i bez modyfikowania VPS. Zachowywać lokalne
niezacommitowane zmiany przy odzyskiwaniu workspace.

Gotowe: uwierzytelnione API/panel potwierdzania adresu, szyfrowane linki,
atomowe kolejkowanie obu checkoutów, ograniczone procesy SES, wspólna blokada
wysyłki i limit kroczący, blokady odbiorców, offline weryfikacja podpisu SNS v2
z jawnie zatwierdzonym pinem oraz transakcyjne przetwarzanie jednoznacznego SES
z deduplikacją. Brak listenera HTTP, prawdziwych pinów i aktywacji na serwerze.

Bieżący pakiet lokalny: 74/74, bez błędów/pominięć, 7 izolowanych modułów.
Nowy raport: docs/audits/feedback_config_2026-10-25/local-summary.json.
Dodano chroniony zewnętrzny plik konfiguracji, rotację pinów i komendę kontroli
bez DB/sieci. Nie ma jeszcze odbiornika ani rzeczywistej konfiguracji AWS.
Anonimowy audyt rzeczywistego HTTP: 107/107 tras niepublicznych zablokowanych.
Raporty: docs/audits/pinned_feedback_2026-10-25/.

W Windows poprzednika (40119699868) były 3 błędy: dwa audyty nie uwzględniały
publicznego GET opcji weryfikacji, trzeci oczekiwał starej listy skryptów.
Odtworzono i naprawiono je, zachowując autoryzację tras prywatnych. Nie deklarować
zakończenia aktualnej pełnej regresji przed sprawdzeniem nowego CI.

Następne zadania:
1. Sprawdzić CI tej gałęzi, w tym native PostgreSQL i pełny Windows.
2. Operacyjne dostarczanie/rotacja pinów (loader i snapshot już gotowe), nie przez
   żądanie. Kontrola konfiguracji nie zatwierdza łańcucha CA dowolnego certyfikatu.
3. Odbiornik zdarzeń z ograniczoną polityką SNS i prywatnym archiwum REVIEW/starych
   zgłoszeń. Nie udostępniać bezpośrednio funkcji block ani przyjmować flag verified.
4. Korelacja identyfikatora SES dla ukrytych odbiorców, monitorowanie i harmonogram.
5. Sekrety SMTP poza kodem, rzeczywisty test własnej skrzynki, wdrożenie po kopii
   i pełne testy na VPS. Wszystkie funkcje nadal domyślnie wyłączone.

Domena wiejskapaka.pl została potwierdzona przez użytkownika w SES eu-north-1.
Nie oznacza to potwierdzenia limitów/trybu produkcyjnego konta ani adresów klientów.
Nie mamy tutaj rzeczywistych danych SMTP. Nie modyfikować VPS bez aktualnego
zakresu wdrożenia. Szczegóły: PODPISY_SNS_I_ZDARZENIA_SES_2026-10-25.md.

Szczegóły ostatniego pakietu: KONFIGURACJA_ZAUFANIA_SNS_2026-10-25.md.
