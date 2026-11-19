# Zachowanie SharePoint Lists przez Graph API (zweryfikowane na DEV)

Wyniki testów technicznych z 2026-11-19 na witrynie DEV (lista Clients, dane syntetyczne `ZZTEST-`, istniejąca
rejestracja Entra, uprawnienie `Sites.Selected` z rolą `write`). Wszystkie testowe elementy zostały usunięte
po ID; schemat listy, indeksy i uprawnienia nie były zmieniane. Dokument opisuje fakty, na których opiera się
`SharePointBackend`.

## Operacje na elementach
| Operacja | Żądanie | Wynik |
|---|---|---|
| Utworzenie | `POST …/items` z `{"fields": {...}}` | **201**, nagłówek `Location`, ETag `"<guid>,1"` |
| Aktualizacja | `PATCH …/items/{id}/fields` z samymi zmienianymi polami | **200**, odpowiedź to zaktualizowane pola, nowy ETag w nagłówku `ETag` i w `@odata.etag` |
| Usunięcie | `DELETE …/items/{id}` | **204** (element trafia do kosza witryny); kolejny `GET` → **404** `itemNotFound` |
| Odczyt po filtrze | `GET …/items?$filter=fields/Title eq '…'&$expand=fields($select=…)` | działa także dla wartości z `/`; porównanie **nie rozróżnia wielkości liter**; działa `startswith(...)` |

- **Identyfikatory elementów nie są używane ponownie** (po usunięciu elementu o ID 1 kolejne elementy dostają wyższe numery).
- **Wersjonowanie:** każda zmiana (`PATCH`) tworzy nową wersję elementu (`_UIVersionString` rośnie), co zwiększa zużycie miejsca przy częstych aktualizacjach.

## ETag i współbieżność
- ETag ma postać `"<guid>,<wersja>"`; wersja rośnie o 1 przy każdej zmianie. Zwracany jest w treści (`eTag`, `@odata.etag`) i w nagłówku `ETag`.
- `PATCH` bez `If-Match`: zapis bez sprawdzania (wygrywa ostatni).
- `PATCH` z aktualnym `If-Match`: **200**.
- `PATCH` z nieaktualnym `If-Match`: **412**, `code: "resourceModified"`, element **niezmieniony**.
- `PATCH` z `If-Match: *`: **200** (bez sprawdzania wersji).

## Czyszczenie pól
`{"Pole": null}` i `{"Pole": ""}` dają ten sam skutek: po odczycie klucza pola **nie ma w odpowiedzi** (brak = NULL/pusty).
Odczyt musi więc traktować brak klucza jak pustą wartość.

## Unikalność
Utworzenie elementu z wartością zajętą w kolumnie unikalnej (Title albo Alias) kończy się:

**HTTP 400**, `code: "invalidRequest"`, `message: "One or more fields with unique constraints already has the provided value."`

- To **nie jest 409** i odpowiedź **nie wskazuje, które pole koliduje**.
- Unikalność **nie rozróżnia wielkości liter** (`ZZTEST-…` i `zztest-…` kolidują).
- Komunikaty błędów per pole (np. „Klient z tym NIP już istnieje”) wymagają odczytu po `$filter` przed zapisem.

## Niezweryfikowane
Jednoczesne tworzenie dwóch elementów z tym samym Title (wyścig) oraz `$filter` po kolumnie `Alias`.

## Uzupełnienie (etap 4A, 2026-11-19, DEV, lista Clients, dane `ZZTEST-`)

| Fakt | Wynik |
|---|---|
| ETag w odczycie kolekcji | `@odata.etag` jest w każdym elemencie `GET …/items`, także przy `$select=id` i `$expand=fields(...)`; ma tę samą postać `"<guid>,<wersja>"` co ETag z odpowiedzi `POST`/`PATCH` i działa w `If-Match` |
| Pola wymagane (`required=true`: Title, CompanyName, AddressP1, AddressP2, Alias) | Graph **nie wymusza** ich przy `POST` ani `PATCH`: brak pola, `""` i `null` są przyjmowane i dają brak klucza przy odczycie |
| Czyszczenie pola przez `PATCH` | `{"AddressP2": null}` i `{"AddressP2": ""}` usuwają wartość (klucz znika z odpowiedzi) |
| Nowa linia w polu jednoliniowym (AddressP2) | Graph ją przyjmuje; aplikacja i tak zapisuje AddressP2 bez nowych linii (jak migracja: `, `) |
| `PATCH` pola unikalnego na zajętą wartość | **400 `invalidRequest`**, ten sam komunikat o unikalności co przy `POST`; także dla aliasu różniącego się wielkością liter |
| `PATCH` nieistniejącego pola | 400 `invalidRequest`: `Field '<nazwa>' is not recognized` |
| `PATCH` / `DELETE` nieistniejącego ID | **404** `itemNotFound` |
| `PATCH` z nieaktualnym `If-Match` | **412** `resourceModified`: „The resource has changed since the caller last read it; usually an eTag mismatch”; element niezmieniony |
| Ponowne użycie NIP i aliasu po usunięciu elementu | działa (kosz witryny nie blokuje unikalności) |
| Nieudany `POST` (400) | zużywa numer ID (kolejny element dostaje wyższe ID) |

### Konsekwencje dla `SharePointBackend` (zapis klientów)
* Zapis idzie wyłącznie przez `GraphWriter` (DEV-only, tylko lista Clients, ID elementu wyłącznie cyfry, `PATCH` tylko z konkretnym `If-Match`).
* Kolizje NIP i aliasu są wykrywane odczytem przed zapisem (z `casefold`); konflikt wykryty dopiero przez `POST`/`PATCH` (400 bez wskazania pola)
  jest rozstrzygany odczytem weryfikującym.
* Backend pamięta ETag klienta z ostatniego odczytu (`get_clients`, `get_client_by_nip`) lub własnego zapisu i używa go w `If-Match`;
  przy 412 zapis nie jest ponawiany, a wynik to `(False, ConflictMessage)` (podklasa `str`, `isinstance(msg, ConflictMessage)`).
* Ponawiany jest wyłącznie HTTP 429 (do 3 prób, `Retry-After` do 30 s). Po 5xx i po błędzie połączenia zapis nie jest ponawiany;
  po niejednoznacznym `POST` odczyt weryfikujący sprawdza, czy element powstał.
* Puste pola (`""`, `None`) nie są wysyłane przy tworzeniu, a przy aktualizacji są czyszczone; odczyt zwraca `''` (jak SQLite).
* Zmiana bez różnic nie wysyła żądania (każdy `PATCH` tworzy nową wersję elementu).
* Aktualizacja i zapis pól dodatkowych nieistniejącego klienta (brak przy odczycie albo 404 z `PATCH`) zwracają
  `(False, "Klient nie został znaleziony")` - świadoma różnica względem SQLite, który zwraca cichy sukces.

## Uzupełnienie (etap 4B, 2026-11-19, DEV, lista Suppliers, dane `ZZTEST-`)

Lista Suppliers: `Title` (NIP; unikalny, zindeksowany), `CompanyName`, `AddressP1`, `AddressP2` (tekst do 255 znaków)
oraz `IsDefault` (Tak/Nie, niewymagane, wartość domyślna kolumny „0”, **niezindeksowane**).

### Fakty zmierzone sondą 4B-0
| Fakt | Wynik |
|---|---|
| `DELETE` z aktualnym ETagiem w `If-Match` | **204** |
| `DELETE` z nieaktualnym ETagiem | **412** `resourceModified`; element **nie** został usunięty |
| `DELETE` z `If-Match: *` albo bez `If-Match` | 204 (Graph nie sprawdza wersji) - dlatego aplikacja **zawsze** wysyła konkretny ETag |
| `PATCH` `IsDefault=true` / `false` | wartość jest zwracana jawnie |
| `PATCH` `IsDefault=null` | klucz **znika** z odpowiedzi (stan nieokreślony) - aplikacja nigdy nie wysyła `null` dla `IsDefault` |
| `POST` bez `IsDefault` | `IsDefault=false` (wartość domyślna kolumny) |
| `POST` z zajętym `Title` | 400 `invalidRequest` (jak w Clients) |
| Ponowne użycie NIP po usunięciu | działa (kosz witryny nie blokuje unikalności) |
| `$filter` po `IsDefault` | 400 - filtr jest wykonywany po stronie klienta |

### Konsekwencje dla `SharePointBackend` (dostawcy)
* Zapis dostawców idzie wyłącznie przez `GraphWriter` (DEV-only; dozwolone listy: Clients i Suppliers; Offers, Wuzetkas, inne listy i PROD są blokowane).
* **`add_supplier`**: przed `POST` sprawdza format i zajętość NIP (odczyt po `Title`, bez rozróżniania wielkości liter). Duplikat kończy się
  `(False, "Dostawca z tym NIP już istnieje w bazie")` bez `POST`. Tworzy rekord z `Title`, `CompanyName`, `AddressP1`, `AddressP2`
  (puste pola nie są wysyłane) i zawsze `IsDefault=false`. Po 400 o unikalności odczyt weryfikujący rozstrzyga, czy NIP jest zajęty.
  Po utraconej odpowiedzi lub błędzie 5xx/sieci odczyt po NIP ustala wynik: rekord z naszymi danymi i `IsDefault=false` oznacza sukces,
  rekord z innymi danymi - duplikat, brak rekordu - błąd. **`POST` nigdy nie jest ponawiany.**
* **`update_supplier`**: znajduje dostawcę po dokładnym NIP; zmienia tylko `CompanyName`, `AddressP1`, `AddressP2` (nigdy `Title` ani `IsDefault` -
  `IsDefault` nie należy do dozwolonych pól `PATCH`). Brak dostawcy lub 404 → `(False, "Dostawca nie został znaleziony")`. Zmiana bez różnic nie wysyła
  żądania. Po niejednoznacznej odpowiedzi odczyt weryfikujący ustala, czy zmiana została zapisana (nie ma ponowienia w ciemno).
* **`delete_supplier`**: odmawia usunięcia dostawcy domyślnego (`"Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślnego."`).
  Przed `DELETE` ponownie odczytuje element po ID i sprawdza `Title` oraz `IsDefault`, a ETag z tego odczytu trafia do `If-Match`.
  404 → „Dostawca nie został znaleziony”; po 5xx lub błędzie sieci nie ma kolejnego `DELETE`. Usunięcie dostawcy nie wybiera nowego domyślnego.
* **`get_default_supplier`**: filtr `IsDefault` po stronie klienta; przy kilku domyślnych zwraca pierwszego wg ID i loguje wyłącznie ID elementów
  (odczyt niczego nie naprawia).
* Pamięć ETagów jest kluczowana parą `(lista, Title)`, więc ten sam NIP w Clients i Suppliers ma niezależne wpisy (odczyt dostawców nie nadpisze ETagu klienta i odwrotnie).
  Wpis jest odrzucany po 412, 404 i po każdym niejednoznacznym zapisie.

### `set_default_supplier` - brak transakcji obejmującej wiele elementów
Graph nie zapewnia transakcji na wielu elementach, a dwa `PATCH` nie są atomowe. Dlatego algorytm jest zaprojektowany tak, aby przerwanie w dowolnym
miejscu nigdy nie zostawiało stanu „brak domyślnego dostawcy”:

1. **A - świeży odczyt** całej listy z ETagami (nigdy z pamięci ETagów). Brak NIP → `(False, "Dostawca nie został znaleziony")` bez zapisów.
   Wskazany dostawca jest już jedynym domyślnym → sukces bez żadnego zapisu (idempotencja).
2. **B - ustawienie wskazanego**: `PATCH IsDefault=true` z ETagiem z odczytu (pomijane, jeśli już jest domyślny).
3. **C - odznaczenie pozostałych**: `PATCH IsDefault=false` na każdym innym domyślnym, w kolejności ID, z jego własnym ETagiem. Dzięki temu naprawiany jest też stan z kilkoma domyślnymi.
4. **D - odczyt weryfikujący**: sukces dopiero, gdy świeży odczyt pokazuje dokładnie jednego domyślnego - wskazanego.

| Sytuacja | Wynik | Stan SharePoint / odzyskiwanie |
|---|---|---|
| 412 lub 404 przy kroku B | `(False, ConflictMessage)` / „Dostawca nie został znaleziony” | nic nie zmieniono |
| Błąd 5xx/sieci przy kroku B | odczyt flagi wskazanego rozstrzyga; jeśli nadal nieustalone - `PartialFailureMessage` | stan nieznany; ponowne wywołanie jest bezpieczne |
| Błąd przy kroku C (412, 5xx, sieć), flaga poprzedniego domyślnego nadal ustawiona | `(False, PartialFailureMessage)` z nazwą wskazanego, poprzedniego i liczbą pozostałych | wskazany jest domyślny, ale istnieje więcej niż jeden domyślny |
| Poprzedni domyślny usunięty lub już odznaczony (404, odczyt potwierdza) | traktowane jako odznaczony | brak problemu |
| Krok D: odczyt się nie udał, wskazany usunięty, kilku domyślnych | `(False, PartialFailureMessage)` | odświeżyć listę i ponowić |
| Krok D: wskazany nie jest już domyślny (ktoś zmienił w międzyczasie) | `(False, ConflictMessage)` | odświeżyć listę i ponowić |

`PartialFailureMessage` (`src/data/errors.py`, podklasa `str` z `partial=True`, jak `ConflictMessage`) oznacza „część zmian została wykonana”. Backend **nigdy nie zgłasza sukcesu
przy niespójnym stanie**, a komunikat dla użytkownika zawsze mówi, co jest ustawione, i prosi o odświeżenie listy oraz ponowne ustawienie dostawcy - ta operacja naprawia stan.
Żaden z kroków nie jest ponawiany automatycznie (poza HTTP 429).

### Ograniczenia współbieżności
* `If-Match` chroni każdy pojedynczy element, ale **nie** całą operację: między krokami A, B i C inny użytkownik może zmienić listę. Skutki są wykrywane
  (412, krok D), a nie zapobiegane. Najgorszy możliwy wynik to czasowo kilku domyślnych dostawców, które naprawia ponowne ustawienie domyślnego.
* Odczyt `get_default_supplier` w trakcie operacji może zobaczyć stan przejściowy (dwóch domyślnych).
* Dwa jednoczesne `POST` z tym samym NIP rozstrzyga unikalność `Title` po stronie SharePoint (jeden zwróci 400); sam wyścig nie był testowany.
* `DELETE`, `PATCH` i `POST` nie są transakcyjne względem odczytu poprzedzającego: ETag zamyka tylko okno pojedynczego elementu.
* Usunięty element trafia do kosza witryny (aplikacja go nie dotyka); każdy `PATCH` tworzy nową wersję elementu.
* Backend SharePoint nie jest podłączony do fasady `database_service` - aplikacja nadal używa wyłącznie SQLite.

### Różnice względem SQLite (dostawcy)
* Komunikaty tekstowe i krotki wyników są takie same jak w `SqliteBackend` (m.in. „Dostawca nie został znaleziony”, odmowa usunięcia domyślnego).
* SQLite zmienia domyślnego w jednej transakcji (najpierw zeruje wszystkie flagi, potem ustawia wskazaną). SharePoint nie ma takiej transakcji, więc kolejność jest odwrotna
  (najpierw wskazany, potem reszta - patrz wyżej) i pojawiają się wyniki `ConflictMessage` oraz `PartialFailureMessage`, których SQLite nie zwraca.
* Konflikt wersji (412) przy aktualizacji, usunięciu i zmianie domyślnego zwraca `ConflictMessage`; SQLite nie wykrywa współbieżnych zmian.
* NIP porównywany jest dokładnie jako 10-znakowy tekst z zerami wiodącymi; unikalność `Title` w SharePoint nie rozróżnia wielkości liter.
* Pola tekstowe dostawców są odczytywane jako `''`, gdy ich nie ma (`None` nie trafia do wywołującego); `AddressP2` dostawcy nie zamienia nowych linii.
