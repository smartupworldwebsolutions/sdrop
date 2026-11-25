# Smartupworld Windows apps: Partner Center registry and playbook
Saved 2026-11-25 (from the owner's Gemini-guided submissions). Reuse for SFences Pro, STorrent and new apps.

## Publisher (same for every app)
- Display name: Smartupworld · Publisher ID: CN=A10ED12C-0499-4FBE-8193-87C74DAFC0BB
- Support: admin@smartupworld.com · https://smartupworld.com/contact/
- PC "pain" folder: C:\Users\mahmu\projects\windows-apps\<AppName>

## Apps
| App | Identity Name | Store ID | Stack | Status |
|---|---|---|---|---|
| SyncMind | Smartupworld.SyncMind | 9N071G9JK9R2 | .NET 10 WPF + WebView2 | Live in Store |
| SClip | Smartupworld.SClip-ClipboardManager | 9NQVQF9L978K | Python + PyQt6 + SQLite | Live: https://apps.microsoft.com/detail/9nqvqf9l978k |
| SDrop | Smartupworld.Sdrop (lowercase d) | 9P87Z4KCJGXQ | Python + PyQt6 | Listing/properties/age rating done 2026-11-25; package built from commit eb38300 |
| SFences Pro, STorrent | not reserved yet | | | Remaining |
SDrop PFN: Smartupworld.Sdrop_d7c0160x3szs0. Pages: /sdrop/ and /sdrop-privacy-policy/ on smartupworld.com (privacy page uses theme template page-sdrop-privacy-policy.php).

## Steps
1. Reserve the name in Partner Center FIRST. Copy Identity Name, Publisher, Publisher display name exactly (casing matters) and give them to the build workflow (inputs of "Build Windows packages"). Upload only `<App>-Store.msix` (unsigned is correct), never the .exe or ZIP.
2. Pricing: all markets, public, Currency USD + Retail price Free (otherwise Save draft stays disabled).
3. Properties: category Utilities & tools or Productivity. Choose "Yes, my product uses personal information" to reveal the privacy URL box. Website /<app>/, privacy /<app>-privacy-policy/ (must return 200). Keep the install-to-other-drives and OneDrive-backup boxes checked; uncheck clip-recording. Minimum hardware: keyboard and mouse.
4. Age rating (IARC): All Other App Types; physical media No. Offline apps: Online Content No. Web/AI apps (SyncMind): Online Content Yes, then answer No to the 4 revealed sections. Accept the IARC terms box on the preview screen.
5. Package: ignore the runFullTrust warning. Replacing a package: remove the old one first or raise the Version (1.0.0.1).
6. Store listing: product name matches reservation; features one per box, no dashes; at least one real desktop screenshot (1366x768+; logos do not count); short description; up to 7 keywords with no third-party brand names; Developed by Smartupworld.
   Images: 720x1080 -> 9:16 Poster art; 2160x2160 -> 1:1 Box art; 300x300 -> Store display images "1:1 App tile icon" (leave 150 and 71 empty).
7. Submission Options: runFullTrust reason, max 500 characters (keep under 480). General tester notes go in the separate "Additional Testing Information" page. Then Submit for certification.

## Problems met
1. Partner Center reserved "Sdrop", not "SDrop": reserve first, build after.
2. Privacy page needs the WordPress page published AND a Hostinger hPanel Git "Deploy" if auto-deploy lags.
3. Privacy URL box hidden until "Yes, uses personal information".
4. Pricing Save disabled until USD + Free chosen.
5. IARC: pick All Other App Types + "No" to physical media first; Online Content Yes adds 4 sections.
6. Logos and screenshots are separate slots.
7. Duplicate package version stalls validation.
8. runFullTrust box and tester notes are on different pages.
