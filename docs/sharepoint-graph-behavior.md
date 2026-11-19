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
