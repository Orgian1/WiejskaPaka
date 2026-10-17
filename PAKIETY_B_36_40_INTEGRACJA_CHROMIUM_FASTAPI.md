# WiejskaPaka — pakiety B/36–B/40: Chromium + rzeczywisty backend

## Co jest testowane

`python -m scripts.check_browser_backend_bridge`

- **B/36:** rejestracja, logowanie i wylogowanie rolnika i klienta przez interfejs Chromium i prawdziwe endpointy FastAPI.
- **B/37:** utworzenie produktu (349 groszy, opłata dostawy 501 groszy) i punktu odbioru przez formularze rolnika.
- **B/38:** złożenie zamówienia z odbiorem osobistym i kontrola sumy 349 groszy.
- **B/39:** zamówienie z dostawą i kontrola sumy 850 groszy.
- **B/40:** wylogowanie, wyczyszczenie zamówień i ukrycie prywatnych paneli; kontrola błędów JS i poziomego przewijania.

Wykonany scenariusz przesyła żądania z Chromium do **rzeczywistej aplikacji FastAPI**, używając funkcji mostu Playwright i `TestClient`. Nie używa fikcyjnych odpowiedzi API. Baza SQLite jest tworzona w katalogu tymczasowym, a konfiguracja PostgreSQL jest usuwana przed importem aplikacji.

## Granice testu

To **nie jest** rzeczywista komunikacja sieciowa Chromium–serwer HTTP. Most zastępuje `window.fetch`, ponieważ w środowisku testowym dostęp Chromium do localhost jest blokowany. Nie testuje proxy, TLS, CORS, ciasteczek, rzeczywistego serwera PostgreSQL, RLS ani płatności produkcyjnych. Nie zastępuje testów na fizycznym telefonie. Nie modyfikuje Neon ani wiejskapaka.pl.

## Uruchamianie

Z katalogu projektu:

```bash
python -m scripts.check_browser_backend_bridge
python -m pytest -q
```

Wymaga Playwright i zainstalowanego Chromium. Przy braku Chromium test integracyjny jawnie kończy się błędem, a nie pozornym sukcesem.
