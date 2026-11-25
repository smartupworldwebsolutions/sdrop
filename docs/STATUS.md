# SDrop — STATUS (START HERE)
Updated: 2026-11-25
- App v2.0.0 (Python/PyQt6, PyInstaller). Publisher shown in app: "Smartupworld".
- winget: PR microsoft/winget-pkgs #486147 waiting for a moderator. Do NOT push changes to it.
- Microsoft Store: IN PROGRESS. Packaging/ + workflow + docs/STORE_LISTING.md added today.
## Next
1. Owner reserves name "SDrop" in Partner Center, then gives Identity Name + Publisher CN + Publisher display name.
2. Run workflow "Build Windows packages" with those values; test the MSIX; upload SDrop-Store.msix.
3. Draft smartupworld.com/sdrop/ and /sdrop-privacy-policy/ pages (DRAFT first), publish only after owner's yes.
## Known limits
- MSIX: the "start with Windows" option writes the registry Run key, which MSIX virtualizes -> it will not autostart in the Store build. Fix later with a StartupTask.
- Workflow and MSIX scripts are untested until the first Actions run.
