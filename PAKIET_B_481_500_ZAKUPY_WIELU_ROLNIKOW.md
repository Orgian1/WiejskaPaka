# B/481–B/500 — wybór rolnika przy finalizacji koszyka
- Dodano opcjonalny `farmer_id` do testowego checkoutu.
- Checkout realizuje atomowo tylko pozycje wybranego rolnika; pozostałe zostają w koszyku.
- Bez `farmer_id` zachowano dotychczasowe zachowanie.
- Interfejs umożliwia wybór rolnika i pobiera jego punkty odbioru.
- Opłata za dostawę nadal naliczana osobno dla każdej pozycji.
- Brak rzeczywistych płatności i wdrożenia Neon.
- Testy należy uruchamiać osobno: część starszych modułów ustawia bazę testową globalnie przy imporcie.
