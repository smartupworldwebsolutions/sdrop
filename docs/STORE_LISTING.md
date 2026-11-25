# SDrop — Microsoft Store listing (copy to paste into Partner Center)

Developer / publisher name everywhere: **Smartupworld**. Copyright: `© 2026 Smartupworld`.
Website (page must exist first): https://smartupworld.com/sdrop/
Privacy policy (page must exist first): https://smartupworld.com/sdrop-privacy-policy/
Support: https://smartupworld.com/contact/  ·  admin@smartupworld.com

## Pricing / properties / age rating (same answers as SyncMind)
- Free, USD, all markets, public. Category: Productivity (or Utilities & tools).
- "Does this product access, collect, or transmit personal information?" -> Yes (reveals the privacy URL box).
- IARC: All Other App Types. Online Content: **No** (SDrop shows no web content). Every other question: No.

## Short description
Floating neon file shelf: gather files, links and images, then drag them all out at once.

## Full description
```text
SDrop is a free floating shelf for your Windows desktop. Drag files, folders, images, links or text onto it from anywhere, keep them together while you work, then drag everything out at once into any app or folder.

Shake your mouse while dragging a file and SDrop pops up right beside your cursor, so you never have to open two windows side by side. Or summon it from any app with a keyboard shortcut.

Key Features
- Shake to Summon: shake while dragging and the shelf appears next to your cursor (Off, Low, Medium or High sensitivity).
- Global Hotkey: show or hide SDrop from any app with Win+Alt+D, Ctrl+Alt+D or Ctrl+Shift+D.
- Multi-Shelf Tabs: keep separate shelves for separate jobs. Add a tab with +, rename it with a double-click.
- Safe by Default: SDrop only keeps references to your files. It makes no background copies, and dragging out copies by default, so your originals stay where they are.
- Mixed Media: files, folders, pasted screenshots (Ctrl+V), images dragged from a browser, links and text snippets.
- Zip All: compress everything on the shelf into one ZIP in the background, with automatic file-name de-duplication.
- Quick Preview and Image Export: press Space to preview; right-click an image to save a PNG, JPG or BMP copy.
- 5 Neon Glass Themes: Electric Cyan, Cyber Magenta, Neon Lime, Ultraviolet and Solar Amber, with adjustable opacity.

Privacy
SDrop works on your PC. Your shelves and settings are stored locally. Smartupworld does not collect analytics, run user accounts or receive your files.

Requires Windows 10 or Windows 11 (64-bit).
```

## Features (bullets)
- Shake to Summon: shake while dragging a file and the shelf appears beside your cursor.
- Global Hotkey: show or hide SDrop from any app.
- Multi-Shelf Tabs: separate shelves for separate jobs.
- Safe by Default: keeps references only, drag-out copies, originals untouched.
- Mixed Media: files, folders, screenshots, browser images, links and text.
- Zip All: one background ZIP of everything on the shelf.
- Quick Preview and Image Export to PNG, JPG or BMP.
- 5 neon glass themes with adjustable opacity.

## Keywords (7)
file shelf, drag and drop, clipboard shelf, file manager, zip files, image converter, desktop utility

## Screenshot caption
Gather files, links and images on one floating shelf, then drag them all out at once.

## Image mapping (files come from the GitHub "latest" release, SDrop-store-logos.zip)
- 9:16 Poster art 720x1080 -> SDrop-store-logo-720x1080.png
- 1:1 Box art 2160x2160 -> SDrop-logo-2160.png
- 1:1 App tile icon 300x300 -> SDrop-store-logo-300x300.png
- Screenshot (1366x768 or larger): take one of the real app on screen.

## runFullTrust justification (Submission Options)
```text
SDrop is a packaged Python/Qt desktop application. runFullTrust is required for all packaged desktop apps that run as full-trust processes.
```

## Tester notes (Additional Testing Information)
```text
SDrop is a free Windows desktop utility (Python/PyQt6). It declares runFullTrust because it is a packaged desktop application. It runs no background services and collects or transmits no data. No login is needed. To test: install and start SDrop, drag any file from File Explorer onto the shelf, then drag it out into another folder. Press Win+Alt+D to hide or show it. Optional per-user items the user turns on in Settings: start with Windows, tray icon, global shortcut. Privacy policy: https://smartupworld.com/sdrop-privacy-policy/ - Support: admin@smartupworld.com
```
