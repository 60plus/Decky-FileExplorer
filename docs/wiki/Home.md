# FileExplorer user guide

![FileExplorer: Two panels. One controller.](../../images/cover.png)

Manage files on your **SteamOS PC or handheld** without leaving Gaming Mode.
FileExplorer opens two folders side by side, with controller controls for copying,
archive browsing, text editing, image previews and network shares.

This manual describes **FileExplorer**. The screenshots were captured from the
installed plugin on a SteamOS PC, using demonstration files and real LAN discovery
results. Steam supplies the button glyphs for the active controller.

## Choose a guide

| I want to… | Guide |
| --- | --- |
| Install the plugin or update the installed ZIP | [Installation](Installation.md) |
| Learn the controls and use the two panels | [Everyday use](Daily-Use.md) |
| Copy files and leave a transfer running | [Copying and background jobs](Copy-and-Background-Jobs.md) |
| Open an archive and extract only what I need | [Archives](Archives.md) |
| Edit TXT, CFG, JSON or other small text files | [Text editor](Text-Editor.md) |
| View pictures and switch between them with the controller | [Image viewer](Image-Viewer.md) |
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

![Two panels with multiple folders selected](../../images/screenshots/01-two-panels-c446ee4897f4.png)

## What this version includes

The compact Decky sidebar contains **Launch FileExplorer**, **Settings**, **Update**
and **About**. The file manager opens in a large central window; the other pages
stay in the sidebar. About shows the version, plugin icon and 60plus logo.

Updates currently use the plugin ZIP from
[latest release](https://github.com/60plus/Decky-FileExplorer/releases/latest).
The **Update** page explains this; automatic GitHub updates are not enabled yet.

The recorded test environment is **SteamOS 3.8.28 with Decky Loader 3.2.10 on an
x86-64 PC**. See the [verification notes](../TESTING.md) for the checks and their
limits, and the [full screenshot gallery](../SCREENSHOTS.md) for the feature captures.
