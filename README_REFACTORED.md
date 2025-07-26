# Offer Generator - Refactored

This application has been refactored to improve code organization and maintainability. The monolithic `appp.py` file has been split into several modules:

## File Structure

### Core Modules

- **`main.py`** - Main application entry point and application logic
- **`ui_components.py`** - UI components and layout management
- **`database.py`** - Database operations and client management
- **`offer_generator.py`** - Document generation functionality
- **`table_manager.py`** - Product table management
- **`config.py`** - Configuration constants and settings

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

## Running the Application

To run the refactored application:

```bash
python main.py
```

To run the original application:

```bash
python appp.py
```

## Module Responsibilities

### `main.py`
- Application initialization
- Main window setup
- Event handling coordination
- Application lifecycle management

### `ui_components.py`
- Form layout and widget creation
- Client search window functionality
- Data collection from UI elements
- UI state management

### `database.py`
- SQLite database connections
- Client data retrieval
- Database error handling

### `offer_generator.py`
- Document template processing
- PDF/DOCX generation
- Date formatting utilities

### `table_manager.py`
- Product table functionality
- Calculation logic
- Table data management

### `config.py`
- Application constants
- Default values
- File paths
- UI configuration

## Future Enhancements

The refactored structure makes it easier to implement:
- Unit testing for individual components
- Additional database operations
- New UI features
- Enhanced error handling
- Logging capabilities
