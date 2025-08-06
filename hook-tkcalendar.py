# Custom PyInstaller hook for tkcalendar
# This file should help PyInstaller properly bundle tkcalendar

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all tkcalendar modules and data
datas, binaries, hiddenimports = collect_all('tkcalendar')

# Explicitly include all submodules
hiddenimports += collect_submodules('tkcalendar')

# Add specific imports that are commonly needed
hiddenimports += [
    'tkcalendar.calendar_',
    'tkcalendar.dateentry', 
    'tkcalendar.tooltip',
    'tkcalendar.__main__',
    'babel',
    'babel.dates',
    'babel.core',
    'babel.numbers'
]
