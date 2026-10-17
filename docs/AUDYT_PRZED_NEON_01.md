# WiejskaPaka — audyt przed podłączeniem Neon (2026-10-14)

## Zrobione
- Dodatkowe regresyjne testy blokowania migracji przy brakujących tabelach i kolumnach.
- Test kolejności tabel z kluczami obcymi.
- Test sprawdzania również dodatkowych tabel w bazie docelowej.
- Migrator jawnie sprawdza odroczone ograniczenia FK (`SET CONSTRAINTS ALL IMMEDIATE`) przed zgłoszeniem sukcesu.

## Niezweryfikowane
- Żadne połączenie z rzeczywistym PostgreSQL/Neon nie zostało nawiązane.
- Migracja danych nie była wykonywana na PostgreSQL.
- Nie przeprowadzono testów przeglądarkowych ani niezależnego audytu bezpieczeństwa.

## Gdy Neon będzie gotowy
1. Utworzyć **oddzielny, pusty projekt testowy**, nie bazę produkcyjną.
2. Wykorzystać bezpośrednie (nie pooled) połączenie do migracji.
3. Przekazać URL wyłącznie przez bezpieczne zmienne środowiskowe; nie wpisywać hasła w rozmowie ani w plikach ZIP.
4. Uruchomić schemat i migracje SQL, a następnie testy integracyjne i porównanie danych.
5. Nie przełączać strony publicznej ani płatności przed końcowym odbiorem.
