# Integracja zmian zwykłego czatu i Work — WiejskaPaka

Połączony kod zachowuje cały portfel i pozostałe funkcje z Work oraz dodatkowe
bramki demonstracji i kontrolę nagłówka ze wspólnej gałęzi PR #50.
Nie zastąpiono jednego wariantu drugim: obie historie są rodzicami scalenia.

| Źródło | Włączone zmiany |
| --- | --- |
| PR #50, 6090820c4d66728ecf81ddc5956f5cc97424c181 | kontrola gotowości demo i regresja nagłówka przed szybkim Windows |
| PR #50, 5d2efe2526f49bdd2a9a5169ab4892e60d18cf68 | osobny, izolowany scenariusz zakup–odbiór–dostawa w bramce Windows |
| PR #50, b9ca634627c46daa542541504a7e84be3c072340 | unikalne identyfikatory HTML oraz istniejące cele linków logowania, rejestracji i panelu |
| Work, PR #53 | pełny profil demo, portfel, niezmienne warunki wypłat, decyzje końcowe i bezpieczne odzyskiwanie operacji |

Scalenie: `5dedc0e7b96c41a2ce2b8c1f063cd0c2991ee236`, rodzice:
`d284581be4ad8ebaea0b76e0e5ccf10f0aea18fb` (Work z zakończonym raportem)
oraz `b9ca634627c46daa542541504a7e84be3c072340` (aktualna gałąź PR #50).
Scalenie przeszło bez konfliktów. Zmiany względem ukończonego kodu Work dotyczą
wyłącznie workflow CI i testu nagłówka. Backend, frontend, migracje, zależności
i skrypty aplikacji pozostały identyczne; potwierdzono odciskiem źródeł.

## Weryfikacja

Lokalnie wykonano dokładne polecenia dodane do bramki:

- test_demo_readiness.py i test_header_auth_actions.py: 8 PASS, 0 FAIL, 0 SKIP;
- scripts.check_demo_readiness: PASS — strona i zasoby, zakup testowy, odbiór,
  dostawa, jednorazowy PIN, prywatność adresu, kwoty w groszach.

Pełne CI połączonego drzewa: https://github.com/Orgian1/WiejskaPaka/actions/runs/42797838007.
Zakończone: **5/5 zadań — sukces**, dla commitu `5dedc0e`.

| Bramka | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Windows — pełna izolowana regresja | 4640 | 0 | 275 |
| Windows — szybka regresja | 91 | 0 | 0 |
| PostgreSQL 16 — natywne i HTTP | 97 | 0 | 0 |
| PostgreSQL 17 — natywne i HTTP | 97 | 0 | 0 |
| Chromium — zdjęcia i scenariusze offline | 76 | 0 | 0 |

Pełna regresja Windows obejmuje 4915 przypadków, bez niekompletnych modułów
i przekroczonych limitów czasu. Pominięte 275 przypadków nie są zaliczeniami.
Chromium dodatkowo zaliczył HTTP w pięciu rozmiarach widoku. Oba dodane
przez zwykły czat kroki Windows — regresja nagłówka i gotowości demo oraz
izolowana ścieżka zakupu — zakończyły się sukcesem.
Zapisane artefakty i odciski źródeł:
`audits/ordinary_chat_integration_2026-11-10/`. Wszystkie pięć raportów
potwierdza zakończenie, sukces i niezmienność źródeł. Końcowy commit raportu
zmienia wyłącznie dokumentację; wyniki odnoszą się jawnie do `5dedc0e`.

Raport zakończonego wcześniej Windows oraz pozostałych bramek dla kodu Work
058f8b4: ODZYSKIWANIE_OPERACJI_PORTFELA_2026-11-10.md. Bazowa pełna regresja
Linux z tego raportu obejmuje ten sam kod aplikacji. Zmieniony test nagłówka
sprawdzono lokalnie, a komplet po scaleniu wykonuje nowe CI.

Próbna integracja z historią main została obliczona przez git merge-tree:
wynikowe drzewo jest identyczne z PR #53. Zapisano ją osobno na
integration/demo-main-20261110, commit 28c88591d63e849d511ea0bacda90b3d4bec9015.
Nie przesunięto main i nie zapisywano gałęzi PR #50–52.

Nie zmieniano VPS ani jego danych, nie podłączano PayU, prawdziwych płatności
ani banku. Ograniczenia i procedury bezpiecznego wdrożenia/rollbacku z poprzednich
raportów pozostają w mocy. Portfel nadal jest symulacją niezależną od płatności
zamówień i ich zwrotów.
