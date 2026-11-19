# Testy SharePointBackend (offline i na żywo w DEV)

Dotyczy backendu `src/data/backends/sharepoint_backend.py` (odczyt, Clients CRUD, Suppliers CRUD, `set_default_supplier`).
Zachowanie Graph, na którym opiera się backend, opisuje [sharepoint-graph-behavior.md](./sharepoint-graph-behavior.md).
Backend SharePoint **nie jest** podłączony do fasady `database_service` - aplikacja nadal używa SQLite.

Polecenia uruchamia się z katalogu głównego projektu, w środowisku z `requirements.txt`. Pliki testów mają nazwy `*_test.py`
(wzorzec `test_*.py` jest w `.gitignore`), a pytest nie jest wymagany - używany jest `unittest`.

## Testy offline (bez sieci, bez logowania)

Wszystkie moduły (testy na żywo są w nich pomijane bez zmiennej środowiskowej, ale ich klasy offline - np. strażnicy - działają):

```powershell
python -m unittest tests.database_service_characterization_test tests.database_service_facade_test `
  tests.sharepoint_migration_test tests.sharepoint_backend_test tests.sharepoint_client_write_test `
  tests.sharepoint_infrastructure_test tests.sharepoint_supplier_write_test tests.sharepoint_supplier_default_test `
  tests.sharepoint_token_cache_test tests.sharepoint_backend_live_test tests.sharepoint_client_write_live_test `
  tests.sharepoint_supplier_live_test
```

| Moduł | Zakres |
|---|---|
| `database_service_characterization_test` | zachowanie SQLite (punkt odniesienia) |
| `database_service_facade_test` | fasada deleguje do `SqliteBackend`; publiczne API bez zmian |
| `sharepoint_migration_test` | migrator SQLite → SharePoint DEV |
| `sharepoint_backend_test` | odczyty `SharePointBackend`; zawiera `FakeGraph` (atrapa Graph z ETagami, 412/404/400, wstrzykiwanymi błędami) używany przez pozostałe testy |
| `sharepoint_client_write_test` | Clients: dodawanie, aktualizacja, pola dodatkowe, usuwanie, konflikty |
| `sharepoint_infrastructure_test` | pamięć ETagów `(lista, Title)`, zakres zapisu `GraphWriter`, `DELETE` z konkretnym ETagiem, `PartialFailureMessage` |
| `sharepoint_supplier_write_test` | `add_supplier`, `update_supplier`, `delete_supplier` |
| `sharepoint_supplier_default_test` | `set_default_supplier`, ostrzeżenie w `get_default_supplier` |
| `sharepoint_token_cache_test` | trwały cache tokenów MSAL (DPAPI) |
| `*_live_test` | testy na żywo (patrz niżej) oraz ich klasy offline sprawdzające strażników |

Testy offline nie wykonują żądań sieciowych. Aby to potwierdzić, można uruchomić je w procesie, który podmienia
`socket.socket.connect`, `socket.create_connection` i `requests.adapters.HTTPAdapter.send` na funkcje zgłaszające błąd i zlicza próby;
oczekiwany wynik to zero prób oraz kod wyjścia 0. Kod wyjścia testów należy odczytać od razu po uruchomieniu, osobno od sprzątania plików tymczasowych.
Testy nie dotykają prawdziwej bazy SQLite ani trwałego cache tokenów (cache jest wtedy tylko w pamięci).

## Testy integracyjne DEV

Wszystkie wymagają logowania MSAL w przeglądarce (istniejąca rejestracja Entra, bez client secret), aktywnego środowiska **DEV**
i są domyślnie pomijane. Raporty (bez tokenów) trafiają do `%APPDATA%\HantechDokumenty\migration\`, poza repozytorium.

| Test | Zmienna | Zakres |
|---|---|---|
| `tests.sharepoint_backend_live_test` | `HANTECH_LIVE_SP_TESTS=1` | **tylko odczyt**: zgodność 684 migrowanych rekordów z SQLite |
| `tests.sharepoint_client_write_live_test` | `HANTECH_LIVE_SP_WRITE_TESTS=1` | zapis Clients na rekordach `ZZTEST-` |
| `tests.sharepoint_supplier_live_test` | `HANTECH_LIVE_SP_SUPPLIER_TESTS=1` | zapis Suppliers i `set_default_supplier` na rekordach `ZZTEST-` |

```powershell
$env:HANTECH_LIVE_SP_SUPPLIER_TESTS = "1"
python -m unittest tests.sharepoint_supplier_live_test -v
Remove-Item Env:HANTECH_LIVE_SP_SUPPLIER_TESTS
```

Testy zapisu zmieniają dane w DEV, więc uruchamiaj je świadomie. Preflight przerywa test **bez zapisów**, gdy lista Suppliers nie zawiera
dokładnie jednego rekordu (prawdziwego dostawcy ID 1 z `IsDefault=True`) albo istnieją pozostałości `ZZTEST-` z poprzednich przebiegów.
Pozostałości trzeba usunąć ręcznie - test nigdy nie kasuje cudzych rekordów. Po uruchomieniu warto usunąć trwały cache tokenu
(`%LOCALAPPDATA%\HantechDokumenty\auth\msal_token_cache.bin`), jeśli nie ma być zachowany.

### Zabezpieczenia testów zapisu dostawców
* **Strażnik HTTP `SupplierWriteGuard`** blokuje żądanie *przed wysłaniem* (podmiana `requests.Session.request`). Dopuszcza wyłącznie:
  środowisko DEV i witrynę DEV (każdy identyfikator PROD jest blokowany); zapisy tylko na liście Suppliers;
  `POST` z syntetycznym `Title` (`999xxxxxxx`), `CompanyName` z prefiksem `ZZTEST-` i `IsDefault=false`;
  `PATCH`/`DELETE` wyłącznie dla ID z **rejestru rekordów utworzonych w bieżącym przebiegu** (rejestr jest tworzony od nowa, nic nie jest pamiętane z wcześniejszych testów);
  `PATCH` tylko na `/fields` i tylko z polami `CompanyName`, `AddressP1`, `AddressP2`, `IsDefault` (typu bool);
  `DELETE`/`PATCH` tylko z konkretnym ETagiem w `If-Match` (nigdy `*`, nigdy bez nagłówka).
* **ID 1 jest nietykalne**: strażnik blokuje je zawsze, nawet gdyby trafiło do rejestru.
* **`ScopedSupplierBackend`** (klasa wyłącznie testowa): `set_default_supplier` czyta całą listę, więc w testach zapisu widok Suppliers jest
  ograniczony do rejestru bieżącego przebiegu - prawdziwy dostawca jest dla algorytmu niewidoczny i nie może zostać odznaczony. Kod produkcyjny nie jest zmieniany.
  Offline (zawsze uruchamiane) test kontrolny dowodzi, że bez tego ograniczenia algorytm odznaczyłby ID 1, a strażnik zablokowałby takie żądanie.
* **Stan przed i po**: ETag, wersja, `IsDefault` i hash pól dostawcy ID 1, liczność list, ETagi pozostałych list oraz odcisk schematu czterech list.
  Wszystko musi być identyczne po teście.
* **Sprzątanie**: tylko rekordy z rejestru; przed każdym `DELETE` ponownie sprawdzane są ID, `Title` i ETag; bez dotykania kosza witryny.
  Sprzątanie działa także po nieudanym teście (`tearDownClass`).
* Test strażnika „na żywo” wysyła wyłącznie niegroźne żądania (nieistniejące ID, odczyt PROD) i potwierdza, że żadne nie zostało wysłane.

Testy zapisu klientów (`WriteGuard`) mają analogiczne zasady dla listy Clients: tylko DEV, tylko `ZZTEST-`, tylko ID z rejestru, konkretny `If-Match`.
