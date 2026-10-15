# FileExplorer user guide

The screenshots and manual show the current development interface. The [latest public release](https://github.com/60plus/Decky-FileExplorer/releases/latest) may not include every feature shown yet.

![FileExplorer: Two panels. One controller.](../../images/cover.png)

Manage files on your **SteamOS PC or handheld** without leaving Gaming Mode.
FileExplorer opens two folders side by side, with controller controls for copying,
archive browsing, text editing, image previews, audio/video playback and network shares.

This manual describes **FileExplorer**. The screenshots were captured from the
installed plugin on a SteamOS PC and ROG Ally handheld, using demonstration files and real LAN discovery
results. Steam supplies the button glyphs for the active controller.

## Choose a guide

| I want to… | Guide |
| --- | --- |
| Install the plugin or update the installed ZIP | [Installation](Installation.md) |
| Choose a Handheld or Steam PC profile and customize it | [First setup](First-Setup.md) |
| Learn the controls and use the two panels | [Everyday use](Daily-Use.md) |
| Set up the layout, keyboard and controller hints on a handheld | [Handheld guide](Handheld-Guide.md) |
| Copy or move files and leave a transfer running | [Copying and background jobs](Copy-and-Background-Jobs.md) |
| Create an archive, browse it or extract selected files | [Archives](Archives.md) |
| Add a non-Steam application or open a game's folder | [Steam integration](Steam-Integration.md) |
| Edit TXT, CFG, JSON or other small text files | [Text editor](Text-Editor.md) |
| View pictures and switch between them with the controller | [Image viewer](Image-Viewer.md) |
| Play audio and video with the controller | [Media player](Media-Player.md) |
| Check audio, video and text file support | [Supported formats](Supported-Formats.md) |
| Browse all handheld feature screenshots | [Handheld gallery](Handheld-Gallery.md) |
| Find a NAS, connect to SMB or open a mounted share | [Network shares](Network-Shares.md) |
| Show hidden files, change sorting or empty Trash | [Settings and Trash](Settings-and-Trash.md) |
| Understand the implementation | [How it works](How-It-Works.md) |
| Resolve an error or collect useful diagnostics | [Troubleshooting](Troubleshooting.md) |

## Your first copy

1. Open **Decky → FileExplorer → Launch FileExplorer**.
2. Use **L1 / LB** for the left panel and open your source folder.
3. Use **R1 / RB** for the right panel and open the destination folder.
4. Return to the source panel. Press **X** on each item you want to copy.
5. Press **Y**, check the destination in the confirmation and choose **Copy**.

The copy continues if you close FileExplorer. Reopen it to see progress, or let
the notifications report **25%, 50%, 75% and completion**.

| SteamOS PC | SteamOS handheld |
| --- | --- |
| [![Two file panels on PC](../../images/screenshots/pc-two-panels-c507ff7187f6.png)](../../images/screenshots/pc-two-panels-c507ff7187f6.png) | [![Two file panels on handheld](../../images/screenshots/handheld-two-panels-f825575c3911.png)](../../images/screenshots/handheld-two-panels-f825575c3911.png) |

## What this version includes

The compact Decky sidebar contains **Launch FileExplorer**, **Settings**, **Update**
and **About**. The file manager fills the available space on handhelds and smaller
screens, and uses a centered window on large displays. The other pages stay in
the sidebar. About shows the version, plugin icon and 60plus logo.

The **Update** page checks the
[latest release](https://github.com/60plus/Decky-FileExplorer/releases/latest),
verifies the download and opens Decky's installation prompt. Startup checks notify
once per OS boot when an update is available and can be disabled in Settings.

The recorded test environments are a **SteamOS PC and a ROG Ally handheld**, both
running **SteamOS 3.8.28 with Decky Loader 3.2.10**. See the
[verification notes](../TESTING.md) for the checks and their limits. Browse the
[PC gallery](../SCREENSHOTS.md) or [handheld gallery](Handheld-Gallery.md), or start
with the [handheld setup and controls guide](Handheld-Guide.md).
