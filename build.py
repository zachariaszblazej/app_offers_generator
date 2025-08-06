#!/usr/bin/env python3
"""
Build script for creating executable from the Offer Generator application
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and print its output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result

def install_requirements():
    """Install requirements"""
    print("📦 Installing requirements...")
    if Path('requirements.txt').exists():
        run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    else:
        # Install minimal requirements
        packages = [
            'python-docx>=0.8.11',
            'Pillow>=8.0.0', 
            'PyInstaller>=5.0.0',
            'tkcalendar>=1.6.0',
            'docxcompose>=1.4.0'
        ]
        for package in packages:
            run_command([sys.executable, '-m', 'pip', 'install', package])

def create_exe():
    """Create executable using PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"Using PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        run_command([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Test critical imports before building
    print("🧪 Testing critical imports...")
    try:
        import tkcalendar
        from tkcalendar import DateEntry, Calendar
        print(f"✅ tkcalendar {tkcalendar.__version__} imports successful")
    except ImportError as e:
        print(f"❌ tkcalendar import failed: {e}")
        return False
    
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        from src.core.main_app import OfferGeneratorMainApp
        print("✅ Main app import successful")
    except ImportError as e:
        print(f"❌ Main app import failed: {e}")
        return False
    
    # Clean up any existing build directories
    build_dirs = ['build', 'dist', '__pycache__']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"Removing existing {dir_name} directory...")
            shutil.rmtree(dir_name)
    
    # Run PyInstaller with all necessary flags
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--onefile',
        '--windowed',
        '--name=OfferGenerator',
        '--additional-hooks-dir=.',
        '--add-data=src/*:src',
        '--add-data=templates/*:templates',
        '--add-data=background_offer_1.png:.',
        '--add-data=app_settings.json:.',
        # Hidden imports for all modules
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=PIL.Image',
        '--hidden-import=docx',
        '--hidden-import=docx.shared',
        '--hidden-import=docx.enum.text',
        '--hidden-import=docx.enum.table',
        '--hidden-import=tkcalendar',
        '--hidden-import=tkcalendar.calendar_',
        '--hidden-import=tkcalendar.dateentry',
        '--hidden-import=tkcalendar.tooltip',
        '--hidden-import=tkcalendar.__main__',
        '--hidden-import=babel',
        '--hidden-import=babel.dates',
        '--hidden-import=src.core.main_app',
        '--hidden-import=src.core.navigation_manager',
        '--hidden-import=src.core.offer_generator_app',
        '--hidden-import=src.core.offer_editor_app',
        '--hidden-import=src.ui.frames.main_menu_frame',
        '--hidden-import=src.ui.frames.settings_frame',
        '--hidden-import=src.ui.frames.browse_clients_frame',
        '--hidden-import=src.ui.frames.browse_suppliers_frame',
        '--hidden-import=src.ui.frames.browse_offers_frame',
        '--hidden-import=src.ui.frames.offer_creation_frame',
        '--hidden-import=src.ui.frames.offer_editor_frame',
        '--hidden-import=src.ui.components.ui_components',
        '--hidden-import=src.ui.components.product_table',
        '--hidden-import=src.ui.windows.client_search_window',
        '--hidden-import=src.ui.windows.supplier_search_window',
        '--hidden-import=src.ui.windows.product_add_window',
        '--hidden-import=src.ui.windows.product_edit_window',
        '--hidden-import=src.services.offer_generator_service',
        '--hidden-import=src.services.offer_editor_service',
        '--hidden-import=src.services.sync_service',
        '--hidden-import=src.data.database_service',
        '--hidden-import=src.utils.config',
        '--hidden-import=src.utils.settings',
        'main.py'
    ]
    
    print("Building executable...")
    result = run_command(cmd, check=False)
    
    if result.returncode == 0:
        print("✅ Build completed successfully!")
        print("📁 Executable location: dist/OfferGenerator")
        
        # Create distribution folder with all necessary files
        create_distribution()
        
    else:
        print("❌ Build failed!")
        return False
    
    return True

def create_distribution():
    """Create a distribution package with all necessary files"""
    print("📦 Creating distribution package...")
    
    dist_dir = "distribution"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # Copy executable
    exe_path = os.path.join("dist", "OfferGenerator")
    dist_exe_path = os.path.join(dist_dir, "OfferGenerator")
    shutil.copy2(exe_path, dist_exe_path)
    print("✅ Copied executable to distribution")
    
    # Copy necessary files
    files_to_copy = [
        "app_settings.json",
        "background_offer_1.png"
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, dist_dir)
            print(f"✅ Copied {file}")
    
    # Copy templates directory
    if os.path.exists("templates"):
        shutil.copytree("templates", os.path.join(dist_dir, "templates"))
        print("✅ Copied templates directory")
    
    # Create README
    readme_content = """# Generator Ofert

## Instrukcja uruchomienia

1. Upewnij się, że masz dostęp do bazy danych SQLite
2. Uruchom aplikację przez dwukliknięcie na plik wykonywalny OfferGenerator
3. Przy pierwszym uruchomieniu przejdź do Ustawień i skonfiguruj:
   - Ścieżkę do folderu z ofertami
   - Ścieżkę do bazy danych

## Wymagania systemowe

- System operacyjny: Windows 10/11, macOS 10.14+, lub Linux
- Dostęp do folderu z ofertami
- Dostęp do bazy danych SQLite

## Rozwiązywanie problemów

Jeśli aplikacja nie uruchamia się:
1. Sprawdź czy ścieżki w ustawieniach są poprawne
2. Upewnij się, że masz uprawnienia do odczytu/zapisu w katalogach
3. Sprawdź czy plik bazy danych istnieje i jest dostępny

## Kontakt

W przypadku problemów skontaktuj się z administratorem systemu.
"""
    
    with open(os.path.join(dist_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Show contents
    print("📋 Distribution contents:")
    for root, dirs, files in os.walk(dist_dir):
        level = root.replace(dist_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        for d in dirs:
            print(f"{indent}   📁 {d}/")
        for f in files:
            file_path = os.path.join(root, f)
            size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            print(f"{indent}   📄 {f} ({size:.1f} MB)")
    
    return dist_dir

def main():
    """Main build function"""
    print("🚀 Starting build process for Offer Generator...")
    
    # Check if we're in the right directory
    if not Path('src').exists():
        print("❌ Error: src directory not found. Make sure you're in the project root.")
        return
    
    if not Path('main.py').exists():
        print("❌ Error: main.py not found. Make sure the main entry point exists.")
        return
    
    # Install requirements
    install_requirements()
    
    # Create executable
    success = create_exe()
    
    if success:
        print("🎉 Build process completed successfully!")
        print("📁 Check the 'distribution' folder for the complete package")
    else:
        print("💥 Build process failed!")

if __name__ == "__main__":
    main()
