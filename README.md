# Generator Ofert

System tworzenia ofert handlowych z pełną funkcjonalnością zarządzania klientami, dostawcami i automatycznym generowaniem numerów ofert.

## 🚀 Szybki start

### Uruchomienie aplikacji

```bash
python launcher.py
```

lub bezpośrednio:

```bash
python main.py
```

## ✨ Funkcjonalności

- 📝 **Tworzenie ofert** - Pełny interfejs do tworzenia ofert handlowych
- 👥 **Zarządzanie klientami** - Wyszukiwanie i autowypełnianie danych klientów z bazy
- 🏭 **Zarządzanie dostawcami** - Wyszukiwanie i autowypełnianie danych dostawców z bazy
- 🔢 **Automatyczne numerowanie** - Automatyczne generowanie numerów ofert w formacie `<nr>/OF/<rok>/<alias>`
- 💾 **Zapis do bazy** - Automatyczne śledzenie ofert w bazie danych
- 🧮 **Kalkulacje** - Automatyczne obliczanie sum, podatków i wartości brutto
- 📄 **Generowanie dokumentów** - Eksport do plików Word z szablonem

## 🎯 Menu główne

Po uruchomieniu aplikacji zobaczysz menu główne z opcjami:

- **Stwórz nową ofertę** - Przejście do interfejsu tworzenia oferty
- **Przeglądaj oferty** *(wkrótce)* - Przeglądanie istniejących ofert
- **Ustawienia** *(wkrótce)* - Konfiguracja aplikacji
- **Zamknij aplikację** - Bezpieczne zamknięcie

## 🔧 Wymagania

- Python 3.7+
- Tkinter (zazwyczaj dołączony do Pythona)
- Biblioteki: `docxtpl`, `tkcalendar`, `sqlite3`

## 📁 Struktura projektu

```
├── launcher.py          # Launcher aplikacji
├── main.py             # Główna aplikacja z nawigacją
├── navigation.py       # System nawigacji
├── ui_components.py    # Komponenty interfejsu
├── database.py         # Operacje bazodanowe
├── offer_generator.py  # Generowanie ofert
├── table_manager.py    # Zarządzanie tabelą produktów
├── config.py          # Konfiguracja
├── templates/         # Szablony dokumentów
└── generated_docs/    # Wygenerowane pliki
```

## 📖 Szczegółowa dokumentacja

Pełna dokumentacja dostępna w pliku [`README_REFACTORED.md`](README_REFACTORED.md).

## 🏗️ Wersja

**Wersja 2.0** - Zrefaktorowana z nawigacją i pełną funkcjonalnością

---

*System Generator Ofert - Upraszczanie procesu tworzenia ofert handlowych*
