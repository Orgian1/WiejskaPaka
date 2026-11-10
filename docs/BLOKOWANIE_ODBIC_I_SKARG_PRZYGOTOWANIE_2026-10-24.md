# Blokowanie adresów po trwałych odbiciach i skargach — część wewnętrzna

## Gotowe

Dodano prywatny rejestr mail_recipient_blocks. Przechowuje tylko SHA256
zwalidowanego adresu z małych liter, powód permanent_bounce/complaint i czas.
Nie przechowuje adresu jawnie ani treści zgłoszenia. Zapis wymaga transakcji,
jest idempotentny i nie obniża skargi do zwykłego odbicia przy późniejszym wpisie.
Nie ma automatycznego odblokowania po ponowieniu linku czy potwierdzeniu adresu.

Obie komendy SES sprawdzają blokadę przed rezerwacją budżetu i przed SMTP.
Zwracają SUPPRESSED bez połączenia z transportem i bez zużycia limitu. Zakup
pozostaje w panelu, a jego wiadomość ma stan skipped; link weryfikacyjny jest
wygaszany i usuwany z zaszyfrowanej kolejki. Pierwotny zakup/PIN w sejfie nie jest
modyfikowany. Pozostałe zadania mogą być obsługiwane w granicach danej partii.

Nowa ręczna migracja optional_mail_suppression.sql, manifest z sumą kontrolną
i preflight wymagający tabeli są zapisane razem z kodem. Migracja nie została
zastosowana na VPS. Obie komendy pozostają domyślnie wyłączone.

## Granica zaufania — czego jeszcze nie ma

Funkcja block jest wyłącznie prywatnym interfejsem dla przyszłej, niezależnie
uwierzytelnionej ścieżki administracyjnej/dostawcy. NIE dodano publicznego endpointu
SNS ani importera dowolnego JSON. Żaden klient nie może zlecić blokady przez API.
Nie przyjmujemy flagi typu verified=true jako dowodu autentyczności zgłoszenia.

Przed automatycznym przyjmowaniem SES trzeba zweryfikować źródło/podpis SNS,
dozwolony temat ARN, konto i region, bezpieczne pobieranie certyfikatu, aktualność
oraz duplikaty zdarzeń; poprawnie powiązać zdarzenie z nadawcą i odbiorcą.
Skarga z ukrytym adresem wymaga dodatkowego mapowania identyfikatora SES.
Nie wolno zgadywać odbiorcy ani blokować całej listy z niezweryfikowanego JSON.
Brakuje również monitorowania i procedury kontrolowanego odblokowania.

Lista blokad jest kopiowana wraz z bazą. Po odtworzeniu budżet wysyłki pozostaje
wstrzymany przez poprzedni moduł. Przed jego wznowieniem trzeba uzgodnić aktualne
blokady z dostawcą — kopia nie zna zdarzeń po jej utworzeniu.

## Testy i źródła

Lokalnie 150 testów zaliczonych, 0 błędów, 0 pominięć, 14 izolowanych modułów.
Obejmują prywatność, normalizację wielkości liter, duplikaty, priorytet skargi,
rollback, wymaganie transakcji oraz blokadę obu rzeczywistych kolejek przed
transportem, bez naliczania próby. Dodano natywny test PostgreSQL z procesem
weryfikacji i rzeczywistym rejestrem blokad; jego wynik wymaga bieżącego CI.

Dokumentacja AWS wykorzystana do ustalenia zakresu:
- https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html
- https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications.html
- https://docs.aws.amazon.com/ses/latest/dg/troubleshoot-notifications.html

Żadnego rzeczywistego e-maila nie wysłano. VPS bez zmian.
