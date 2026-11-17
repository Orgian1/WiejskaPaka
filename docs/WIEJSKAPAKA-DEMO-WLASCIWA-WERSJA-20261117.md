# WiejskaPaka — właściwa wersja demo, 17 listopada 2026

## Jednoznaczna identyfikacja

- Repozytorium: `Orgian1/WiejskaPaka`
- Gałąź: `WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116`
- Zweryfikowany commit: `074fa4da0e343663dcd5beb0bbb731dea55351c0`
- Punkt wyjścia wyglądu: `codex/demo-finalization-20261112`; NIE zastępować interfejsem z innych gałęzi bez porównania i zgody właściciela.
- Nie scalać automatycznie do `main`, nie wdrażać produkcyjnie.

## Zweryfikowane kontrole GitHub Actions (commit 074fa4da)

- End-to-end demo journey: https://github.com/Orgian1/WiejskaPaka/actions/runs/44007728082 — success
- RLS disposable PostgreSQL API gate: https://github.com/Orgian1/WiejskaPaka/actions/runs/44007727942 — success
- Chromium browser checks: https://github.com/Orgian1/WiejskaPaka/actions/runs/44007728003 — success
- Wallet ads role targeting: https://github.com/Orgian1/WiejskaPaka/actions/runs/44007727996 — success

## Warunki odbioru na komputerze właściciela

1. Uruchomić właśnie tę gałąź i potwierdzić wzrokowo wcześniej zaakceptowany układ strony, produkty w rzędach i właściwy panel sprzedawcy.
2. Sprawdzić osobno konto klienta i sprzedawcy, koszyk, portfel, ogłoszenia, punkty odbioru, zamówienia i PIN.
3. Reklamy portfela: osobne treści dla klientów i sprzedawców, widoczny czerwony X z odliczaniem 5 sekund, samoczynne zamknięcie po 5 sekundach, najwyżej raz na 30 minut.
4. Testy automatyczne są zielone, ale nie zastępują wizualnej akceptacji ani kontroli na docelowym środowisku.
5. PayU produkcyjne pozostaje wyłączone do zakończenia integracji, formalności i testów z operatorem.

Nie mylić tego punktu kontrolnego z wcześniejszymi wersjami o innym wyglądzie.
