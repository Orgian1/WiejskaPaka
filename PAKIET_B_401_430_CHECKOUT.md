# WiejskaPaka B/401–430 — testowy zakup zapisanego koszyka

Nowy endpoint `POST /cart/checkout-test` tworzy atomowo oddzielne zamówienie dla każdej pozycji koszyka jednego rolnika. Ponownie sprawdza ceny i stany magazynowe, aktualizuje magazyn, zapisuje zdarzenia, czyści koszyk dopiero po sukcesie. Przy błędzie transakcja jest wycofywana.

Ograniczenia: koszyk może zawierać produkty tylko jednego rolnika; dostawa jest liczona osobno dla każdej pozycji (jak w dotychczasowym modelu zamówienia) i wyraźnie komunikowana. Nie ma wspólnego zamówienia wielopozycyjnego, płatności ani prawdziwego przelewu. PIN w odpowiedzi jest WYŁĄCZNIE TESTOWY. Weryfikacja PostgreSQL/Neon i testy end-to-end pozostają do wykonania.
