# Wznowienie i niezależna kontrola — 19.10.2026

Kontrolowany checkpoint: `6c1d999607d5c8cff29fca75521b57e23179520f`, gałąź `preview/queued-reset-http-20261019`. Kod testowany przez CI: `ee4b1a3deedd621d94de1b06dbc7c6ff033fe718`; późniejszy commit zmienia wyłącznie dokumentację. Nie przywracano starszych archiwów.

## Weryfikacja lokalna

Uruchomiono sześć modułów przez `scripts/run_tests_per_file.py`, każdy w osobnym procesie:

- test_checkout_vault_http.py
- test_checkout_retention_http.py
- test_reset_mail_queue.py
- test_reset_mail_keys.py
- test_queued_reset_config.py
- test_queued_reset_http.py

Wynik: **106 zaliczonych, 0 błędów, 1 pominięty; 6/6 modułów**. Raport: complete=true, success=true, sources_unchanged=true. Pominięcie dotyczy odmowy obsługi uprawnień na systemie innym niż POSIX; kontrolę wykonano na Linuksie. Poprzednia wspólna próba tych samych modułów również miała 106/0/1; nie sumujemy powtórzeń.

## Zweryfikowane artefakty CI

Przebieg: https://github.com/Orgian1/WiejskaPaka/actions/runs/39226979147

Pobrano trzy archiwa, porównano SHA-256 z digestem GitHub i odczytano raporty. Wszystkie mają complete=true, success=true, sources_unchanged=true, a pięć odcisków evidence zgadza się z lokalnym checkoutem.

| Bramka | Zaliczone | Błędy | Pominięcia |
| --- | ---: | ---: | ---: |
| PostgreSQL | 40 | 0 | 0 |
| Chromium | 36 | 0 | 0 |
| Windows recovery | 80 | 0 | 0 |

HTTP viewports: success=true. Pełny Windows w momencie kontroli pozostaje w toku. Wynik pakietu lokalnego nie zastępuje pełnej regresji i nie jest doliczany do jej historycznych liczb.

## Kontynuacja

Najpierw odebrać pełny Windows dla powyższego przebiegu, zweryfikować raport i jego evidence. Zachować nieudaną pierwszą próbę jako wynik historyczny. Dopiero po przejściu wymaganych bramek rozpatrywać połączenie PR #10 z wiejskapaka-import. Nie zmieniono kodu aplikacji ani nie połączono gałęzi. Dostawca poczty, hosting i rzeczywiste płatności pozostają niepodłączone.
