[Manual home](Home.md)

# Everyday use

## The two panels

The active panel is the source for file actions. The other panel is the destination
for copying or extraction. Both panels show their path, file list and selection
count; local folders also show free space.

On handhelds and smaller screens, FileExplorer fills the available space between
Steam's header and controller controls. Compact toolbars leave more room for files
while keeping your selected text size. Large displays retain the centered window.
The text editor and image viewer adapt to the same available space.

![Source and destination side by side](../../images/screenshots/01-two-panels-c446ee4897f4.png)

Open a folder with **A**. The **..** row and **B** go to its parent. At the
filesystem or share root, **B** closes FileExplorer. The toolbar's **Close** button
closes the window immediately, without cancelling a background transfer.

**Locations** changes the active panel. It includes Home, Downloads where present,
mounted drives and remembered SMB connections. **Enter path** accepts an absolute
local path, such as `/home/deck/Downloads`; use **Add SMB share** for a new SMB
connection.

## Controller reference

These names use Xbox / Steam Deck conventions. The on-screen legend uses Steam's
glyphs for the controller you are using.

| Button | In the file manager |
| --- | --- |
| D-pad / left stick up and down | Move through file rows and vertical menus |
| D-pad / left stick left and right | Move between controls placed side by side |
| L1 / LB | Focus the left panel |
| R1 / RB | Focus the right panel |
| A | Open a folder, archive, text file or image; confirm a control |
| B | Go back to the parent folder or dismiss a dialog |
| X | Select or deselect the focused file or folder |
| Y | Copy to the other panel; extract when browsing an archive |
| Start / Menu | Open file and folder options |
| View / Select | Open Locations |

The [text editor](Text-Editor.md) has its own legend: **A** edits a line,
**X** inserts one, **Y** saves the file and **R3** switches between text and toolbar.
The [image viewer](Image-Viewer.md) uses **left/right** or **L1/R1** to change
pictures in the current folder, and **B** to return to the file list.

## Select files

Press **X** on each desired item. A check mark and the selection count show what is
selected. If nothing is selected, a copy uses the focused item. Opening another
folder clears that panel's selection.

**Options → Select all** selects the visible entries. When a selection is present,
the same menu offers **Clear selection**. Hidden entries are not listed unless
**Show hidden files** is enabled; copying a selected folder still includes its
contents, including hidden files.

For mouse control, click a row to focus it, double-click to open it and click its
selection square to toggle it. Use **Refresh** after changes made by another app.

## File and folder options

![Options for a configuration file](../../images/screenshots/08-file-options-218d6cc6a81f.png)

| Option | What it does |
| --- | --- |
| Copy to other panel | Opens a confirmation with the destination path |
| Extract whole archive to other panel | Creates a new folder in a local destination |
| Rename | Renames one item; enter a name without path separators |
| Edit text file | Opens the small-file text editor |
| Move to Trash | Moves local items to the SteamOS Trash |
| Delete permanently | Deletes items on a direct SMB connection after confirmation |
| New folder | Creates a folder in the active panel |
| Locations / network shares | Opens the location chooser |
| Empty Trash | Opens the separate warning for the shared Desktop Mode Trash |

Unavailable actions are disabled, for example renaming an archive member or
starting a second operation while one is running. To move a file between folders
in this version, copy it, check the destination and then remove the source.

Next: [Copying and background jobs](Copy-and-Background-Jobs.md).
