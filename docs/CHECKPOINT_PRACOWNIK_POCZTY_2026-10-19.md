# Checkpoint ograniczonego procesu kolejki — 19.10.2026

Kod: f4ddd02a63b2ee3361352626e8e1d2b3d88d6bdd.
Gałąź: preview/bounded-reset-worker-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/13
Baza PR: preview/queued-reset-http-v2-20261019 (roboczy PR #12).
CI pracownika: https://github.com/Orgian1/WiejskaPaka/actions/runs/39255687395

## Wykonany zakres

Dodano jawnie wywoływany proces spawn z limitem 1–25 prób pobrania i czasu
1–60 sekund. Po przekroczeniu czasu stosuje sygnał zatrzymania i kończy
proces. Wynik zawiera wyłącznie stałe kody oraz liczniki; błędy i timeout
nie twierdzą, że transport niczego nie przyjął. Trwałe dzierżawy i znaczniki
kolejki zachowują rozróżnienie między nierozpoczętym a niepewnym zadaniem.

Dziewiętnaście lokalnych przypadków obejmuje rzeczywisty proces potomny,
limity, brak zadań, timeout przed połączeniem i po znaczniku rozpoczęcia,
odmowę ponownej wysyłki niepewnego zadania, błędy transportu/serializacji,
zamknięcie dzieci, ukrycie prywatnych danych i walidację wyniku.
Nowy scenariusz natywny uruchamia proces z ograniczoną rolą PostgreSQL
i transportem w pamięci. Bramka wymaga teraz co najmniej 41 zaliczeń.

## Potwierdzone wyniki badanego kodu

| Kontrola | Wynik |
| --- | --- |
| Lokalny pakiet powiązanych modułów | 112 PASS, 0 FAIL, 37 SKIP (brak lokalnego PostgreSQL) |
| Ostatni przebieg modułu procesu | 19 PASS, 0 FAIL |
| Natywny PostgreSQL 16 | 41 PASS, 0 FAIL, 0 SKIP |
| Chromium | 36 PASS, 0 FAIL, 0 SKIP; HTTP w pięciu rozmiarach: sukces |
| Szybki Windows | 80 PASS, 0 FAIL, 0 SKIP |
| Pełny Windows pracownika | 3950 PASS, 0 FAIL, 120 SKIP; sukces |

Lokalne przebiegi nakładają się — nie sumować. Raporty trzech zakończonych
bramek: `audits/bounded_worker_f4ddd02_2026-10-19/`. Zweryfikowano SHA-256
archiwów CI, zgodność pełnego zestawu odcisków źródeł/testów/zależności
z lokalnym drzewem oraz success, complete i sources_unchanged.
Provenance zapisuje badany commit, identyfikator przebiegu i artefaktu.
Zdalne drzewo kodu zgadzało się z lokalnym git: d71871a321793d5b92dca70e17bd2b91c5177403.

## Stan poprzedniego pakietu

Aktualizacja 19.10.2026, po 17:08 Europe/Warsaw: pełny Windows kodu HTTP,
przebieg 39253492205, zakończył się sukcesem: 3931 PASS, 0 FAIL, 119 SKIP.
Pełny Windows pracownika również zakończył się sukcesem: 3950 PASS,
0 FAIL, 120 SKIP. Raporty windows.json i ich provenance pobrano i
zweryfikowano względem odcisków PostgreSQL tego samego badanego commita.
Raporty poprzednich zakończonych bramek dotyczą kodu 88c4cad, a nie pracownika.

## Granice i dalsza praca

Pracownik nie jest uruchamiany przez API, usługę systemową ani harmonogram.
Nie ma domyślnego SMTP lub połączenia z bazą; wszystkie funkcje dostarcza
jawnie wywołujący. Testy nie wysyłają prawdziwej poczty. Ograniczenia procesu
nie stanowią systemowej izolacji uprawnień lub sieci.

Oba wyniki pełnego Windows zostały odebrane; success, complete oraz
sources_unchanged są prawdziwe. Pominięcia pozostają pominięciami, nie
zaliczeniami natywnych testów innych środowisk. Nie sumować wyników
nakładających się przebiegów.

Następnie: osobna rola i konto usługi, uprawnienia i nadzorca procesu,
retencja metadanych, potwierdzanie adresów, kopie/rotacja kluczy i bezpieczne
odtworzenie oraz osobny odbiór dostawcy poczty i DNS.
Nie scalono PR #12 ani #13. Hosting i rzeczywiste płatności pozostają odłączone.
