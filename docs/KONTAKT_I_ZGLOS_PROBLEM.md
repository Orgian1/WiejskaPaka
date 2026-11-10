# Kontakt i zgłoszenie problemu

Na dole strony znajdują się dwa linki: „Kontakt” i „Zgłoś problem”.
Oba wskazują nagłówek publicznego formularza `#contact-heading`, dostępnego bez logowania.
Link ustawia rodzaj wiadomości, zachowuje wpisaną treść i przenosi fokus
na nagłówek formularza. Można również samodzielnie zmienić rodzaj wiadomości.

Pola: rodzaj, e-mail do odpowiedzi, temat i wiadomość. Bez numeru telefonu.
Formularz mieści się na telefonie i komputerze. Nie zastępuje istniejących
zgłoszeń dotyczących zamówień w panelu zalogowanego użytkownika.

Zgodnie z prośbą e-mail zostanie podłączony później. Teraz przycisk wysyłki
jest wyłączony i wyświetlany jest komunikat o nieuruchomionym kontakcie.
Skrypt blokuje także wymuszone wysłanie formularza: nie przesyła ani nie
zapisuje treści, nie dodaje jej do URL i nie pokazuje fikcyjnego potwierdzenia.

Podłączenie osobnej skrzynki będzie kolejnym krokiem: adres odbiorcy
i konfigurację transportu należy ustawić po stronie serwera. Hasła i klucze
nie mogą trafić do plików publicznych. Punkt integracji interfejsu to obsługa
submit w `web/contact.js`; pola mają nazwy topic, email, subject i message.
Należy włączyć przycisk dopiero wraz z działającym odbiorem i potwierdzeniem
przyjęcia wiadomości. W tej zmianie nie uruchomiono SMTP ani PayU i nie
modyfikowano VPS.

## Sprawdzenie zmiany

Kod: `e7b6ed6a860205eadcf4283388445fe84ad8f038`, PR #55.
Lokalnie: 15 PASS, 0 FAIL, 0 SKIP — struktura stopki, zachowanie JS, nagłówek,
gotowość demo i struktura mobilna. Testy Chromium na rzeczywistym serwerze
potwierdziły oba linki, zachowanie treści, fokus, brak wysłania i czyszczenie
formularza przy szerokości 320 i 1280 px. Pierwszy przebieg ujawnił utratę
fokusu; oba linki kierują teraz na fokusowalny nagłówek, a test zachowano.

CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/42821692804.
Zakończone bramki: Chromium 78 PASS oraz HTTP w pięciu rozmiarach,
PostgreSQL 16 i 17 po 97 PASS, szybki Windows 91 PASS. Pełny Windows był
jeszcze w toku podczas zapisywania tych dowodów; nie przypisujemy mu wyniku
wcześniejszej wersji. Aktualny stan jest widoczny w powyższym przebiegu.
Raporty z odciskami źródeł: `audits/footer_contact_2026-11-10/`.
Końcowe uzupełnienie dokumentacji nie zmienia testowanego kodu.
