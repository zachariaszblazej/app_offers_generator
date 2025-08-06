#!/usr/bin/env python3
"""
Simple test script to verify imports work in GitHub Actions
"""

print("=== Starting import tests ===")

# Test 1: Basic Python modules
try:
    import sys
    import os
    print(f"[OK] Python {sys.version}")
    print(f"[OK] Current directory: {os.getcwd()}")
except Exception as e:
    print(f"[FAIL] Basic Python imports failed: {e}")

# Test 2: tkinter
try:
    import tkinter
    print("[OK] tkinter available")
except Exception as e:
    print(f"[FAIL] tkinter failed: {e}")

# Test 3: PIL/Pillow
try:
    import PIL
    print(f"[OK] PIL version: {PIL.__version__}")
except Exception as e:
    print(f"[FAIL] PIL failed: {e}")

# Test 4: python-docx
try:
    import docx
    print("[OK] python-docx available")
except Exception as e:
    print(f"[FAIL] python-docx failed: {e}")

# Test 5: babel
try:
    import babel
    print(f"[OK] babel version: {babel.__version__}")
except Exception as e:
    print(f"[FAIL] babel failed: {e}")

# Test 6: tkcalendar
try:
    import tkcalendar
    print(f"[OK] tkcalendar version: {tkcalendar.__version__}")
    from tkcalendar import DateEntry, Calendar
    print("[OK] tkcalendar DateEntry and Calendar imported")
except Exception as e:
    print(f"[FAIL] tkcalendar failed: {e}")

# Test 7: Main app
try:
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from src.core.main_app import OfferGeneratorMainApp
    print("[OK] Main app import successful")
except Exception as e:
    print(f"[FAIL] Main app import failed: {e}")

print("=== Import tests completed ===")
