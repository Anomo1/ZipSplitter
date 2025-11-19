# Distribution Guide

## Standalone Executable

Your application has been packaged as a single executable file:

**Location:** `dist/ZipSplitter.exe`  
**Size:** ~11 MB

## How to Share

1. Navigate to the `dist` folder inside `ZipSplitterApp`.
2. Copy `ZipSplitter.exe` to any location or USB drive.
3. Share the file with anyone — **no Python installation required**.

## Running the Exe

- Double-click `ZipSplitter.exe` to launch the application.
- The app runs completely standalone with all dependencies bundled.

## Notes

- The exe works on Windows (64-bit).
- First launch might be slightly slower as it extracts temporary files.
- Some antivirus software may flag PyInstaller executables as false positives. This is normal for bundled Python apps.

## Rebuilding the Exe

If you make changes to the source code, rebuild the exe with:

```bash
pyinstaller --onefile --noconsole --name="ZipSplitter" main.py
```

The new exe will be in the `dist` folder.
