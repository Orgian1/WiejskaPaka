# Pakiet B/16 — raporty bez wyścigów odpowiedzi

- Panel rolnika: pobrany raport wypłat testowych (również komunikat o błędzie) jest wyświetlany wyłącznie dla najnowszego odświeżenia panelu i bieżącej sesji.
- Panel administratora: identyfikator kolejnego żądania raportu finansowego zapobiega nadpisaniu nowszego raportu przez opóźnioną odpowiedź starszego żądania. Walidacja miesiąca dopuszcza tylko 01–12.
- Dodano dwa testy regresyjne i zaktualizowano dwa starsze testy zgodnie z silniejszą ochroną.
- Wynik lokalny: 2452 zaliczone, 6 pominiętych, 16 podtestów zaliczonych. Testy PostgreSQL wymagające serwera nadal pominięte.
- Bez zmian w Neon, publicznej stronie i płatnościach rzeczywistych.
