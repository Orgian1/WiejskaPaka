# Ochrona historii zgłoszeń po zmianie widoku — 18.10.2026

Punkt wznowienia: `23d29c8f254e8ba85b846f5762e7f29cb0c92ef2`,
gałąź `wiejskapaka-import`, zapis 12:51 czasu Polski.

## Zmiana

Przycisk wcześniejszych wpisów sprawdza sesję, generację widoku, numer
bieżącego żądania szczegółów i obecność widoku przed wysłaniem żądania.
Zachowana kontrolka z poprzedniej sprawy lub sesji nie wysyła już żądania
przy użyciu bieżącego konta. Istniejące sprawdzenie po odpowiedzi pozostaje.
Autoryzacja serwera i zasady rozliczeń pozostają bez zmian.

## Weryfikacja

- Dwa nowe scenariusze: uruchomienie starej kontrolki po zmianie sesji
  oraz po otwarciu innej sprawy. Oba wymagają braku nowego żądania.
- Test po stronie Python wymaga teraz zarówno kodu zakończenia 0,
  jak i jawnego znacznika PASS z wykonanego scenariusza JavaScript.
- Kontrolowane uruchomienie testu z dawnym warunkiem, bez zmiany plików,
  zakończyło się błędem: stare sterowanie wysłało drugie żądanie zamiast
  zachować licznik 1. Potwierdza to odtwarzanie regresji.
- Bieżący zestaw celowany: 31 zaliczonych, 0 błędów, 0 pominiętych:
  `test_support_cases_ui.py`, `test_support_cases_http.py`,
  `test_catalog_page_ui.py`. Obejmuje rzeczywiste HTTP testowego zakupu,
  role, ponowienia i brak skutków finansowych zgłoszenia.

Pełna regresja Linux nowego zestawu: 313/313 modułów, 3802 zaliczone,
0 błędów, 40 pominiętych, razem 3842 przypadki. Raport potwierdza
`complete`, `success` i `sources_unchanged`. Oczyszczony zapis:
`audits/support_history_linux_2026-10-18.json`. Zestaw celowany jest
podzbiorem pełnej regresji; liczników nie dodaje się do siebie.
Pominięcia obejmują opcjonalne środowiska natywne. Ten wynik nie zastępuje
Windows, PostgreSQL ani rzeczywistego Chromium dla nowego commitu. Nie uruchamiano integracji produkcyjnych,
płatności, rzeczywistej poczty ani zewnętrznych baz danych.
