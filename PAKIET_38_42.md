# Pakiet 38–42 — autoryzacja testowych operacji rozliczeniowych

W pięciu endpointach POST ponownie weryfikowana jest sesja użytkownika
w tej samej transakcji PostgreSQL co modyfikacja danych:
- tworzenie tygodniowego planu wypłat;
- rezerwowanie planu;
- anulowanie rezerwacji;
- zbiorcza kontrola rezerwacji;
- administracyjne uruchomienie przebiegu planowania.

Mechanizm `order_write_db` sprawdza zgodność ID i aktualnej roli użytkownika
z sesją. SQLite pozostaje lokalnym wariantem developerskim. Operacje nadal
wymagają `WP_ENABLE_TEST_PAYMENTS=1`; **nie wysyłają przelewów**.

**Ograniczenia:** Nie wykonano testów na żywej bazie Neon. RLS jest wyłączony.
Inne endpointy rozliczeniowe i księgowe wymagają dalszego przeglądu. Nie
należy uruchamiać aplikacji publicznie ani podłączać prawdziwych płatności.
