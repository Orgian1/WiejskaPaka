# Synchronizacja GitHub — 17.10.2026

Dziewięć pakietów napraw v1–v9 opublikowano na `wiejskapaka-import`.
Końcowy commit kodu: `a2c2e5320d2c551c1dcebb985ffc15fca595d3ae`.
Drzewo plików: `68112e7bdb5b9ea7d91e79e39af9dda2214f5047`, identyczne z lokalnym v9.
`main` pozostał na `9b96de3b4f55255daf85c5280909e9ee8e5b21f4`.
Nie wykonano force push, wdrożenia ani konfiguracji płatności.

Zapis wykonano przez integrację GitHub; terminal nadal nie ma danych logowania
do `git push`. Odczyt przez `git fetch` działa. Integracja nadała nowe identyfikatory
commitów, zachowując osobne pakiety i identyczne drzewa plików każdego etapu.
Oryginalną lokalną historię zachowano na `wiejskapaka-import-local-v9`.

## Potwierdzone testy

Lokalna regresja Linux/Python 3.12.14: **3573 PASS, 0 FAIL, 17 SKIP**,
3590 przypadków, 283 moduły. Rzeczywisty HTTP: **4/4 zadania PASS**.
Po pobraniu opublikowanej gałęzi ponownie sprawdzono zgodność odcisku kodu
oraz hashy wszystkich 283 modułów z końcowym raportem v9. Samo przeniesienie
identycznych plików i ta dokumentacja nie stanowią nowego uruchomienia testów.
Dowody: `audits/regression_2026-10-17_v9_summary.json` i
`RAPORT_AUDYTU_PLATNOSCI_2026-10-17.md`.

Windows, natywny PostgreSQL, Chromium i 19 lokalnych historycznych modułów
nadal wymagają sprawdzenia. Nie są traktowane jako zaliczone. Aplikacja pozostaje
wersją demonstracyjną bez gotowości produkcyjnej. Audyt bezpieczeństwa/RLS,
zgodność konsumencka, wydajność oraz kopie i odtwarzanie wymagają dalszej oceny.

## Historia pakietów

| Pakiet | Lokalny commit archiwalny | Commit opublikowany |
| --- | --- | --- |
| v1 | `bc4f8d45ce26e2c2fd765cc4fc18e53b30e05394` | `bb7bd009ba3f8037e5ea3c32b3c7d844222be672` |
| v2 | `8278ded45a7dbd38288db331fa94fb522ff37cea` | `2c588f0accbc46abdb323210c0a9bf1017068c1e` |
| v3 | `0a3f92806a1c5f8401459f368aba2dbfd33955b3` | `3fb9c3ab7fae9bbb0a7c6524d1396abde78acb2b` |
| v4 | `e334e45d6f6519cd9e078653ce0ace09c98a1ae2` | `109f00c97e31bc695fd0fdd89237007e03b2cda0` |
| v5 | `f99bcfecd7ebf5745d8c7aaa9ccd44f2690269a7` | `710c3c0ac018b4f327960e50ed4262a51bcf70f0` |
| v6 | `ebf2a9554ff9460bc7f79c51e96c8b3b23145ff1` | `1466df2fe2f0cce5f86835e666daac3a9fbd8a76` |
| v7 | `83c58f77b01ace0cac77957c846a8ff97c332003` | `d83fb7c7aac01275f48ab10b96aa1c1baccb588c` |
| v8 | `eea0c09548682167874f256b3544deb8a6b6a0c7` | `34f3d4b381d5183a8906c984653e83eadafbae0b` |
| v9 | `0057577a24eea1a793409a7b31445daf717da660` | `a2c2e5320d2c551c1dcebb985ffc15fca595d3ae` |

Archiwalne ZIP-y v1–v9 opisują ówczesną lokalną historię i stan połączenia.
Ich informacje o braku wysyłki były prawdziwe w chwili sporządzenia raportów;
aktualny stan synchronizacji opisuje ten dokument. Nie stosuj starszego bundle
na nowej gałęzi jako aktualizacji fast-forward: identyfikatory historii są inne.
Jeżeli masz już commity z bundle lub własne zmiany, zachowaj je i połącz historie
zwykłym merge po przeglądzie. Odmowa `--ff-only` nie uzasadnia `reset --hard`
ani force push. Nie usuwaj baz, zakupów, kluczy i lokalnych plików.

Dla lokalnej gałęzi bez archiwalnych commitów i bez własnych zmian zwykłe
`git fetch origin`, przejście na `wiejskapaka-import` i
`git merge --ff-only origin/wiejskapaka-import` pobierają aktualny kod.
