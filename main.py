#!/usr/bin/env python3
"""
Main entry point for the Offer Generator application
"""
import sys
import os
import traceback
from datetime import datetime

# Add the src directory to the Python path so we can import our modules
def setup_python_path():
    """Setup Python path for both development and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle
        src_path = os.path.join(sys._MEIPASS, 'src')
    else:
        # Development
        src_path = os.path.join(os.path.dirname(__file__), 'src')
    
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    return src_path

# Setup path at module level
setup_python_path()

def setup_error_logging():
    """Setup error logging to file for debugging"""
    try:
        log_dir = os.path.join(os.path.expanduser("~"), "OfferGenerator_Logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        def log_error(message):
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now()}: {message}\n")
            except:
                pass  # Ignore logging errors
        
        return log_error
    except:
        return lambda x: None  # Return dummy function if logging setup fails

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Normal execution
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def safe_input(prompt="Press Enter to exit..."):
    """Safe input that works in both console and windowed mode"""
    try:
        if hasattr(sys.stdin, 'read') and sys.stdin.readable():
            return input(prompt)
        else:
            # In windowed mode, just wait a bit and continue
            import time
            time.sleep(2)
            return ""
    except (EOFError, OSError, RuntimeError):
        # stdin not available (windowed mode)
        import time
        time.sleep(2)
        return ""

def main():
    """Main entry point"""
    log_error = setup_error_logging()
    
    try:
        log_error("Starting OfferGenerator application...")
        
        # Get correct paths for both development and PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller executable
            current_dir = sys._MEIPASS
            log_error(f"Running from PyInstaller bundle: {current_dir}")
        else:
            # Running in development
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_error(f"Running in development mode: {current_dir}")
        
        # Check if src directory exists
        src_dir = get_resource_path('src')
        log_error(f"Looking for src directory at: {src_dir}")
        
        if not os.path.exists(src_dir):
            error_msg = f"ERROR: src directory not found at {src_dir}"
            log_error(error_msg)
            log_error(f"Available files in current directory: {os.listdir(current_dir) if os.path.exists(current_dir) else 'Directory not accessible'}")
            print(error_msg)
            safe_input("Press Enter to exit...")
            sys.exit(1)
        
        log_error("Importing main application...")
        # Python path should already be set up
        from src.core.main_app import OfferGeneratorMainApp
        
        log_error("Creating application instance...")
        # Initialize and run the application
        app = OfferGeneratorMainApp()
        
        log_error("Starting application...")
        app.run()
        
    except KeyboardInterrupt:
        log_error("Application interrupted by user")
        print("\nApplication interrupted by user")
        sys.exit(0)
    except ImportError as e:
        error_msg = f"Import Error: {e}"
        log_error(error_msg)
        log_error(f"Python path: {sys.path}")
        print(f"❌ Import Error: {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
        safe_input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        error_msg = f"Error starting application: {e}"
        traceback_str = traceback.format_exc()
        log_error(error_msg)
        log_error(f"Full traceback:\n{traceback_str}")
        
        print(f"❌ Error starting application: {e}")
        print("\nFull error details:")
        print(traceback_str)
        print(f"\nError log saved to: {os.path.join(os.path.expanduser('~'), 'OfferGenerator_Logs')}")
        safe_input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
