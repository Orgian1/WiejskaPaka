# Kontakt i zgłoszenie problemu

Na dole strony znajdują się dwa linki: „Kontakt” i „Zgłoś problem”.
Oba wskazują publiczny formularz `#contact-section`, dostępny bez logowania.
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
