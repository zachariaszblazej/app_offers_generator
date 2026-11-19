# Migracja SQLite → SharePoint DEV

> **Status: migracja do SharePoint DEV zakończona i zweryfikowana (2026-11-19).**
>
> - SharePoint **DEV zawiera migrowane dane** (684 rekordy).
> - Aplikacja **nadal korzysta wyłącznie z SQLite**. Migracja **nie oznacza** przełączenia aplikacji na SharePoint.
> - **PROD nie został zmodyfikowany** (na PROD wykonano wyłącznie odczyty schematu list).
> - Baza SQLite nie została zmieniona (hash przed i po migracji identyczny).

## Wynik końcowy

| Lista (SharePoint DEV) | Źródło (SQLite) | Przeniesiono | Zgodność pól |
|---|---|---|---|
| Suppliers | 1 | 1 | 100% |
| Clients | 39 | 39 | 100% |
| Offers | 417 | 417 | 100% |
| Wuzetkas | 227 | 227 | 100% |
| **Razem** | **684** | **684** | |

Migracja przebiegła etapami (Suppliers + Clients → Offers → Wuzetkas), każdy etap został zweryfikowany
przed przejściem do następnego. Brak błędów zapisu i brak duplikatów. Dane to migawka bazy
z 2026-11-18; dokumenty dodane w aplikacji później nie są w SharePoint.

## Cel i sposób działania

Migrator kopiuje zawartość czterech tabel SQLite do czterech list SharePoint (te same nazwy) przez
Microsoft Graph, z użyciem istniejącej rejestracji Entra ID i logowania MSAL (bez client secret).
Kod: `src/integrations/sharepoint/migration/`.

Kolejność: Suppliers → Clients → Offers → Wuzetkas. Zasady mapowania:

- `Title` w SharePoint jest **technicznym, unikalnym kluczem elementu**:
  - Suppliers i Clients: NIP jako 10-znakowy tekst z zerami wiodącymi,
  - Offers: `{numer}/OF/{rok}`,
  - Wuzetkas: `WZ_{numer}_{rok}`.
- `OfferFilePath`, `WzFilePath`, `OfferContext` i `WzContext` są przenoszone **bez zmian** (format i treść).
- Jedyna zmiana wartości: w `Clients.AddressP2` znak nowej linii jest zamieniany na `, `.
- Wartości NULL są pomijane. Dane historyczne nie są poprawiane ani normalizowane.
- Brak pliku dokumentu nie blokuje przeniesienia rekordu (jest tylko odnotowany w raporcie).

Migrator jest idempotentny: przed zapisem pobiera istniejące elementy list. Element identyczny jest
pomijany, element o tym samym `Title`, ale innych danych jest zgłaszany jako konflikt i **nigdy nie
jest nadpisywany**. Błędy 429/503 są ponawiane (Retry-After lub wykładniczy backoff), a błąd
pojedynczego rekordu nie przerywa migracji.

## Uruchamianie

Z katalogu głównego projektu (wymaga zainstalowanych zależności z `requirements.txt`; logowanie
interaktywne w przeglądarce):

```powershell
# Dry-run (domyślny tryb): tylko odczyty, zapisuje wyłącznie lokalny raport
python -m src.integrations.sharepoint.migration

# Zapis etapami - jawny wybór list i fraza potwierdzająca
python -m src.integrations.sharepoint.migration --execute --lists Suppliers,Clients --confirm MIGRATE-DEV
python -m src.integrations.sharepoint.migration --execute --lists Offers --confirm MIGRATE-DEV
python -m src.integrations.sharepoint.migration --execute --lists Wuzetkas --confirm MIGRATE-DEV

# Test zapisu jednego syntetycznego rekordu w Clients (utwórz, odczytaj, usuń, zweryfikuj)
python -m src.integrations.sharepoint.migration --synthetic-test --confirm SYNTHETIC-TEST-DEV
```

Opcjonalnie: `--db <ścieżka>` (domyślnie baza z ustawień aplikacji), `--report-dir <katalog poza projektem>`,
`--allow-errors` (przy `--execute` pomija rekordy błędne zamiast odmówić).

Zapis (`--execute`) odmawia działania, gdy: brak `--lists` lub frazy `--confirm`, brak raportu
dry-run, **hash bazy SQLite różni się od ostatniego dry-runu**, dry-run lub plan zawiera błędy.
Po zapisie migrator ponownie czyta listy i porównuje liczbę elementów oraz każde pole ze źródłem.

## Zabezpieczenia

- **Wyłącznie DEV.** Migrator nie ma opcji wyboru środowiska. Przerywa, gdy aktywne środowisko to PROD,
  gdy Site ID lub adres witryny nie odpowiada DEV albo gdy konfiguracja DEV zawiera identyfikatory PROD
  (`migration/guard.py`; identyfikator witryny DEV jest tam zapisany niezależnie od `config.py`).
  Przed pracą weryfikowane są też witryna i listy przez Graph. Guard jest sprawdzany przed każdym żądaniem zapisu.
- **SQLite tylko do odczytu:** `mode=ro` + `PRAGMA query_only=ON`; SHA-256, rozmiar i czas modyfikacji
  pliku są porównywane przed i po operacji.
- **Zapis ograniczony:** jedyne operacje zapisu to utworzenie elementu (`POST`) na czterech listach DEV oraz
  usunięcie elementu testowego. Usuwanie działa wyłącznie na liście Clients, po numerycznym Item ID i tylko
  gdy `Title` elementu ma prefiks `ZZTEST-` i jest identyczny z oczekiwanym.
- Tokeny nie są logowane ani zapisywane na dysku (cache MSAL tylko w pamięci).

## Lokalizacje danych (poza repozytorium)

Wszystko poniżej leży w katalogu danych aplikacji, `%APPDATA%\HantechDokumenty\migration\`, i **nie
jest częścią repozytorium**:

| Zawartość | Ścieżka |
|---|---|
| Mapa kluczy SQLite → Item ID SharePoint (DEV) | `id_map_DEV.json` |
| Raporty dry-run | `dryrun_<data>.txt` / `.json` |
| Raporty zapisu (etapy) | `execute_<data>.txt` / `.json` |
| Raport testu syntetycznego | `synthetic_test_<data>.txt` / `.json` |
| Kopia bezpieczeństwa SQLite (tylko do odczytu, sprawdzona hashem) | `backup\` |

Raporty maskują dane firm. **Migrator odmawia zapisu raportów, mapy ID i innych danych migracyjnych do
katalogu repozytorium projektu i jego podkatalogów** (`migration/datadir.py`). Dotyczy to także
`--report-dir`; ścieżka jest normalizowana (ścieżki względne, `..`, dowiązania/junctiony, wielkość liter
na Windows), więc nie da się tego obejść. Sprawdzenie odbywa się przed jakąkolwiek pracą oraz przy
każdym zapisie raportu i mapy ID. Domyślna lokalizacja w `%APPDATA%` działa bez zmian.

## Testy

```powershell
python -m unittest tests.sharepoint_migration_test -v
```

40 testów offline (bez sieci): mapowanie (w tym aliasy różniące się wielkością liter), walidacja, guard DEV/PROD,
ponawianie 429/503, idempotencja, konflikty, blokada przy zmianie hasha, dry-run bez zapisów, ograniczenie
usuwania oraz walidacja katalogu danych (poza repozytorium).

## Czego ta migracja nie zmienia

Aplikacja (`src/data/database_service.py` i logika biznesowa) nadal czyta i zapisuje dane w SQLite.
Przełączenie aplikacji na SharePoint, operacje CRUD na listach, migracja do PROD oraz ewentualna
migracja dokumentów dodanych po 2026-11-18 to osobne etapy.
