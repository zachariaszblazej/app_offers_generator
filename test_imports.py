#!/usr/bin/env python3
"""
Simple test script to verify imports work in GitHub Actions
"""

print("=== Starting import tests ===")

# Test 1: Basic Python modules
try:
    import sys
    import os
    print(f"✅ Python {sys.version}")
    print(f"✅ Current directory: {os.getcwd()}")
except Exception as e:
    print(f"❌ Basic Python imports failed: {e}")

# Test 2: tkinter
try:
    import tkinter
    print("✅ tkinter available")
except Exception as e:
    print(f"❌ tkinter failed: {e}")

# Test 3: PIL/Pillow
try:
    import PIL
    print(f"✅ PIL version: {PIL.__version__}")
except Exception as e:
    print(f"❌ PIL failed: {e}")

# Test 4: python-docx
try:
    import docx
    print("✅ python-docx available")
except Exception as e:
    print(f"❌ python-docx failed: {e}")

# Test 5: babel
try:
    import babel
    print(f"✅ babel version: {babel.__version__}")
except Exception as e:
    print(f"❌ babel failed: {e}")

# Test 6: tkcalendar
try:
    import tkcalendar
    print(f"✅ tkcalendar version: {tkcalendar.__version__}")
    from tkcalendar import DateEntry, Calendar
    print("✅ tkcalendar DateEntry and Calendar imported")
except Exception as e:
    print(f"❌ tkcalendar failed: {e}")

# Test 7: Main app
try:
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from src.core.main_app import OfferGeneratorMainApp
    print("✅ Main app import successful")
except Exception as e:
    print(f"❌ Main app import failed: {e}")

print("=== Import tests completed ===")
