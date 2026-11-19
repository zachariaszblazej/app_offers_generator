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
Jednoczesne tworzenie dwóch elementów z tym samym Title (wyścig), `$filter` po kolumnie `Alias`, `PATCH` pola unikalnego
na zajętą wartość, `PATCH` nieistniejącego pola.
