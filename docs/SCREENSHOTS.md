# FileExplorer screenshot gallery

FileExplorer, captured in Steam Gaming Mode on a SteamOS PC on 15 October 2026.
These are unedited screenshots of the installed plugin, using demonstration files in
`/home/deck/fileexplorer-lab` and real SMB discovery results from the test LAN.
Controller glyphs are supplied by Steam. These captures use the Steam PC profile:
100% interface scale, an opaque panel and controller hints only on Steam's bottom bar.
The explicitly labelled legend comparison retains its earlier four-mode captures.

Screenshots are refreshed when the layout or demonstrated behavior changes.
A different version number alone does not require a new gallery.

[Back to the README](../README.md)

See also the [handheld gallery](wiki/Handheld-Gallery.md), captured on a ROG Ally
running SteamOS, including interface scaling and the editor's L3 toolbar toggle.

## First setup

Choose a profile and review its settings. The handheld wizard fills the available
space; its settings scroll above fixed Save and Back buttons.

[![Welcome](../images/screenshots/pc-setup-welcome-63da58563441.png)](../images/screenshots/pc-setup-welcome-63da58563441.png)

[![Profile choice](../images/screenshots/pc-setup-profiles-e3f96bc0c649.png)](../images/screenshots/pc-setup-profiles-e3f96bc0c649.png)

[![Editable profile settings](../images/screenshots/pc-setup-settings-7e4c603d2416.png)](../images/screenshots/pc-setup-settings-7e4c603d2416.png)

The centered splash appears once for three seconds; repeat displays are off by default.

[![Centered startup image](../images/screenshots/pc-splash-a6ebad1fe06e.png)](../images/screenshots/pc-splash-a6ebad1fe06e.png)

Press the controller Help button on any setup setting for its explanation.

[![Setting help opened with X](../images/screenshots/pc-setup-help-20e713238998.png)](../images/screenshots/pc-setup-help-20e713238998.png)

## Long file lists

The dark, rounded scrollbar matches the file panels. Controller navigation keeps
the focused file visible; the other panel can stay at its own position.

[![Long folder with the styled scrollbar](../images/screenshots/pc-scrollbar-04a7ccae75bd.png)](../images/screenshots/pc-scrollbar-04a7ccae75bd.png)

## Update from GitHub

Check the latest stable release, read the release notes and download the update.
The ZIP is verified before Decky opens its installation prompt.

The development build in this capture is newer than the public release, so the
check correctly reports that no update is needed. Download controls appear when
a newer public version is available. The installation prompt below uses the
current local plugin ZIP and was cancelled after capture.

![Result of checking GitHub for an update](../images/screenshots/pc-github-update-d683c5dec15f.png)

![Decky asks for confirmation before replacing the installed plugin](../images/screenshots/pc-verified-install-634bb1755a2a.png)

Startup checks can notify once per OS boot. The Settings switch disables automatic
checks and notifications while keeping manual updates available.

![Startup update preference in the Decky sidebar](../images/screenshots/pc-startup-setting-50f670562f3b.png)

## Two file panels

Keep the source and destination side by side. Select multiple files or folders with **X**,
then copy them to the other panel with **Y**. The bottom legend stays visible.

![Two panels with modification dates and a selected file](../images/screenshots/pc-two-panels-c507ff7187f6.png)

The **Modified** column shows local dates and times. **Options → Sort by…**
chooses name, size or newest-first dates for both panels.

## Open archives like folders

Browse into a ZIP, select the profiles you want and extract those items into the other panel.
The archive remains unchanged. ZIP, RAR, 7z and TAR use the same browsing workflow.

![Profiles selected inside a ZIP archive](../images/screenshots/pc-archive-browsing-a8dd18da7330.png)

## Edit text while keeping its layout

Line numbers, a highlighted active line and controller shortcuts make small configuration
changes possible without leaving Gaming Mode. Formatting and encoding are retained;
JSON also receives a syntax check before saving. The example shows a JSON file with CRLF endings.
Press **R3** to reach the toolbar and again to return to the cursor.

![Text editor showing a controller configuration](../images/screenshots/pc-text-editor-eb56264c4a94.png)

## See the line above the keyboard

Press **A** to edit. The whole editor panel shrinks above Steam's on-screen keyboard,
keeping the toolbar, current line, nearby text and status visible.

![Editing controller sensitivity with Steam's keyboard](../images/screenshots/pc-keyboard-3b28b937f8c1.png)

## Follow a transfer at a glance

The open window shows the percentage, copied bytes, total size, speed and current filename.
This screenshot uses a real copy of demonstration data. Demo workers were held
briefly to capture the controls; the displayed speed is a recorded reading, not
a performance measurement.

![A real copy with live progress and speed](../images/screenshots/pc-copy-progress-c2d9b1c3a529.png)

## Let it finish in the background

Copying continues after closing FileExplorer. Native Steam notifications use the
plugin's icon and report quarter milestones plus completion. The example notification
at the bottom right comes from extracting the demonstration Game backup archive.

![Native notification with FileExplorer closed](../images/screenshots/pc-extracted-50-e562b98a3dbe.png)

## Find servers on your network

Choose **Locations → Add SMB share → Find servers** to discover SMB servers without
typing their addresses. This capture shows seven real results from the test LAN,
including advertised device names and local IP addresses. Select a server to fill
the connection form, then use **List shares** to choose a share.

![Automatic SMB discovery showing real local servers and their IP addresses](../images/screenshots/pc-smb-discovery-fdde134d19a1.png)

## Reach your network shares

The connection dialog offers **Find servers** and **List shares**, manual server/share
entry, optional credentials and a Remember connection option further down the form.
The form is shown before entering login details; no connection was submitted.

![Network share form with example server and share](../images/screenshots/pc-network-share-a0720567c9c1.png)

## Common file actions in one menu

Open **Options** to copy, rename, edit text, create a folder or move local files to Trash.
Actions that do not apply to the selected item are disabled.

![File options including moving and archive creation](../images/screenshots/pc-options-7822e8fb357c.png)

## Know which Trash will be emptied

A red warning explains that FileExplorer and Desktop Mode share the same Trash.
The dialog was cancelled after this screenshot; no user files were deleted.

![Empty Trash confirmation with red warning](../images/screenshots/pc-trash-warning-a319b9484192.png)

## Customize the appearance

Choose an accent color, background opacity and text size in the compact Decky sidebar.
Reset appearance restores the default look without changing folders or connections.
Opacity, interface scale and extraction limit use full-width sliders. Press **X**
to expand help for the focused setting; moving up/down hides it again.

![Appearance settings and color preview](../images/screenshots/pc-appearance-9b2b3fe8319d.png)

![Separate spacing for Reset appearance, Empty Trash and Saved connections](../images/screenshots/pc-settings-actions-53eb0f4f65af.png)

## Select and copy text with the controller

Hold **RT/R2** while moving in the text to select a fragment or several lines.
**View/Select** copies into the system clipboard. Use Steam's keyboard to paste,
and **Menu/Start** to undo an edit.

![Multiline text selection with native controller glyphs](../images/screenshots/pc-text-selection-5d1e5fca048b.png)

## View pictures in Gaming Mode

Press **A** to open an image. Use **left/right** or **L1/R1** to switch pictures
without returning to the file list. The header shows the filename, image counter,
dimensions and file size. The lake artwork was generated for this demonstration;
the screenshot is an unedited capture of the installed SteamOS plugin.

![Aurora landscape inside FileExplorer's image viewer](../images/screenshots/pc-image-viewer-a75b84e35404.png)

## Look inside an archive of pictures

The image viewer also works inside archive folders. Only the chosen image is
extracted temporarily, and the source archive is unchanged. The second capture
shows another image selected from the demonstration ZIP.

![Previewing an image directly from the demonstration ZIP](../images/screenshots/pc-archive-image-6f938b6f1c25.png)

## Media, recovery and controller hints

[![Media file icons](../images/screenshots/pc-media-file-icons-9c1f76a170f7.png)](../images/screenshots/pc-media-file-icons-9c1f76a170f7.png)

[![Media audio cover](../images/screenshots/pc-media-audio-cover-33d092badbe7.png)](../images/screenshots/pc-media-audio-cover-33d092badbe7.png)

[![Media audio speaker](../images/screenshots/pc-media-audio-speaker-cb213785376f.png)](../images/screenshots/pc-media-audio-speaker-cb213785376f.png)

[![Media video](../images/screenshots/pc-media-video-f191b3ac0528.png)](../images/screenshots/pc-media-video-f191b3ac0528.png)

[![Media fullscreen](../images/screenshots/pc-media-fullscreen-366cffa04907.png)](../images/screenshots/pc-media-fullscreen-366cffa04907.png)

[![Text editor](../images/screenshots/pc-text-editor-eb56264c4a94.png)](../images/screenshots/pc-text-editor-eb56264c4a94.png)

[![Keyboard](../images/screenshots/pc-keyboard-3b28b937f8c1.png)](../images/screenshots/pc-keyboard-3b28b937f8c1.png)

[![Interrupted copy recovery](../images/screenshots/pc-conflict-recovery-b8f77da76948.png)](../images/screenshots/pc-conflict-recovery-b8f77da76948.png)

[![Legend settings](../images/screenshots/pc-legend-settings-cee1c5ed5e2e.png)](../images/screenshots/pc-legend-settings-cee1c5ed5e2e.png)

[![Hidden legends](../images/screenshots/pc-hidden-legends-dc996cb16bf6.png)](../images/screenshots/pc-hidden-legends-dc996cb16bf6.png)

## Compare controller legends

Panel only, Steam bar only, both and hidden. Four native captures arranged side by side.

[![Four controller legend modes on pc](../images/screenshots/pc-legend-comparison-ac8bf11feeb0.png)](../images/screenshots/pc-legend-comparison-ac8bf11feeb0.png)

## Moving, packing and Steam integration

[![Confirm a move to the other panel](../images/screenshots/pc-move-802c82eb6d8a.png)](../images/screenshots/pc-move-802c82eb6d8a.png)

[![Choose archive format and compression](../images/screenshots/pc-pack-7b0810112696.png)](../images/screenshots/pc-pack-7b0810112696.png)

[![Add a non-Steam application](../images/screenshots/pc-add-steam-ac50c28e3484.png)](../images/screenshots/pc-add-steam-ac50c28e3484.png)

[![Open the running application folder from Steam](../images/screenshots/pc-game-menu-48fe6dd10f5d.png)](../images/screenshots/pc-game-menu-48fe6dd10f5d.png)

## Copy queue and parallel progress

Each task has its own progress. Choose up to five copies, or queue the selection after existing tasks.

![Copy queue options](../images/screenshots/pc-queue-options-f431892a2e34.png)

![Copy queue progress](../images/screenshots/pc-queue-progress-f29fe1237075.png)

![Copy queue add](../images/screenshots/pc-queue-add-9f872a035188.png)



## Recover unsaved text

Restore a saved draft after interruption, keeping the original file unchanged until Save.

[![Restore an unsaved text draft on pc](../images/screenshots/pc-draft-recovery-2fad4cc796e1.png)](../images/screenshots/pc-draft-recovery-2fad4cc796e1.png)


## Name conflicts and grouped Options

File actions and folder controls occupy separate columns. Copy and move conflicts use six actions, with a separate backup or overwrite confirmation.

[![Two-column Options menu](../images/screenshots/pc-options-7822e8fb357c.png)](../images/screenshots/pc-options-7822e8fb357c.png)

[![Six actions at a name conflict](../images/screenshots/pc-conflict-overwrite-76ee2d89ead3.png)](../images/screenshots/pc-conflict-overwrite-76ee2d89ead3.png)

[![Keep a backup or overwrite](../images/screenshots/pc-conflict-backup-82b01746585c.png)](../images/screenshots/pc-conflict-backup-82b01746585c.png)

[![A move conflict appears while FileExplorer is closed](../images/screenshots/pc-conflict-background-folder-cff872f33ef9.png)](../images/screenshots/pc-conflict-background-folder-cff872f33ef9.png)
