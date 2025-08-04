# Zrefaktoryzowana struktura aplikacji Apka Oferty

## Nowa struktura folderów

```
src/
├── __init__.py
├── core/                     # Główna logika aplikacji
│   ├── __init__.py
│   ├── main_app.py          # Główna klasa aplikacji
│   ├── navigation_manager.py # Manager nawigacji między ramkami
│   └── offer_generator_app.py # Główna logika generowania ofert
├── data/                     # Warstwa dostępu do danych
│   ├── __init__.py
│   └── database_service.py  # Operacje na bazie danych
├── services/                 # Logika biznesowa
│   ├── __init__.py
│   └── offer_generator_service.py # Serwis generowania ofert
├── ui/                       # Interfejs użytkownika
│   ├── __init__.py
│   ├── components/          # Komponenty wielokrotnego użytku
│   │   ├── __init__.py
│   │   ├── product_table.py # Tabela produktów
│   │   └── ui_components.py # Główne komponenty UI
│   ├── frames/              # Ramki aplikacji (różne ekrany)
│   │   ├── __init__.py
│   │   ├── browse_clients_frame.py
│   │   ├── browse_suppliers_frame.py
│   │   ├── main_menu_frame.py
│   │   ├── offer_creation_frame.py
│   │   └── settings_frame.py
│   └── windows/             # Okna modalne i dialogi
│       ├── __init__.py
│       ├── client_search_window.py
│       ├── product_add_window.py
│       └── supplier_search_window.py
└── utils/                   # Funkcje pomocnicze
    ├── __init__.py
    ├── config.py            # Konfiguracja aplikacji
    └── settings.py          # Zarządzanie ustawieniami
```

## Opis komponentów

### Core (`src/core/`)
- **main_app.py**: Główna klasa aplikacji `OfferGeneratorMainApp`
- **navigation_manager.py**: Klasa `NavigationManager` zarządzająca nawigacją
- **offer_generator_app.py**: Klasa `OfferGeneratorApp` z logiką tworzenia ofert

### Data (`src/data/`)
- **database_service.py**: Wszystkie funkcje operujące na bazie danych SQLite

### Services (`src/services/`)
- **offer_generator_service.py**: Logika generowania dokumentów ofert (Word)

### UI Components (`src/ui/components/`)
- **product_table.py**: Klasa `ProductTable` zarządzająca tabelą produktów
- **ui_components.py**: Klasa `UIComponents` z głównymi elementami interfejsu

### UI Frames (`src/ui/frames/`)
- **main_menu_frame.py**: Główne menu aplikacji
- **offer_creation_frame.py**: Ramka tworzenia ofert
- **browse_clients_frame.py**: Zarządzanie klientami
- **browse_suppliers_frame.py**: Zarządzanie dostawcami
- **settings_frame.py**: Ustawienia aplikacji

### UI Windows (`src/ui/windows/`)
- **client_search_window.py**: Okno wyszukiwania klientów
- **supplier_search_window.py**: Okno wyszukiwania dostawców
- **product_add_window.py**: Okno dodawania produktów

### Utils (`src/utils/`)
- **config.py**: Stałe konfiguracyjne aplikacji (ścieżki, wymiary okna, itp.)
- **settings.py**: Zarządzanie ustawieniami użytkownika (dane firmy, preferencje)

## Uruchamianie aplikacji

### Zrefaktoryzowana wersja
```bash
python main_refactored.py
```

### Oryginalna wersja (nadal dostępna)
```bash
python main.py
python main_old.py
```

To run the original monolithic version:
```bash
```

## Korzyści z refaktoryzacji

### 1. **Separacja odpowiedzialności**
- Każda klasa ma jasno określoną odpowiedzialność
- Logika biznesowa oddzielona od interfejsu użytkownika
- Warstwa dostępu do danych wydzielona

### 2. **Lepsze zarządzanie zależnościami**
- Importy są bardziej przejrzyste
- Łatwiejsze testowanie poszczególnych komponentów
- Unikanie cyklicznych zależności

### 3. **Łatwiejsza rozbudowa**
- Nowe funkcjonalności można dodawać bez modyfikacji istniejącego kodu
- Jasna struktura ułatwia orientację w projekcie
- Komponenty można łatwo ponownie wykorzystywać

### 4. **Lepsza czytelność kodu**
- Każdy plik ma jasno określony cel
- Krótsze, bardziej skupione klasy
- Lepsze nazewnictwo

### 5. **Łatwiejsze utrzymanie**
- Błędy można łatwiej zlokalizować
- Zmiany w jednym komponencie nie wpływają na inne
- Łatwiejsze debugowanie

## Mapowanie starych plików na nową strukturę

| Stary plik | Nowa lokalizacja |
|------------|------------------|
| `main.py` → `OfferGeneratorMainApp` | `src/core/main_app.py` |
| `main.py` → `OfferGeneratorApp` | `src/core/offer_generator_app.py` |
| `navigation.py` → `NavigationManager` | `src/core/navigation_manager.py` |
| `navigation.py` → `MainMenuFrame` | `src/ui/frames/main_menu_frame.py` |
| `navigation.py` → `OfferCreationFrame` | `src/ui/frames/offer_creation_frame.py` |
| `navigation.py` → `BrowseClientsFrame` | `src/ui/frames/browse_clients_frame.py` |
| `navigation.py` → `SettingsFrame` | `src/ui/frames/settings_frame.py` |
| `suppliers_frame.py` | `src/ui/frames/browse_suppliers_frame.py` |
| `database.py` | `src/data/database_service.py` |
| `offer_generator.py` | `src/services/offer_generator_service.py` |
| `config.py` | `src/utils/config.py` |
| `settings.py` | `src/utils/settings.py` |
| `table_manager.py` → `ProductTable` | `src/ui/components/product_table.py` |
| `ui_components.py` → `UIComponents` | `src/ui/components/ui_components.py` |
| `ui_components.py` → `ClientSearchWindow` | `src/ui/windows/client_search_window.py` |
| `ui_components.py` → `SupplierSearchWindow` | `src/ui/windows/supplier_search_window.py` |
| `ui_components.py` → `ProductAddWindow` | `src/ui/windows/product_add_window.py` |

## Dalsze możliwości rozwoju

1. **Testy jednostkowe**: Łatwe dodanie testów dla każdej klasy
2. **Wzorce projektowe**: Możliwość implementacji wzorców jak Factory, Observer
3. **Konfiguracja**: Wydzielenie konfiguracji do osobnego modułu
4. **Logowanie**: Dodanie systemu logowania
5. **Walidacja**: Wydzielenie walidacji do osobnych klas
6. **API**: Łatwe dodanie REST API lub innych interfejsów

## Zachowanie kompatybilności

Stare pliki nadal działają, więc można stopniowo migrować do nowej struktury. Zrefaktoryzowana wersja używa tych samych plików konfiguracyjnych i bazy danych co oryginalna.

## Navigation System

### Main Menu
The new version includes a main menu with the following options:
- **Stwórz nową ofertę** - Navigate to offer creation interface
- **Przeglądaj oferty** - (Future feature) Browse existing offers
- **Ustawienia** - (Future feature) Application settings
- **Zamknij aplikację** - Exit the application

### Navigation Features
- **Back Button** - Return to main menu from any screen
- **Modal Windows** - Client and supplier search windows
- **Frame Management** - Smooth transitions between different screens
- **State Preservation** - Form data is preserved during navigation

### Interface Structure
- **Main Application** (`main.py`) - Direct startup with menu and full functionality
- **Legacy Files** - Previous versions kept for reference

## Future Enhancements

The refactored structure makes it easier to implement:
- Unit testing for individual components
- Additional database operations
- New UI features
- Enhanced error handling
- Logging capabilities
