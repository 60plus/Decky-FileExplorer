# <img src="images/icon.svg" width="36" height="36" alt=""> FileExplorer

[![Downloads](https://img.shields.io/github/downloads/60plus/Decky-FileExplorer/total)](https://github.com/60plus/Decky-FileExplorer/releases)
[![Latest release downloads](https://img.shields.io/github/downloads/60plus/Decky-FileExplorer/latest/total?label=downloads%40latest)](https://github.com/60plus/Decky-FileExplorer/releases/latest)
[![Stars](https://img.shields.io/github/stars/60plus/Decky-FileExplorer?style=flat&logo=github)](https://github.com/60plus/Decky-FileExplorer/stargazers)
[![License: MIT](https://img.shields.io/github/license/60plus/Decky-FileExplorer)](LICENSE)

![FileExplorer: Two panels. One controller.](images/cover.png)

A simple, controller-friendly file manager for **SteamOS and Decky Loader**.
Open two folders side by side, select your files and copy or move them across.

[User manual](https://github.com/60plus/Decky-FileExplorer/wiki) ·
[Handheld guide](docs/wiki/Handheld-Guide.md) ·
[How it works](https://github.com/60plus/Decky-FileExplorer/wiki/How-It-Works) ·
[Troubleshooting](https://github.com/60plus/Decky-FileExplorer/wiki/Troubleshooting)

[![Buy me a beer](images/support/buy-me-a-beer.svg)](https://buymeacoffee.com/60plus)

## What it does

- **Two panels** with independent folders and selections. On handhelds and smaller screens, the window fills the available space between Steam's header and controller controls.
- **File and folder modification dates** beside their sizes, with local time. Choose name, size or newest-first date order from **Options → Sort by…** or Settings.
- **Gamepad controls** with Steam's controller glyphs. Choose hints on the panel, Steam bar, both, or neither.
- **Optional startup image.** A centered splash appears for three seconds on the first launch. Further displays are off by default and can be enabled in Settings.
- **First setup with Handheld and Steam PC profiles.** Choose a layout, use X for setting explanations, adjust and save. Everything stays editable later. See [first setup](docs/wiki/First-Setup.md).
- **Copy files and folders** between local disks and SMB shares, with percentage and transfer speed. On cancellation, keep unfinished copies for later or remove them. **Options → Interrupted copies** retains recovery tasks across restarts and subsequent operations.
- **Queue transfers or run up to 5 copies together.** Multiple selections can run one at a time or with a chosen parallel limit. Each active copy has its own progress; browsing, text editing and media playback remain available.
- **Copy or move with a choice at name conflicts:** change the incoming name, keep the old item as a numbered `.bak`, or overwrite with a red confirmation button. The interruption window has six consistent actions. Moves between filesystems verify the copied data before removing the source.
- **Two-column Options menu:** file actions on the left, current-folder and FileExplorer actions on the right, with four-direction controller navigation.
- **Background jobs through systemd** keep copying, moving, packing or extracting after closing FileExplorer. Plugin notifications report 25%, 50%, 75% and completion while the window is closed.
- **Open ZIP, RAR, 7z and TAR archives like folders**, select their contents and extract them to the other panel, using SteamOS's libarchive.
- **Create ZIP, 7z, TAR, TAR.GZ, TAR.BZ2 and TAR.XZ archives** with a name, compression level and destination panel of your choice.
- **Add applications and scripts to Steam** from Options or the mouse context menu. Open a running game's folder using **Open in FileExplorer** in Steam's game menu. See [Steam integration](docs/wiki/Steam-Integration.md).
- **Discover SMB servers and list their shares** from the connection dialog.
- **Browse SMB2 shares**, including guest access and username/password/domain authentication.
- **Remember SMB connections** when requested. Previously connected shares can be reopened without entering the password again.
- **Browse mounted network shares**, including NFS and desktop GVFS mounts, as ordinary folders.
- **Rename, create folders and select multiple files** from the Options menu.
- **Move local files to Trash** and restore them in Desktop Mode. **Empty Trash** is available in Options and Settings with a separate confirmation. SMB deletion is permanent.
- **Edit small text files** such as TXT, CFG, INI, JSON, XML and scripts, preserving their existing formatting and encoding. Automatic recovery drafts protect pending edits; only **Save** changes the original file.
- **Preview BMP, PNG, JPEG, GIF and WebP images** fitted to the available space. Left/right switches between images in the current folder, including SMB and archive folders.
- **Play audio and video** with pause, seek, stop, previous/next file and fullscreen video. Embedded audio covers appear automatically; a speaker icon fills in when no cover is present. See the [media guide](docs/wiki/Media-Player.md) for formats and compatibility playback.
- **Recognize text, configuration, code, archive, image, audio and video files** with distinct icons. A opens supported previews; **Options → Edit file** tries an unfamiliar extension as text.
- **Select and copy text with the controller**, paste through Steam's keyboard and undo with Menu/Start. The whole editor fits above the keyboard.
- **Customize the appearance** with six accent colors, background opacity, four text sizes and 70% to 100% interface scaling. The window keeps its size while smaller controls leave more room for content.

The Decky sidebar contains **Launch FileExplorer**, **Settings**, **Update**, **Support** and **About**.
Settings, Update and About stay inside the compact sidebar. **Update** checks the latest stable GitHub release,
shows its release notes, verifies the download and opens Decky's installation prompt.
Startup checks notify once per OS boot when a newer version is available. Disable them in Settings if preferred.

**Support** opens optional Buy Me a Coffee, Bitcoin and Cardano links and QR codes.
All features stay free. See [support options](docs/wiki/Support.md) for addresses.

## Supported formats

| Type | Recognized formats | What opens |
| --- | --- | --- |
| Audio (12 extensions) | `mp3`, `mp2`, `wav`, `wave`, `flac`, `ogg`, `oga`, `opus`, `m4a`, `m4b`, `aac`, `weba` | Player with embedded cover or speaker icon |
| Video (6 extensions) | `mp4`, `m4v`, `mov`, `webm`, `ogv`, `mkv` | Player with seek, pause and fullscreen |
| Images | BMP, PNG/APNG, JPG/JPEG/JPE/JFIF, GIF, WebP | Image viewer; previous/next picture |
| Archives | ZIP, RAR, 7z, TAR, GZ, BZ2, XZ, TGZ, TBZ/TBZ2, TXZ | Browse and extract files |
| Text (238 extensions, plus known filenames) | TXT, LOG, CFG/INI/CONF, JSON, YAML, TOML, XML, Markdown, CSV/TSV, subtitles, source code and more | Plain-text editor, preserving original formatting |

Media playback depends on the codecs inside the file. When needed, system FFmpeg
provides compatibility playback, up to 720p/30 fps for video. A filename extension
alone does not guarantee that every encoded file will play.

PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX and ODT/ODS/ODP are **not displayed as documents**.
HTML, SVG, RTF, Markdown and notebook files open as **source text**, without page
layout or rich formatting. Unknown text extensions can use **Options → Edit file**;
binary data is rejected. Opening a script never executes it.

[Complete text extension and filename list](docs/wiki/Supported-Formats.md) · [Audio/video controls](docs/wiki/Media-Player.md)

## See it in action

| PC | Handheld |
| --- | --- |
| [![Two file panels on a SteamOS PC](images/screenshots/pc-two-panels-c507ff7187f6.png)](images/screenshots/pc-two-panels-c507ff7187f6.png) | [![Two file panels on a SteamOS handheld](images/screenshots/handheld-two-panels-f825575c3911.png)](images/screenshots/handheld-two-panels-f825575c3911.png) |
| Browse two folders with sizes and modification dates. | The same columns fit the handheld at 70% scale. |
| [![PC text editor above Steam's keyboard](images/screenshots/pc-keyboard-3b28b937f8c1.png)](images/screenshots/pc-keyboard-3b28b937f8c1.png) | [![Handheld text editor at 80 percent scale above Steam's keyboard](images/screenshots/handheld-scaled-hidden-toolbar-b73d5ba87503.png)](images/screenshots/handheld-scaled-hidden-toolbar-b73d5ba87503.png) |
| Keep the edited text visible above the keyboard. | Smaller controls and a hidden toolbar leave more room for text. |
| [![Video playback on a SteamOS PC](images/screenshots/pc-media-video-f191b3ac0528.png)](images/screenshots/pc-media-video-f191b3ac0528.png) | [![Video playback on a SteamOS handheld](images/screenshots/handheld-media-video-4188f64d6ef3.png)](images/screenshots/handheld-media-video-4188f64d6ef3.png) |
| Play, pause and seek without leaving Gaming Mode. | The player and controller hints fit the handheld screen. |
| [![Four controller legend modes on pc](images/screenshots/pc-legend-comparison-ac8bf11feeb0.png)](images/screenshots/pc-legend-comparison-ac8bf11feeb0.png) | [![Four controller legend modes on handheld](images/screenshots/handheld-legend-comparison-9301ecfb7c8a.png)](images/screenshots/handheld-legend-comparison-9301ecfb7c8a.png) |
| Compare panel hints, the Steam bar, both and hidden. | The same four modes on the handheld. Click to enlarge. |

Expand a gallery below for more screenshots from SteamOS Gaming Mode.
Click any image to open it at full size. Full galleries: [PC](docs/SCREENSHOTS.md)
and [handheld](docs/wiki/Handheld-Gallery.md).

<details>
<summary><strong>PC</strong></summary>

### First setup

Choose a device profile, then adjust its settings before saving.

| Choose a profile | Review settings |
| --- | --- |
| [![PC profile choice](images/screenshots/pc-setup-profiles-e3f96bc0c649.png)](images/screenshots/pc-setup-profiles-e3f96bc0c649.png) | [![PC setup settings](images/screenshots/pc-setup-settings-7e4c603d2416.png)](images/screenshots/pc-setup-settings-7e4c603d2416.png) |

| Centered startup image | Help for each setting |
| --- | --- |
| [![Three-second startup image](images/screenshots/pc-splash-a6ebad1fe06e.png)](images/screenshots/pc-splash-a6ebad1fe06e.png) | [![Help opened with the controller](images/screenshots/pc-setup-help-20e713238998.png)](images/screenshots/pc-setup-help-20e713238998.png) |

### Resolve a name conflict

| Six consistent actions | Keep a backup or overwrite |
| --- | --- |
| [![Name conflict with six actions](images/screenshots/pc-conflict-overwrite-76ee2d89ead3.png)](images/screenshots/pc-conflict-overwrite-76ee2d89ead3.png) | [![Backup and red overwrite confirmation](images/screenshots/pc-conflict-backup-82b01746585c.png)](images/screenshots/pc-conflict-backup-82b01746585c.png) |

Change the incoming name to keep both items, or choose how to replace the existing file or folder.

### Copy queue and parallel transfers

Choose one-at-a-time copying or up to five simultaneous tasks, then keep browsing, editing or playing media.

![Copy queue progress on PC](images/screenshots/pc-queue-progress-f29fe1237075.png)

![Copy queue options on PC](images/screenshots/pc-queue-options-f431892a2e34.png)

![Copy queue add on PC](images/screenshots/pc-queue-add-9f872a035188.png)


### Recover unsaved text

[![Restore an unsaved text draft on pc](images/screenshots/pc-draft-recovery-2fad4cc796e1.png)](images/screenshots/pc-draft-recovery-2fad4cc796e1.png)

### Moving, packing and Steam integration

| Create an archive | Add to Steam |
| --- | --- |
| [![Archive options](images/screenshots/pc-pack-7b0810112696.png)](images/screenshots/pc-pack-7b0810112696.png) | [![Create a Steam shortcut](images/screenshots/pc-add-steam-ac50c28e3484.png)](images/screenshots/pc-add-steam-ac50c28e3484.png) |

| Move to the other panel | Open the game folder |
| --- | --- |
| [![Move confirmation](images/screenshots/pc-move-802c82eb6d8a.png)](images/screenshots/pc-move-802c82eb6d8a.png) | [![Native Steam game menu](images/screenshots/pc-game-menu-48fe6dd10f5d.png)](images/screenshots/pc-game-menu-48fe6dd10f5d.png) |

### Media, recovery and optional controls

| Audio and video player | Embedded audio cover |
| --- | --- |
| [![Audio and video player](images/screenshots/pc-media-video-f191b3ac0528.png)](images/screenshots/pc-media-video-f191b3ac0528.png) | [![Embedded audio cover](images/screenshots/pc-media-audio-cover-33d092badbe7.png)](images/screenshots/pc-media-audio-cover-33d092badbe7.png) |

| Recover an interrupted copy | Both legends hidden |
| --- | --- |
| [![Recover an interrupted copy](images/screenshots/pc-conflict-recovery-b8f77da76948.png)](images/screenshots/pc-conflict-recovery-b8f77da76948.png) | [![Both legends hidden](images/screenshots/pc-hidden-legends-dc996cb16bf6.png)](images/screenshots/pc-hidden-legends-dc996cb16bf6.png) |


These captures show the installed plugin on a SteamOS PC, using demonstration files.

![File and folder dates beside their sizes, with a selected file](images/screenshots/pc-two-panels-c507ff7187f6.png)

| Browse archives like folders | Edit configuration files |
| --- | --- |
| [![Select individual profiles inside a ZIP archive](images/screenshots/pc-archive-browsing-a8dd18da7330.png)](images/screenshots/pc-archive-browsing-a8dd18da7330.png) | [![Text editor with indentation, line numbers and an active line](images/screenshots/pc-text-editor-eb56264c4a94.png)](images/screenshots/pc-text-editor-eb56264c4a94.png) |
| Open an archive with **A**, select with **X**, extract with **Y**. | Keep indentation, blank lines, encoding and line endings. |

| Keep the edited line visible | Watch progress and speed |
| --- | --- |
| [![Edited line above Steam's on-screen keyboard](images/screenshots/pc-keyboard-3b28b937f8c1.png)](images/screenshots/pc-keyboard-3b28b937f8c1.png) | [![Copy operation showing percentage, size and transfer speed](images/screenshots/pc-copy-progress-c2d9b1c3a529.png)](images/screenshots/pc-copy-progress-c2d9b1c3a529.png) |
| Make changes with the controller and Steam's keyboard. | See how much has copied and how fast it is moving. |

| Close the panel and carry on | Add a network share |
| --- | --- |
| [![Native FileExplorer notification during a background transfer](images/screenshots/pc-extracted-50-e562b98a3dbe.png)](images/screenshots/pc-extracted-50-e562b98a3dbe.png) | [![SMB connection form with server discovery and share listing](images/screenshots/pc-network-share-a0720567c9c1.png)](images/screenshots/pc-network-share-a0720567c9c1.png) |
| Background operations report **25%, 50%, 75% and done**. | Find servers, list shares and optionally remember the login. |

| File actions within reach | Clear confirmation before emptying Trash |
| --- | --- |
| [![File options including rename, edit, copy and Trash](images/screenshots/pc-options-7822e8fb357c.png)](images/screenshots/pc-options-7822e8fb357c.png) | [![Red warning about the shared Desktop Mode Trash](images/screenshots/pc-trash-warning-a319b9484192.png)](images/screenshots/pc-trash-warning-a319b9484192.png) |
| Open **Options** for rename, edit, copy and folder actions. | The warning explicitly includes the **Desktop Mode Trash**. |

| Make it your own | Select and copy text |
| --- | --- |
| [![Appearance settings in the Decky sidebar](images/screenshots/pc-appearance-9b2b3fe8319d.png)](images/screenshots/pc-appearance-9b2b3fe8319d.png) | [![Several text lines selected with the controller](images/screenshots/pc-text-selection-5d1e5fca048b.png)](images/screenshots/pc-text-selection-5d1e5fca048b.png) |
| Choose an accent color, background opacity and text size. | Hold **RT/R2 + directions**, copy with **View/Select**, paste with Steam's keyboard. |

| Open pictures without leaving Gaming Mode | Preview images inside an archive |
| --- | --- |
| [![Image viewer showing an alpine lake and aurora](images/screenshots/pc-image-viewer-a75b84e35404.png)](images/screenshots/pc-image-viewer-a75b84e35404.png) | [![Viewing another picture directly inside a ZIP](images/screenshots/pc-archive-image-6f938b6f1c25.png)](images/screenshots/pc-archive-image-6f938b6f1c25.png) |
| Press **A** to open; **left/right** or **L1/R1** changes the image. | Open the ZIP, enter its picture folder and press **A** on an image. |

**Network discovery.** Real servers found on the local test network.

[![Automatic SMB discovery showing seven servers on the local network](images/screenshots/pc-smb-discovery-fdde134d19a1.png)](images/screenshots/pc-smb-discovery-fdde134d19a1.png)

| Check the latest GitHub release | Control startup notifications |
| --- | --- |
| [![Checking the installed version against the latest GitHub release](images/screenshots/pc-github-update-d683c5dec15f.png)](images/screenshots/pc-github-update-d683c5dec15f.png) | [![Startup update check switch in Settings](images/screenshots/pc-startup-setting-50f670562f3b.png)](images/screenshots/pc-startup-setting-50f670562f3b.png) |
| When a newer release is available, read its notes, download and confirm in Decky. | Notify once per OS boot; manual checks work with this option off. |

</details>

<details>
<summary><strong>Handheld</strong></summary>

### First setup

Choose a device profile, then adjust its settings before saving.

| Choose a profile | Review settings |
| --- | --- |
| [![Handheld profile choice](images/screenshots/handheld-setup-profiles-026f34a63e51.png)](images/screenshots/handheld-setup-profiles-026f34a63e51.png) | [![Handheld setup settings](images/screenshots/handheld-setup-settings-a173a84bc52f.png)](images/screenshots/handheld-setup-settings-a173a84bc52f.png) |

| Centered startup image | Help for each setting |
| --- | --- |
| [![Three-second startup image](images/screenshots/handheld-splash-6671a1d56392.png)](images/screenshots/handheld-splash-6671a1d56392.png) | [![Help opened with the controller](images/screenshots/handheld-setup-help-6910e56f5297.png)](images/screenshots/handheld-setup-help-6910e56f5297.png) |

### Resolve a name conflict

| Six consistent actions | Keep a backup or overwrite |
| --- | --- |
| [![Name conflict with six actions](images/screenshots/handheld-conflict-overwrite-adf58b4282e0.png)](images/screenshots/handheld-conflict-overwrite-adf58b4282e0.png) | [![Backup and red overwrite confirmation](images/screenshots/handheld-conflict-backup-7325a6c0abc8.png)](images/screenshots/handheld-conflict-backup-7325a6c0abc8.png) |

Change the incoming name to keep both items, or choose how to replace the existing file or folder.

### Copy queue and parallel transfers

Choose one-at-a-time copying or up to five simultaneous tasks, then keep browsing, editing or playing media.

![Copy queue progress on Handheld](images/screenshots/handheld-queue-progress-a40e3952f439.png)

![Copy queue options on Handheld](images/screenshots/handheld-queue-options-bd62eda901e3.png)

![Copy queue add on Handheld](images/screenshots/handheld-queue-add-8f363cf0ae13.png)


### Recover unsaved text

[![Restore an unsaved text draft on handheld](images/screenshots/handheld-draft-recovery-4231eddb03a9.png)](images/screenshots/handheld-draft-recovery-4231eddb03a9.png)

### Moving, packing and Steam integration

| Create an archive | Add to Steam |
| --- | --- |
| [![Archive options](images/screenshots/handheld-pack-f3606a82f12c.png)](images/screenshots/handheld-pack-f3606a82f12c.png) | [![Create a Steam shortcut](images/screenshots/handheld-add-steam-9869350e498b.png)](images/screenshots/handheld-add-steam-9869350e498b.png) |

| Move to the other panel | Open the game folder |
| --- | --- |
| [![Move confirmation](images/screenshots/handheld-move-8ee7e32ce530.png)](images/screenshots/handheld-move-8ee7e32ce530.png) | [![Native Steam game menu](images/screenshots/handheld-game-menu-ee7e057ed9e2.png)](images/screenshots/handheld-game-menu-ee7e057ed9e2.png) |

### Media, recovery and optional controls

| Audio and video player | Embedded audio cover |
| --- | --- |
| [![Audio and video player](images/screenshots/handheld-media-video-4188f64d6ef3.png)](images/screenshots/handheld-media-video-4188f64d6ef3.png) | [![Embedded audio cover](images/screenshots/handheld-media-audio-cover-c8d3a37257f7.png)](images/screenshots/handheld-media-audio-cover-c8d3a37257f7.png) |

| Recover an interrupted copy | Both legends hidden |
| --- | --- |
| [![Recover an interrupted copy](images/screenshots/handheld-conflict-recovery-f301fcba5f9c.png)](images/screenshots/handheld-conflict-recovery-f301fcba5f9c.png) | [![Both legends hidden](images/screenshots/handheld-hidden-legends-85367f2b0660.png)](images/screenshots/handheld-hidden-legends-85367f2b0660.png) |


These captures come from a **ROG Ally running SteamOS**. Browse the
[handheld gallery](docs/wiki/Handheld-Gallery.md) for archives, text selection,
images, network discovery and settings.

| Full window with two panels | More text above the keyboard |
| --- | --- |
| [![Handheld file manager at 70 percent scale](images/screenshots/handheld-two-panels-f825575c3911.png)](images/screenshots/handheld-two-panels-f825575c3911.png) | [![Editor at 80 percent scale with toolbar hidden](images/screenshots/handheld-scaled-hidden-toolbar-b73d5ba87503.png)](images/screenshots/handheld-scaled-hidden-toolbar-b73d5ba87503.png) |
| The window fills Steam's available space. | Choose **80% Interface scale** and press **L3** to hide the toolbar. |

</details>

## Controls

Steam renders the matching glyphs for the active controller. The names below use Xbox / Steam Deck labels.

| Button | Action |
| --- | --- |
| D-pad / left stick | Navigate files and buttons |
| A | Open a supported folder, archive, text file, image, audio or video; confirm |
| B | Parent folder; close at the filesystem/share root |
| X | Select or deselect the focused item, then advance to the next |
| Y | Copy the selection; inside an archive, extract selected contents |
| L1 / LB | Focus the left panel |
| R1 / RB | Focus the right panel |
| R3 | Cycle through toolbar, active transfer controls and the current file row |
| L3 | Hide or show the top toolbar |
| Start / Menu | File and folder options |
| View / Select | Locations, mounted drives and SMB connections |

Copy uses the selected items, or the focused item if nothing is selected.
Use **Left/Right** to move between the two file panels. During a transfer,
press **Right from the right panel** to reach Cancel/Transfers directly,
or **Left from the left panel** to reach the last transfer action.
Left/Right then moves between those buttons; continuing past the end returns
to the file panels. Up returns to the remembered file row; Down reaches the
progress cards. This also works with the toolbar hidden. Without a transfer,
Left/Right wraps between the panels.

R3 reveals a hidden toolbar. During a transfer, the next R3 reaches **Cancel / Transfers**;
another returns to the current row. Without a transfer, the second R3 returns directly.
Down from the toolbar also returns to the files. L3 remembers toolbar visibility
and keeps the legend's chosen setting.
Menus and file lists wrap at their ends, skipping disabled actions. Each Options
column wraps independently; X on the last file advances to the first file.
Mouse users can click to focus, double-click to open and click the square to select.
Steam's text fields support its on-screen keyboard for names and connection details.

## Network shares

Open **Locations → Add SMB share → Find servers**, choose a server, then use **List shares**.
Enter login details before listing shares if the server requires them. Credentials are sent only to the server you choose.
You can also enter a server name or IP and share name manually.
Leave username/password blank for a guest share. Domain is optional.

Discovery combines advertised SMB services with a bounded TCP 445 scan on directly connected private IPv4 LANs.
It checks up to 512 addresses; on networks larger than /24 it scans the computer's local /24.
Servers on other subnets or hidden by a firewall can be entered manually. A detected open port does not guarantee guest access.

Enable **Remember connection** to save the connection for future sessions.
Passwords are encrypted by systemd for this device and Steam user, with no extra unlock password.
TPM and the system key are used when available; a system key alone supports devices without TPM.
If secure storage is unavailable, new connections stay session-only and a warning explains why.
Existing saved passwords migrate automatically after a successful encryption/readback check, keeping the same shares and folders.
Neither passwords nor encrypted credentials are returned by the settings API. Use **Settings → Saved connections → Forget** to remove them.
This protects saved credentials at rest; programs running as the same user can still request decryption.
See [credential storage and recovery](docs/wiki/Network-Shares.md#remember-or-forget-a-connection) for device changes or TPM resets.

Existing operating-system mounts appear in Locations and reuse the operating system's established session.
FileExplorer does not read passwords from KDE Wallet or change `/etc/fstab`.
Direct SMB connections use SMB2 and NTLMv2 on TCP 445; servers requiring SMB3 encryption are not supported in this version.
Unmounted NFS shares should first be mounted through SteamOS/Desktop Mode.

## Settings

- Check GitHub for updates at startup and notify once per OS boot (enabled by default). Manual checks remain available.
- Show hidden files, including dot files and the SMB hidden attribute.
- Show folders first.
- Optional three-second startup image. It appears once on the first launch and stays off afterward unless enabled.
- Sort by name, size or last modification.
- Remember the folders open in both panels.
- Limit the unpacked size of each archive: 10, 50, 100 or 500 GiB, or choose **Unlimited**.
- Choose cyan, blue, green, amber, violet or rose accents, 70/85/100% background opacity and four text sizes.
- Use **Interface scale** to fit more content while keeping the window full size.
- Show controller hints in the panel, on Steam's bar, in both places or hide them.
- Hide the file toolbar, or reveal it with **R3** when needed.
- Reopen **Run first-time setup** to review either profile before saving.
- Empty the SteamOS Trash, including trash on connected drives. This permanently deletes trashed items.

Opacity, interface scale and extraction limit use sliders. Press **X** on a
setting for its explanation; **up/down** closes the help and moves to the next
setting. Descriptions stay hidden until needed.

## Install

Download the **FileExplorer plugin ZIP** from the [latest release](https://github.com/60plus/Decky-FileExplorer/releases/latest).
Use the plugin ZIP, not the source-code archive.

1. Open Decky Loader settings and enable **Developer mode**.
2. Select **Developer → Install Plugin from ZIP File**.
3. Choose the downloaded ZIP and confirm installation.
4. Open **FileExplorer → Launch FileExplorer**.

Decky also accepts a direct plugin ZIP link under **Install Plugin from URL**.
See the [illustrated installation guide](https://github.com/60plus/Decky-FileExplorer/wiki/Installation)
for both methods and the Developer-mode screenshots.

## Update

Open **FileExplorer → Update → Check for updates**, then choose **Download and install**.
The plugin verifies the GitHub ZIP before opening Decky's installation prompt.
Confirm **Install** there. Settings, saved connections and running transfers are preserved.
Updates contain the complete plugin, so intermediate releases are not required.

See the [update guide](https://github.com/60plus/Decky-FileExplorer/wiki/Installation#update-an-existing-installation)
for the complete workflow.

## File handling

FileExplorer runs as the Steam user, without root privileges.
Transfers run in a separate systemd user service. Closing the window or reloading the plugin does not cancel them.
The active window shows progress and speed; when it is closed, FileExplorer posts notifications with its icon at each quarter and at completion.
Notifications require Steam and Decky to be running. Reopening the window reconnects to the current operation.
Shutdown or reboot interrupts a transfer; this version does not resume an interrupted transfer automatically.
Speed measures bytes processed by the current stage, including temporary staging when extracting selected archive contents.

Copy and move name conflicts ask before replacing anything. The six actions are **Resume**, **Start again**, **Change name**, **Overwrite**, **Cancel** and **Open FileExplorer**. Change name keeps both items. Overwrite opens a confirmation with **Back up & replace** (`.bak`, `.bak.2`, etc.) or the red **Overwrite** action. The old item is removed only after the replacement is ready. A folder is replaced as a whole, including old-only contents, rather than merged. Resume retries after you remove the conflicting destination; Start again uses a new retry folder. **B** or **Open FileExplorer** leaves the decision pending. Independent parallel copies can continue. The same question appears with FileExplorer closed and can be reopened from **Transfers / queue**.
Files are copied into a temporary name in the destination and renamed after completion.
An interrupted connection or shutdown can leave a hidden `.fileexplorer-*.partial` item.
Use **Options → Interrupted copies** to verify and resume it, start a separate new copy, or remove the partial data.
Starting another operation does not erase retained recovery tasks.

Press **A** on an archive to browse its folders. **B** returns to the parent folder, including out of the archive root.
Select files or folders with **X**, then press **Y** to extract those items directly into the other panel, locally or on SMB.
The archive stays unchanged. An archive open in the destination panel is read-only.
Selected extraction uses temporary disk space; archives on SMB are downloaded temporarily for reading.
The separate **Extract whole archive** option creates a new folder in a local destination.
To browse an archive nested inside another archive, first extract that inner archive to a normal folder.
Absolute paths, traversal, links and special files are rejected. There is a 100,000-entry limit as well as the configured byte limit.
Password-protected and multipart archives are not supported. Some uncommon RAR compression methods may not be supported by the system library.
Copying symbolic links or special files is refused. A copy preserves file contents and folder structure; it is not a backup of ownership, permissions, ACLs or extended attributes.

## Text editor

Press **A** on a text file, or choose **Options → Edit text file**. Navigate to a line and press **A** to edit it.
The whole editor shrinks above Steam's on-screen keyboard, with the current line and surrounding text visible.
**X** inserts a line with the same indentation; **Y** saves; **Menu/Start** undoes a recent edit.
Press **R3** (click the right stick) to switch between the text and the toolbar.
Move left/right across toolbar buttons, confirm with **A**, and use **R3** or **Down** to return to the cursor.
R3 also closes an open keyboard and focuses the toolbar.
Press **L3** (click the left stick) to hide or show the toolbar and leave more room
for text, including while Steam's keyboard is open. **R3** shows a hidden toolbar
when you need its buttons. **Settings → Interface scale** can make all controls in
the file manager, editor and image viewer smaller without shrinking their windows.
With the keyboard hidden, hold **RT/R2 + directions** to select text and press **View/Select** to copy the selection or current line.
Press **A** at the destination and use Steam's native **Paste**. Recovery drafts are saved automatically after 0.4 seconds without typing, or every 1.5 seconds during continuous typing.
Only **Save** changes the original file. On close, keep a draft for later, discard it or continue editing.
Reopening the same file offers to restore its draft after a crash or shutdown. See [draft recovery](docs/wiki/Text-Editor.md#recovery-drafts).

The editor keeps spaces, tabs, blank lines, existing line endings (including mixed endings), the final newline, BOM and original encoding.
It does not run a formatter or reserialize the document. JSON syntax is checked before saving, with an invalid line highlighted;
other formats retain their text layout but do not have a syntax validator.
UTF-8 and BOM-marked UTF-16 are detected automatically. For older files, choose the original encoding explicitly.
Unsupported characters, external file changes, binary files and files larger than 512 KiB are refused instead of silently replacing data.
The editor supports up to 10,000 lines. Files inside archives must be extracted before editing.
SMB editing uses a temporary replacement and backup; after a connection failure, check any reported backup before retrying.

## Image viewer

Press **A** on a BMP, PNG, JPEG, GIF or WebP file to open the image viewer.
Use **left/right** or **L1/R1** to browse the other images in the same folder; **B** returns to the file list.
The viewer follows the panel's sorting and hidden-file settings and wraps at either end.
It works with local files, existing mounts, SMB shares and images inside browsable archives.
The original file is unchanged. Preview limits are **20 MiB**, **40 megapixels** and **16,384 pixels per side**.
See the [illustrated image-viewer guide](https://github.com/60plus/Decky-FileExplorer/wiki/Image-Viewer).

**Empty Trash** displays a red warning: it also empties the same Trash used in **Desktop Mode**, including connected drives.
The confirmation is required because this permanently deletes the trashed items.

## Build

Use Node.js with pnpm, and Python 3.10 or newer:

```sh
pnpm install --frozen-lockfile
python3 -m pip install --target vendor -r requirements.txt
pnpm typecheck
node --test tests/editor-text.mjs
pnpm build
python3 -m unittest discover -s tests -v
python3 scripts/package.py
```

The installable ZIP and SHA-256 checksum are written to `out/`.
The archive tests use Linux's system libarchive. Runtime Python dependencies are included in the plugin ZIP.
See [verification notes](docs/TESTING.md) for the tested environment and coverage.
The manual source is in [docs/wiki](docs/wiki/Home.md); see
[maintaining the wiki](docs/WIKI.md) for publishing matching documentation updates.

Built with [Decky API and UI](https://github.com/SteamDeckHomebrew/decky-plugin-template),
[pysmb](https://github.com/miketeo/pysmb) and the system [libarchive](https://www.libarchive.org/).
MIT license. Dependency licenses are included with their distributions in the plugin bundle.
The 60plus author logo is supplied by the repository owner and is not covered by the source-code MIT license.
