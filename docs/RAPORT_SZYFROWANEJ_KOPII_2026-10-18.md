# Szyfrowana kopia testowej bazy — 18.10.2026

Dodano `scripts/encrypted_sqlite_snapshot.py`: niezależny klucz kopii,
uwierzytelnione szyfrowanie całej bazy i pierścienia kluczy zakupowych,
atomowa publikacja bez nadpisywania oraz odtworzenie do nowego katalogu.
Klucz musi być poza katalogiem archiwum. Limit bazy: 64 MiB.

Testy celowane: **42/42**, bez pominięć. Obejmują zakup i odtworzenie,
unieważnienie sesji, integralność audytu płatności, niezmienność źródła,
błędny klucz, zmiany nagłówka/nonce/treści/tagu, obcięcie i dopisanie danych,
nieprawidłową zawartość uwierzytelnioną, limity i prywatność CLI.
Uszkodzony kontener nie dociera do etapu zapisu jawnych plików tymczasowych.
Wczesna bramka odzyskiwania Windows wymaga teraz co najmniej 39 testów
bez błędów i pominięć; pełna regresja uruchamia je ponownie.

Pełna regresja Linux: **3658 zaliczonych, 0 błędów, 19 pominiętych**
(3677 przypadków, 291/291 modułów; źródła niezmienione podczas testów).
Wynik: `docs/audits/encrypted_snapshot_linux_2026-10-18.json`.

Kod: `9935ec67474e1150072cc3f10acb21063384aef0`.
Kontrole natywne: https://github.com/Orgian1/WiejskaPaka/actions/runs/39099834582
W chwili zapisania raportu nadal trwają; wcześniejsze zielone wyniki nie
stanowią potwierdzenia bieżącego kodu. Wyniki celowane zapisano w
`docs/audits/encrypted_snapshot_targeted_2026-10-18.json`.

Instrukcja: `docs/ODTWARZANIE_SQLITE.md`. Wersja pozostaje testowa.
Powstają prywatne jawne pliki tymczasowe; zwykłe sprzątanie nie gwarantuje
wymazania po awarii. Windows ACL, harmonogram, retencja, zdalny magazyn
i odtwarzanie PostgreSQL nie są wdrożone. Gałąź `main` pozostała nietknięta.
