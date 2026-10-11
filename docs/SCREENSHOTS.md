# FileExplorer screenshot gallery

FileExplorer, captured in Steam Gaming Mode on a SteamOS PC on 12 October 2026.
These are unedited screenshots of the installed plugin, using demonstration files in
`/home/deck/fileexplorer-lab/demo` and real SMB discovery results from the test LAN.
Controller glyphs are supplied by Steam.

[Back to the README](../README.md)

## Update from GitHub

Check the latest stable release, read the release notes and download the update.
The ZIP is verified before Decky opens its installation prompt.

![Installed and available versions with a verified download option](../images/screenshots/15-github-update-f2b9d6244506.png)

![Decky asks for confirmation before replacing the installed plugin](../images/screenshots/16-verified-install-8c70d74d0335.png)

Startup checks can notify once per OS boot. The Settings switch disables automatic
checks and notifications while keeping manual updates available.

![Startup update preference in the Decky sidebar](../images/screenshots/17-update-settings-2a1f8b6dd8a6.png)

## Two folders, one controller

Keep the source and destination side by side. Select multiple files or folders with **X**,
then copy them to the other panel with **Y**. The bottom legend stays visible.

![Two panels with Mods and Profiles selected](../images/screenshots/01-two-panels-c446ee4897f4.png)

## Open archives like folders

Browse into a ZIP, select the profiles you want and extract those items into the other panel.
The archive remains unchanged. ZIP, RAR, 7z and TAR use the same browsing workflow.

![Profiles selected inside a ZIP archive](../images/screenshots/02-archive-browsing-63332a829c46.png)

## Edit text while keeping its layout

Line numbers, a highlighted active line and controller shortcuts make small configuration
changes possible without leaving Gaming Mode. Formatting and encoding are retained;
JSON also receives a syntax check before saving. The example shows a JSON file with CRLF endings.
Press **R3** to reach the toolbar and again to return to the cursor.

![Text editor showing a controller configuration](../images/screenshots/03-text-editor-e0c4f9946117.png)

## See the line above the keyboard

Press **A** to edit. The whole editor panel shrinks above Steam's on-screen keyboard,
keeping the toolbar, current line, nearby text and status visible.

![Editing controller sensitivity with Steam's keyboard](../images/screenshots/04-keyboard-5d650b4daf23.png)

## Follow a transfer at a glance

The open window shows the percentage, copied bytes, total size, speed and current filename.
This screenshot was taken during a real copy of generated demo data. The speed is an
instantaneous reading on the test PC, not a performance promise.

![A real copy with live progress and speed](../images/screenshots/05-copy-progress-574110153ac8.png)

## Let it finish in the background

Copying continues after closing FileExplorer. Native Steam notifications use the
plugin's icon and report quarter milestones plus completion. The example notification
at the bottom right comes from copying the demo Game backup folder.

![Native notification with FileExplorer closed](../images/screenshots/06-background-notification-6d5018c7b427.png)

## Find servers on your network

Choose **Locations → Add SMB share → Find servers** to discover SMB servers without
typing their addresses. This capture shows seven real results from the test LAN,
including advertised device names and local IP addresses. Select a server to fill
the connection form, then use **List shares** to choose a share.

![Automatic SMB discovery showing real local servers and their IP addresses](../images/screenshots/10-smb-discovery-be509db9bd73.png)

## Reach your network shares

The connection dialog offers **Find servers** and **List shares**, manual server/share
entry, optional credentials and a Remember connection option further down the form.
`nas.example` and `Games` are demonstration values; no login was sent for this screenshot.

![Network share form with example server and share](../images/screenshots/07-network-share-982884978b24.png)

## Common file actions in one menu

Open **Options** to copy, rename, edit text, create a folder or move local files to Trash.
Actions that do not apply to the selected item are disabled.

![Options for controller.json](../images/screenshots/08-file-options-218d6cc6a81f.png)

## Know which Trash will be emptied

A red warning explains that FileExplorer and Desktop Mode share the same Trash.
The dialog was cancelled after this screenshot; no user files were deleted.

![Empty Trash confirmation with red warning](../images/screenshots/09-trash-warning-b01f844c3656.png)

## Customize the appearance

Choose an accent color, background opacity and text size in the compact Decky sidebar.
Reset appearance restores the default look without changing folders or connections.

![Appearance settings and color preview](../images/screenshots/11-appearance-settings-ae2cddb1a94a.png)

## Select and copy text with the controller

Hold **RT/R2** while moving in the text to select a fragment or several lines.
**View/Select** copies into the system clipboard. Use Steam's keyboard to paste,
and **Menu/Start** to undo an edit.

![Multiline text selection with native controller glyphs](../images/screenshots/12-text-selection-76faa3beda67.png)

## View pictures in Gaming Mode

Press **A** to open an image. Use **left/right** or **L1/R1** to switch pictures
without returning to the file list. The header shows the filename, image counter,
dimensions and file size. The lake artwork was generated for this demonstration;
the screenshot is an unedited capture of the installed SteamOS plugin.

![Aurora landscape inside FileExplorer's image viewer](../images/screenshots/13-image-viewer-b9b28a6b4bd2.png)

## Look inside an archive of pictures

The image viewer also works inside archive folders. Only the chosen image is
extracted temporarily, and the source archive is unchanged. The second capture
shows another image selected from the demonstration ZIP.

![Previewing an image directly from the demonstration ZIP](../images/screenshots/14-archive-image-ef37a7c65758.png)
