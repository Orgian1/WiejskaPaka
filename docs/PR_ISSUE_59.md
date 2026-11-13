# Przygotowany Pull Request: paczka #59 przed odbiorem VPS

Repozytorium: Orgian1/WiejskaPaka

Base: `codex/product-categories-filters-20261113`

Head: `codex/issue-59-pre-vps-20261113`

Tytuł: `Paczka #59: sesje, liczniki, kontakt, GPS, Photon i zamówienia sprzedawcy`

## Opis

Refs #59.

Po zalogowaniu formularze logowania/resetu znikają, również po opóźnionych
odpowiedziach serwera. Klient nie widzi kontrolek przesyłania zdjęć.
Czerwone liczniki ulubionych, pozycji koszyka i aktualnych zamówień korzystają
z prywatnego podsumowania konta i odświeżają się po zmianach oraz powrocie do okna.
Wspólny formularz kontaktu i zgłoszeń jest zwinięty na dole strony.

„Blisko mnie” korzysta z zapisanej lokalizacji lub jawnego żądania GPS;
obsługuje odmowę, timeout, niedostępność i wymaganie HTTPS. Adapter Photon
korzysta z języka `default`, systemowego zaufania TLS i toleruje opcjonalne
puste pola wyników. Dodano diagnostykę różnic między minimalnym zapytaniem
a aplikacją na Windows, bez ujawniania sekretów.

Aktualne zamówienia sprzedawcy są grupowane według punktów odbioru;
każdy punkt jest początkowo zwinięty i renderuje po 20 wierszy na stronę.
Dostawy na adres są oddzielone; zachowano działania i PIN-y.

## Walidacja i odbiór

Wyniki: SQLite **4979 PASS / 0 FAIL / 109 SKIP**, PostgreSQL **106 PASS**,
Chromium **136 PASS + 2 PASS** oraz pięć szerokości HTTP PASS. Zestawy nakładają się.
Pełne raporty i sumy źródeł:
`docs/RAPORT_ISSUE_59_2026-11-13.md` i `docs/audits/issue59_20261113/`.
Testy obejmują prywatność kont, sesje, GPS, ulubione, koszyk, kontakty,
zamówienia, duże listy i rozmiary telefonu/tabletu/komputera.

Publiczny Photon jest blokowany przez proxy środowiska chmurowego;
test kontrolowany potwierdza poprawiony kontrakt, ale nie zastępuje diagnostyki
na Windows ani rzeczywistego telefonu. Ogólny kontakt e-mail wymaga istniejącej
konfiguracji SMTP; zapis zgłoszeń zakupowych działa niezależnie.

Instrukcja uruchomienia demo i plan aktualizacji/rollbacku VPS:
`docs/ISSUE_59_ODBIOR_I_VPS_2026-11-13.md`.
Brak nowych migracji SQL. Nie wdrażano na VPS ani nie włączano prawdziwych płatności.
