# WiejskaPaka — stan po zakończeniu modułu rozliczeń (19.11.2026)

## Zweryfikowane w GitHub Actions
- Monthly platform accounting regression: przebieg #223 — **success**, commit `d4b4d557`.
- Approved UI and wallet ads regression: przebieg #542 — **success**, ten sam commit.
- Raporty CSV są niefiskalne i generowane tylko do odczytu; nie stanowią potwierdzenia płatności.

## Następne priorytety dla demo
1. Potwierdzić, że demo uruchamia właściwy zatwierdzony widok; nie nadpisywać `web/index.html`, `web/style.css` ani `web/app.js`.
2. Przejrzeć istniejące RLS i uprawnienia PostgreSQL **w aktualnej gałęzi**, zanim uzna się izolację kont za bezpieczną. Starszy `AUDYT_ZBIORCZY_I_BRAMA_WDROZENIA.md` stwierdzał brak RLS; jest to raport historyczny, nie dowód obecnego stanu.
3. Przeprowadzić testy izolacji użytkowników, transakcji, magazynu i PIN na **odizolowanym PostgreSQL**. Zielone testy SQLite nie zastępują PostgreSQL.
4. Przeprowadzić końcowy odbiór funkcjonalny w przeglądarce na komputerze użytkownika i urządzeniu mobilnym.
5. Dopiero po osobnej decyzji planować PayU, fiskalizację, kopie zapasowe i produkcyjne wdrożenie.

## Ograniczenia
Ten dokument nie potwierdza ukończenia całej aplikacji. Nie wykonano tu testów na rzeczywistym PostgreSQL ani wdrożenia na VPS. Nie uruchomiono PayU. Nie należy scalać tej gałęzi do `main` bez odbioru.
