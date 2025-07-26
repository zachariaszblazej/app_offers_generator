# Offer Generator - Refactored

This application has been refactored to improve code organization and maintainability. The monolithic `appp.py` file has been split into several modules:

## File Structure

### Core Modules

- **`main.py`** - Main application with navigation menu and full functionality
- **`navigation.py`** - Navigation system and menu components
- **`ui_components.py`** - UI components and layout management
- **`database.py`** - Database operations and client management
- **`offer_generator.py`** - Document generation functionality
- **`table_manager.py`** - Product table management
- **`config.py`** - Configuration constants and settings

### Legacy Files (For Reference)
- **`main_old.py`** - Previous refactored version (direct offer creation)
- **`appp.py`** - Original monolithic file

### Original Files
- **`appp.py`** - Original monolithic file (kept for reference)
- **`templates/`** - Document templates
- **`generated_docs/`** - Generated offer documents
- **`background_offer_1.png`** - UI background image

## Key Improvements

1. **Separation of Concerns**: Each module has a specific responsibility
2. **Configuration Management**: All constants centralized in `config.py`
3. **Better Organization**: UI, database, and business logic are separated
4. **Maintainability**: Easier to modify and extend individual components
5. **Reusability**: Components can be reused in other parts of the application
6. **Database Integration**: Both client and supplier search with auto-fill functionality
7. **Automatic Offer Numbering**: Auto-generation of sequential offer numbers with proper file naming
8. **Offer Tracking**: Database storage of offer information and file paths
9. **Navigation System**: Multi-screen interface with main menu and navigation
10. **Unified Interface**: Single, modern interface with all features integrated

## Running the Application

### Main Application
Run the application directly:
```bash
python main.py
```

### Legacy Versions (For Reference)
To run the old refactored version:
```bash
python main_old.py
```

To run the original monolithic version:
```bash
python appp.py
```

## Module Responsibilities

### `main.py`
- Main application with navigation menu
- Frame management and initialization
- Integration of all components
- Multi-screen coordination
- Complete offer generation functionality
- Direct entry point for users

### `navigation.py`
- Navigation manager for frame switching
- Main menu interface
- Offer creation frame wrapper
- Back button functionality
- Screen transition management

### `ui_components.py`
- Form layout and widget creation
- Client search window functionality
- Supplier search window functionality
- Data collection from UI elements
- UI state management
- Auto-fill functionality for both clients and suppliers

### `database.py`
- SQLite database connections
- Client data retrieval
- Supplier data retrieval
- Offer number management
- Offer tracking and storage
- Database error handling

### `offer_generator.py`
- Document template processing
- PDF/DOCX generation
- Date formatting utilities
- Automatic offer number generation
- Offer file path management
- Database integration for offer tracking

### `table_manager.py`
- Product table functionality
- Calculation logic
- Table data management

### `config.py`
- Application constants
- Default values
- File paths
- UI configuration

## New Features Added

### Automatic Offer Number Generation

The application now supports automatic generation of offer numbers with the following format:
`<order_number>/OF/<year>/<client_alias>`

**How it works:**
1. If the "OFERTA NR:" field is left empty, the system automatically generates a new offer number
2. If the field contains a value, that value is used as-is
3. The order number is automatically incremented based on the highest number in the database
4. Client alias is taken from the database (if client was selected) or auto-generated from client name
5. Files are saved to `../FakeHantechServer/Oferty/` with format: `<order_number>_OF_<year>_<client_alias>.docx`
6. Offer information is stored in the database `Offers` table

**Example:**
- Database has offers up to #218
- User selects client "AFD3D JACEK CHUDZIŃSKI" (alias: AFD3D)
- Date is set to 2025
- Generated offer number: `219/OF/2025/AFD3D`
- File saved as: `219_OF_2025_AFD3D.docx`
- Database entry: OfferOrderNumber=219, OfferFilePath=../FakeHantechServer/Oferty/219_OF_2025_AFD3D.docx

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
