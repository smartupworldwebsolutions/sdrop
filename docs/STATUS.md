# SDrop — STATUS (START HERE)
Updated: 2026-11-25
- App v2.0.0 (Python/PyQt6, PyInstaller). Publisher shown in app: "Smartupworld".
- winget: PR microsoft/winget-pkgs #486147 waiting for a moderator. Do NOT push changes to it.
- Microsoft Store: package built (commit eb38300, identity Smartupworld.Sdrop). Owner has finished listing, properties, age rating; remaining: upload package, screenshot, Submit for certification. Playbook: docs/STORE_SUBMISSION_PLAYBOOK.md
## Next
1. Owner reserves name "SDrop" in Partner Center, then gives Identity Name + Publisher CN + Publisher display name.
2. Run workflow "Build Windows packages" with those values; test the MSIX; upload SDrop-Store.msix.
3. Draft smartupworld.com/sdrop/ and /sdrop-privacy-policy/ pages (DRAFT first), publish only after owner's yes.
## Known limits
- MSIX: the "start with Windows" option writes the registry Run key, which MSIX virtualizes -> it will not autostart in the Store build. Fix later with a StartupTask.
- MSIX not yet tested by installing on a PC.

## Store identity (from Partner Center, 2026-11-25)
- Identity Name: Smartupworld.Sdrop (note lowercase d) · Publisher: CN=A10ED12C-0499-4FBE-8193-87C74DAFC0BB · Display: Smartupworld
- PFN: Smartupworld.Sdrop_d7c0160x3szs0 · Store ID: 9P87Z4KCJGXQ
- Defaults in workflow and build-msix.ps1 now use these. https://smartupworld.com/sdrop/ is live; privacy page still needed.
