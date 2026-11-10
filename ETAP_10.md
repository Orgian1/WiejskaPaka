# Neon — etap 10: audyt bezpieczeństwa (tylko odczyt)

Dodano `backend/neon_security_audit.py` i testy regresyjne.
Audyt używa wyłącznie SELECT i nie aktywuje RLS ani nie modyfikuje danych.
Zgłasza brak tabel i wyłączone RLS. Nawet wszystkie RLS=true nie są dowodem
bezpieczeństwa: polityki, zweryfikowana sesja i testy izolacji danych są wymagane.

## Znane blokady
- RLS w Neon jest wyłączone na wrażliwych tabelach (wg testów użytkownika).
- Konto aplikacji ma SELECT na całych tabelach; serwer musi kontrolować każdy odczyt.
- Brak potwierdzonego połączenia backendu z bazą użytkownika.
- Nie wprowadzono zmian w Neon, domenie ani płatnościach.

## Następny etap
Zintegrować uwierzytelnianie i transakcyjny kontekst użytkownika z faktycznym
backendem PostgreSQL, dopiero potem przygotować i przetestować polityki RLS.
