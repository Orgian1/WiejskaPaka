# WiejskaPaka B/2821–B/2880 — dalsza regresja

- Wznowiono regresję na izolowanych bazach SQLite.
- Poprawiono błąd raportowania: agregat grupy regresyjnej nie zawierał flagi `timeout`, choć pojedynczy test ją zapisywał.
- Zaktualizowano test sesji profilu rolnika, by uwzględniał czyszczenie niedokończonego checkoutu podczas zmiany użytkownika.
- Kontrola punktowa: 8 testów zaliczonych (test_regression_diagnostics_b116_b120.py, test_web_farmer_profile_session.py).
- W trakcie regresji: raporty częściowe, nie należy uznawać pełnej regresji za zakończoną.
- Bez zmian w Neon, domenie, hostingu i rzeczywistych płatnościach.
