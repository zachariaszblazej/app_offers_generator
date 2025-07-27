# Instrukcja ustawień aplikacji Generator Ofert

## 🏢 **Edytowalne dane firmy w ustawieniach:**

Aplikacja umożliwia edycję domyślnych danych firmy, które automatycznie wypełniają sekcję między miejscowością/datą a numerem oferty:

### 📝 **Dane firmy (edytowalne w ustawieniach):**
- **Miejscowość** - domyślna miejscowość dla ofert
- **Adres (linia 1)** - pierwszy wiersz adresu
- **Adres (linia 2)** - drugi wiersz adresu (kod + miasto)
- **NIP** - numer identyfikacji podatkowej
- **REGON** - numer w rejestrze REGON
- **Email** - adres email firmy
- **Telefon** - numer telefonu
- **Nazwa banku** - nazwa banku
- **Numer konta** - pełny numer konta bankowego

### 📋 **Produkty z jednostkami miary:**
- `{{product.pid}}` - ID produktu
- `{{product.pname}}` - Nazwa produktu
- `{{product.unit}}` - Jednostka miary (np. "szt.", "kg", "m")
- `{{product.qty}}` - Ilość
- `{{product.unit_price}}` - Cena jednostkowa
- `{{product.total}}` - Wartość całkowita

## 💡 **Przykład użycia w szablonie Word:**

```
{{town}}, {{date}}

Dane firmy:
{{address_1}}
{{address_2}}
NIP: {{nip}}
REGON: {{regon}}
Email: {{email}}
Tel: {{phone_number}}

Bank: {{bank_name}}
Konto: {{account_number}}

Numer oferty: {{offer_number}}

| Lp | Nazwa produktu | j.m. | Ilość | Cena jedn. | Wartość |
|----|----------------|------|-------|------------|---------|
{% for product in products %}
| {{loop.index}} | {{product.pname}} | {{product.unit}} | {{product.qty}} | {{product.unit_price}} zł | {{product.total}} zł |
{% endfor %}
```

## ⚙️ **Jak edytować domyślne wartości:**

1. **Uruchom aplikację**
2. **Kliknij przycisk "Ustawienia"** w menu głównym
3. **W sekcji "Domyślne dane firmy"** edytuj wszystkie pola:
   - Miejscowość, adres, NIP, REGON
   - Email, telefon, dane bankowe
4. **Kliknij "Zapisz ustawienia"**
5. **Nowe wartości będą używane** we wszystkich nowo tworzonych ofertach

## 🔄 **Automatyczne odświeżanie:**

Po zapisaniu ustawień, jeśli masz otwarte okno tworzenia oferty, dane firmy zostaną automatycznie odświeżone bez konieczności ponownego uruchamiania aplikacji.

## 💾 **Plik ustawień:**

Ustawienia są zapisywane w pliku `app_settings.json` w katalogu głównym aplikacji w formacie:

```json
{
    "company_data": {
        "town": "Wałbrzych",
        "address_1": "ul. Truskawiecka 14/4",
        "address_2": "58-301 Wałbrzych",
        "nip": "886-301-82-63",
        "regon": "520101773",
        "email": "g.ciesla@hantech.net.pl",
        "phone_number": "+48 796 996 912",
        "bank_name": "Pekao S.A.",
        "account_number": "37 1240 1952 1111 0011 3033 5600"
    }
}
```

## 🏢 **Edytowalne dane firmy w ustawieniach:**

Aplikacja umożliwia edycję domyślnych danych firmy, które automatycznie wypełniają sekcję między miejscowością/datą a numerem oferty:

### 📝 **Dane firmy (edytowalne w ustawieniach):**
- **Miejscowość** - domyślna miejscowość dla ofert
- **Adres (linia 1)** - pierwszy wiersz adresu
- **Adres (linia 2)** - drugi wiersz adresu (kod + miasto)
- **NIP** - numer identyfikacji podatkowej
- **REGON** - numer w rejestrze REGON
- **Email** - adres email firmy
- **Telefon** - numer telefonu
- **Nazwa banku** - nazwa banku
- **Numer konta** - pełny numer konta bankowego

### � **Dodatkowe zmienne sekcji oferty:**
- `{{offer_title}}` - Tytuł oferty (domyślnie: "OFERTA")
- `{{offer_subtitle}}` - Podtytuł oferty (domyślnie: "Propozycja współpracy handlowej")
- `{{offer_description}}` - Opis oferty (domyślnie: "Mając na uwadze Państwa potrzeby, przedstawiamy następującą ofertę:")
- `{{offer_terms}}` - Warunki realizacji (domyślnie: "Warunki realizacji zamówienia do uzgodnienia.")
- `{{offer_validity}}` - Ważność oferty (domyślnie: "Oferta ważna przez 30 dni od daty wystawienia.")

### 📋 **Produkty z jednostkami miary:**
- `{{product.pid}}` - ID produktu
- `{{product.pname}}` - Nazwa produktu
- `{{product.unit}}` - Jednostka miary (np. "szt.", "kg", "m")
- `{{product.qty}}` - Ilość
- `{{product.unit_price}}` - Cena jednostkowa
- `{{product.total}}` - Wartość całkowita

## 💡 **Przykład użycia w szablonie Word:**

```
{{offer_title}}
{{offer_subtitle}}

{{town}}, {{date}}

Dane firmy:
{{address_1}}
{{address_2}}
NIP: {{nip}}
REGON: {{regon}}
Email: {{email}}
Tel: {{phone_number}}

Bank: {{bank_name}}
Konto: {{account_number}}

Numer oferty: {{offer_number}}

{{offer_description}}

| Lp | Nazwa produktu | j.m. | Ilość | Cena jedn. | Wartość |
|----|----------------|------|-------|------------|---------|
{% for product in products %}
| {{loop.index}} | {{product.pname}} | {{product.unit}} | {{product.qty}} | {{product.unit_price}} zł | {{product.total}} zł |
{% endfor %}

{{offer_terms}}

{{offer_validity}}
```

## ⚙️ **Jak edytować domyślne wartości:**

1. **Uruchom aplikację**
2. **Kliknij przycisk "Ustawienia"** w menu głównym
3. **W sekcji "Domyślne dane firmy"** edytuj:
   - Miejscowość, adres, NIP, REGON
   - Email, telefon, dane bankowe
4. **W sekcji "Domyślne teksty sekcji oferty"** edytuj:
   - Tytuł, podtytuł, opis oferty
   - Warunki realizacji, ważność oferty
5. **Kliknij "Zapisz ustawienia"**
6. **Nowe wartości będą używane** we wszystkich nowo tworzonych ofertach

## 🔄 **Automatyczne odświeżanie:**

Po zapisaniu ustawień, jeśli masz otwarte okno tworzenia oferty, dane firmy zostaną automatycznie odświeżone bez konieczności ponownego uruchamiania aplikacji.

## 💾 **Plik ustawień:**

Ustawienia są zapisywane w pliku `app_settings.json` w katalogu głównym aplikacji w formacie:

```json
{
    "company_data": {
        "town": "Wałbrzych",
        "address_1": "ul. Truskawiecka 14/4",
        "address_2": "58-301 Wałbrzych",
        "nip": "886-301-82-63",
        "regon": "520101773",
        "email": "g.ciesla@hantech.net.pl",
        "phone_number": "+48 796 996 912",
        "bank_name": "Pekao S.A.",
        "account_number": "37 1240 1952 1111 0011 3033 5600"
    },
    "offer_section": {
        "title": "OFERTA",
        "subtitle": "Propozycja współpracy handlowej",
        ...
    }
}
```
