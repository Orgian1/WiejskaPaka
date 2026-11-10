# Pakiet B/10 — formularze mobilne i dostępność

- Dynamiczne pola adresu dostawy otrzymały dostępne nazwy dla czytników ekranu, podpowiedzi autouzupełniania oraz klawiaturę numeryczną dla kodu pocztowego.
- Wybór sposobu realizacji ma nazwę dostępną, a status wyboru jest ogłaszany przez czytnik ekranu.
- Pole PIN odbioru otrzymało nazwę i wzorzec sześciu cyfr; liczba sztuk otrzymała wskazówkę klawiatury numerycznej.
- Karty produktów i przyciski dostosowano do wąskich ekranów, z większymi polami dotykowymi i ochroną przed poziomym przewijaniem.
- Dodano trzy testy regresyjne. Sprawdzono składnię JavaScript oraz pełen zestaw testów na izolowanej SQLite: 2439 zaliczonych, 6 pominiętych, 16 podtestów.

Ograniczenia: testy statyczne nie zastępują przeglądarkowych testów dostępności ani ręcznego sprawdzenia na telefonie. Nie uruchamiano rzeczywistego PostgreSQL, nie zmieniano Neon ani wiejskapaka.pl, nie podłączano płatności.
