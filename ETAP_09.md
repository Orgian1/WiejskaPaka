# WiejskaPaka — Etap 09: prywatność adresów

Zmiany w istniejącym backendzie:
- Kurier uzyskuje adres dopiero w stanie `w_drodze_testowo`, a nie w stanie oczekiwania na płatność testową.
- Rolnik nie może pobierać adresu dostawy klienta przez `/orders/{order_id}/location`; ma dostęp tylko do punktu odbioru swoich zamówień.
- Klient nadal widzi lokalizację własnego zamówienia.
- Dostęp kuriera wygasa po użyciu PIN-u lub potwierdzeniu odbioru.

Ograniczenia: uprawnienia SQL konta aplikacji nadal są szerokie; RLS nie jest włączone. Wymagany dalszy audyt pozostałych endpointów i rzeczywisty test z Neon. Nie używać publicznie.
