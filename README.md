# SDrop — Neon Floating File Shelf for Windows 10/11

**SDrop** is a free, open-source, native Windows floating file shelf built with Python, PyQt6, and pure Win32 APIs by **[SmartUpWorld](https://smartupworld.com)**.

Gather files, folders, browser images, links, and clipboard snippets from anywhere on your PC into a sleek neon staging shelf—then drag them all out at once, zip them in the background, or convert images without touching the originals.

## Key Features

- **Shake-to-Summon:** Shake your mouse while dragging any file or link to pop SDrop open right beside your cursor (Off / Low / Medium / High sensitivity).
- **Global Hotkey:** Summon or hide instantly from any app (`Win+Alt+D`, `Ctrl+Alt+D`, or `Ctrl+Shift+D`).
- **Multi-Shelf Tabs:** Separate workflows by tab (`+` to add, double-click to rename).
- **Non-Destructive References:** Zero background disk copies and safe **Copy-by-default** drag-out.
- **Mixed-Media Staging:** Files, folders, `Ctrl+V` screenshots, dragged browser images, URLs, and text snippets.
- **Background Recursive `Zip All`:** Compresses stacked files and folders off the UI thread with automatic filename deduplication.
- **Quick Preview & Image Export:** Press `Space` to preview; right-click images to export PNG, JPG, or BMP copies.
- **5 Neon Glass Themes:** Electric Cyan, Cyber Magenta, Neon Lime, Ultraviolet, and Solar Amber with adjustable opacity.

## Download

Grab the latest Windows installer (`SDrop-v2.0.0-Setup.exe`) or portable ZIP (`SDrop-v2.0.0-Portable.zip`) from the **[Releases](https://github.com/smartupworldwebsolutions/sdrop/releases)** page.

## Run or Build from Source

    python -m pip install --upgrade PyQt6 pyinstaller
    python sdrop.py

Build standalone Windows bundle and installer:

    python -c "import sys, shutil; from PyQt6.QtWidgets import QApplication; import sdrop; app = QApplication(sys.argv); shutil.copy(sdrop.ensure_ico_file(), 'sdrop.ico')"
    python -m PyInstaller --clean --noconfirm --onedir --windowed --name "SDrop" --icon="sdrop.ico" --hidden-import=PyQt6.sip sdrop.py
    & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" sdrop_setup.iss

---

Developed and maintained by **[SmartUpWorld](https://smartupworld.com)**.
