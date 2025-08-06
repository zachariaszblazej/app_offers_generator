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

def create_exe():
    """Create executable using PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"Using PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        run_command([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Clean up any existing build directories
    build_dirs = ['build', 'dist', '__pycache__']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"Removing existing {dir_name} directory...")
            shutil.rmtree(dir_name)
    
    # Create the spec file content
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    def create_exe(target_platform="current"):
    """Create the executable using PyInstaller"""
    print(f"Building executable for {target_platform}...")
    
    # Set executable name based on platform
    if target_platform == "windows":
        exe_name = "OfferGenerator.exe"
        console_flag = "--noconsole"
        additional_flags = ""
    else:
        exe_name = "OfferGenerator"
        console_flag = "--windowed"
        additional_flags = ""
    
    # Remove existing build and dist directories
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("Removed existing build directory")
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("Removed existing dist directory")
    
    # Run PyInstaller with platform-specific settings
    cmd = f"{python_executable} -m PyInstaller --clean --onefile {console_flag} --name={exe_name.split('.')[0]} --add-data=templates/*:templates --add-data=background_offer_1.png:. --add-data=app_settings.json:. main.py"
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error during build: {result.stderr}")
        return False, None
        
    print("✅ Build completed successfully!")
    
    # Find the created executable
    dist_path = os.path.join('dist')
    if target_platform == "windows":
        exe_path = os.path.join(dist_path, exe_name)
    else:
        exe_path = os.path.join(dist_path, exe_name.split('.')[0])
    
    return True, exe_path
    hiddenimports=[
        'PIL._tkinter_finder',
        'PIL.Image',
        'docx',
        'docx.shared',
        'docx.enum.text',
        'docx.enum.table',
        'tkcalendar',
        'tkcalendar.calendar_',
        'tkcalendar.dateentry',
        'tkcalendar.tooltip',
        'src.core.main_app',
        'src.core.navigation_manager',
        'src.core.offer_generator_app',
        'src.core.offer_editor_app',
        'src.ui.frames.main_menu_frame',
        'src.ui.frames.settings_frame',
        'src.ui.frames.browse_clients_frame',
        'src.ui.frames.browse_suppliers_frame',
        'src.ui.frames.browse_offers_frame',
        'src.ui.frames.offer_creation_frame',
        'src.ui.frames.offer_editor_frame',
        'src.ui.components.ui_components',
        'src.ui.components.product_table',
        'src.ui.windows.client_search_window',
        'src.ui.windows.supplier_search_window',
        'src.ui.windows.product_add_window',
        'src.ui.windows.product_edit_window',
        'src.services.offer_generator_service',
        'src.services.offer_editor_service',
        'src.services.sync_service',
        'src.data.database_service',
        'src.utils.config',
        'src.utils.settings',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OfferGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True if you want to see console output
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to .ico file if you have one
)
'''
    
    # Write the spec file
    with open('OfferGenerator.spec', 'w') as f:
        f.write(spec_content)
    
    print("Created OfferGenerator.spec file")
    
    # Run PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--onefile',
        '--windowed',
        '--name=OfferGenerator',
        '--add-data=templates/*:templates',
        '--add-data=background_offer_1.png:.',
        '--add-data=app_settings.json:.',
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

def create_distribution(exe_path, target_platform="current"):
    """Create a distribution package with all necessary files"""
    print("📦 Distribution package created in: distribution")
    
    dist_dir = "distribution"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # Copy executable
    if target_platform == "windows":
        dist_exe_path = os.path.join(dist_dir, "OfferGenerator.exe")
    else:
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
    readme_content = f"""# Generator Ofert

## Instrukcja uruchomienia

1. Upewnij się, że masz dostęp do bazy danych SQLite
2. Uruchom aplikację przez dwukliknięcie na plik wykonywalny {'OfferGenerator.exe' if target_platform == 'windows' else 'OfferGenerator'}
3. Przy pierwszym uruchomieniu przejdź do Ustawień i skonfiguruj:
   - Ścieżkę do folderu z ofertami
   - Ścieżkę do bazy danych

## Wymagania systemowe

- System operacyjny: {'Windows 10/11' if target_platform == 'windows' else 'Windows 10/11, macOS 10.14+, lub Linux'}
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
    print("📋 Contents:")
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
    print("📦 Installing requirements...")
    if Path('requirements.txt').exists():
        run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Create executable
    success = create_exe()
    
    if success:
        print("🎉 Build process completed successfully!")
        print("📁 Check the 'distribution' folder for the complete package")
    else:
        print("💥 Build process failed!")

if __name__ == "__main__":
    main()
