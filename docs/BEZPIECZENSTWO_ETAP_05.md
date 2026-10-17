# Backend 05 — zabezpieczenia sesji i logowania

- Blokada logowania po pięciu nieudanych próbach na dany adres e-mail (15 minut), zapis w SQLite; licznik resetuje się po poprawnym logowaniu.
- `POST /auth/logout-all` unieważnia wszystkie sesje zalogowanego użytkownika.
- Nagłówki ochronne dla odpowiedzi HTTP oraz ograniczenie cache danych wrażliwych.
- Ograniczenie dotyczy adresu e-mail, nie adresu IP. To nie zastępuje limitowania na reverse proxy, WAF, monitoringu i ochrony przed DoS.
- Brak prawdziwych płatności. Nie wdrażać publicznie przed pełnym audytem.
- PostgreSQL nadal nie jest zaimplementowany. Następny etap: repozytoria i migracje DB.
