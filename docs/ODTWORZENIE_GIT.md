# Historia Git tego wydania

Archiwum ZIP zawiera komplet źródeł oraz `WiejskaPaka_git.bundle`.
Plik bundle przechowuje lokalne commity i nie zawiera ustawionego zdalnego
połączenia ani danych uwierzytelniających do GitHub.

Po wypakowaniu, w katalogu z plikiem bundle:

```bash
git bundle verify WiejskaPaka_git.bundle
git clone -b work/b10921-security WiejskaPaka_git.bundle WiejskaPaka-z-Git
```

Nie wykonano push do GitHub: połączenie nie uzyskało dostępu do wskazanego
repozytorium (404). To nie dowodzi, że repozytorium jest puste. Przed przyszłym
wysłaniem trzeba odczytać jego aktualny stan, sprawdzić prywatność i porównać
historię. Nie wolno nadpisać nieprzeczytanego zdalnego kodu ani zmienić widoczności.
W tej pracy nie uruchomiono GitHub Actions. Nie dodano workflowów.
