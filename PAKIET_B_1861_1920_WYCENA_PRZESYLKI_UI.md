# WiejskaPaka — B/1861–B/1920: wycena przesyłki w koszyku

W panelu koszyka dodano orientacyjną wycenę **wyłącznie dla wybranego rolnika**. Kwota pokazuje wartość produktów, jednorazowy koszt dostawy całej przesyłki oraz sumę. Zmiana rolnika lub trybu odbioru powoduje odświeżenie wyceny. Starsze odpowiedzi serwera nie mogą nadpisać nowszej wyceny. Zmiana sesji czyści podgląd. Wycena nie rezerwuje magazynu, a serwer ponownie weryfikuje kwoty przy składaniu zamówienia.

Zakres prac obejmuje `web/app.js`, `web/index.html` i test kontraktu interfejsu. Nie zmieniono połączeń produkcyjnych, płatności ani schematu Neon. Numeracja to zakres roboczy, nie liczba wdrożonych funkcji.
