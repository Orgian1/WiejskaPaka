# B/661–B/680 — panele obsługi przesyłek

- Rolnik: przypisanie dostawcy, wysyłka całej przesyłki, zgłoszenie nieudanej dostawy z wyborem przyczyny, podgląd kwoty symulowanego zwrotu.
- Rolnik: jeden PIN dla przesyłek odbieranych osobiście.
- Dostawca: lista przesyłek i potwierdzanie całej przesyłki jednym PIN-em, bez ponawiania potwierdzenia dla każdego produktu.
- Powiadomienia: czytelna informacja o symulowanym zwrocie.

UWAGA: interfejs nie zastępuje kontroli uprawnień w backendzie. Zwrot jest symulowany i wymaga WP_ENABLE_TEST_PAYMENTS=1. Nie ma prawdziwego transferu środków. Przed produkcją konieczne są dalsze testy integracyjne i audyt.
