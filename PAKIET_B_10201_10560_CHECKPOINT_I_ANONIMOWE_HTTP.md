# WiejskaPaka B/10201–B/10560 — weryfikacja i poprawa wiarygodności testów

## Naprawa systemu testowania
Skrypt `scripts/run_security_focus_isolated.py` wcześniej bezwarunkowo ufał statusowi PASS z poprzedniego raportu. Po zmianie kodu aplikacji mógł ponownie użyć starego PASS bez wykonania testu. Dodano odcisk SHA-256 treści modułu testowego, wszystkich plików Python backendu, konfiguracji pytest oraz samego runnera. Wynik jest wznawiany tylko przy identycznym odcisku; w raporcie oznaczono `reused_from_checkpoint`.

## Rzeczywiste kontrole wykonane lokalnie
- 2/2 nowe testy regresyjne mechanizmu odcisków.
- 78/78 niepublicznych tras HTTP odrzuciło żądania anonimowe (401/403); 0 niejednoznacznych odpowiedzi i 0 tras wymagających przeglądu w tym teście.
- 4/4 zestawy akceptacyjne HTTP PASS.
- Składnia JS i kompilacja Python PASS.

## Ograniczenia
Audyt anonimowy nie zastępuje kontroli uprawnień pomiędzy zalogowanymi rolami. Nie testowano rzeczywistego PostgreSQL, Chromium przez HTTP ani fizycznych telefonów. Nie uruchamiano produkcyjnych płatności i nie łączono się z Neon.
