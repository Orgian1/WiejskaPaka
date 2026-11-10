# WiejskaPaka — integracja Neon, etap 03 (14.10.2026)

Dodano `backend/neon_readiness.py`: kontrola struktury bazy PostgreSQL w trybie tylko do odczytu. Nie wymaga ani nie ujawnia hasła w kodzie. Sprawdza wymagane tabele i kolumny, ograniczenia administracyjne konta aplikacji oraz raportuje status RLS. Wynik **nie** jest certyfikatem bezpieczeństwa.

## Uruchomienie później, na serwerze backendu (nie w SQL Editor Neon)

1. Zainstaluj zależności z `requirements.txt` oraz `psycopg[binary]`.
2. Ustaw `DATABASE_URL` w prywatnych zmiennych środowiskowych backendu, z TLS. Nie wpisuj go do repozytorium, nie przesyłaj w rozmowie.
3. Uruchom `python -m backend.neon_readiness` z katalogu projektu.
4. Nie uruchamiaj publicznie, dopóki nie przejdą testy integracyjne oraz kontrola autoryzacji i RLS.

**Ważne:** dotychczasowe konto `wiejskapaka_app` nie ma ustawionego hasła, więc połączenie nie zostało przetestowane. RLS pozostaje wyłączone. Nie zmieniaj tego ręcznie bez wdrożenia polityk i testów. Nie zmieniano publicznej strony ani nie uruchomiono płatności.

**Znane ograniczenie finansowe:** obecny schemat `payment_simulations` zawiera dwie części rozliczenia (`commission_grosze`, `seller_grosze`), nie trzy niezależne części 75/20/5. Wymaga osobnej migracji i dopasowania logiki backendu.
