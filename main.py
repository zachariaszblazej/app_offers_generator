#!/usr/bin/env python3
"""
Main entry point for the Offer Generator application
"""
import sys
import os

# Add the src directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main entry point"""
    try:
        from src.core.main_app import OfferGeneratorMainApp
        
        # Initialize and run the application
        app = OfferGeneratorMainApp()
        app.run()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
