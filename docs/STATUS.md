# SDrop — STATUS (START HERE)
Updated: 2026-11-25
- App v2.0.0 (Python/PyQt6, PyInstaller). Publisher shown in app: "Smartupworld".
- winget: PR microsoft/winget-pkgs #486147 waiting for a moderator. Do NOT push changes to it.
- Microsoft Store: SUBMITTED for certification 2026-11-25 (Submission 1, v2.0.0, Store ID 9P87Z4KCJGXQ). Waiting for Microsoft (1-3 business days). Then: add Store badge + link https://apps.microsoft.com/detail/9p87z4kcjgxq to smartupworld.com/sdrop/. Playbook: docs/STORE_SUBMISSION_PLAYBOOK.md
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
