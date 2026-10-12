[Manual home](Home.md)

# Text editor

Edit small text files such as **TXT, CFG, INI, JSON, XML and scripts** directly in
Gaming Mode. The editor works with local files and direct SMB shares. It edits
text lines without automatically formatting or rewriting the document structure.

## Edit text above the keyboard

1. Focus a text file and press **A**, or choose **Options → Edit text file**.
2. Move up or down to the line you want. Left and right move the cursor.
3. Press **A** to edit the document with Steam's on-screen keyboard.
4. Hide the keyboard to return to the editor's cursor and selection controls.
5. Press **Y** or choose **Save file** to write the file.

![Text editor with line numbers, active line and file encoding](../../images/screenshots/03-text-editor-d668bc2ac194.png)

The **whole editor panel shrinks above Steam's keyboard**, keeping the toolbar,
active line, nearby text and status visible. The text scrolls as the cursor moves.
There is no separate line-editing popup. You can edit and paste multiple lines.

On handhelds, **L3** hides the toolbar to show more lines, even while the keyboard
is open. Press L3 again to show it; **R3** reveals and focuses it. For smaller
controls in the same window, change **Interface scale** in Settings and reopen
the editor. See the [handheld examples](Handheld-Gallery.md).

![Complete editor panel above Steam's on-screen keyboard](../../images/screenshots/04-keyboard-34fba006255f.png)

## Select, copy and paste

With the keyboard hidden, hold **RT / R2** and move the D-pad or stick to extend
the selection. You can select part of a line or continue across several lines.
Release the trigger to keep the selection, then press **View / Select** or choose
**Copy text**. If nothing is selected, Copy text copies the current line.

![Selecting several text lines with controller controls](../../images/screenshots/12-text-selection-2b7cce3b86f0.png)

Move to the destination, press **A** and use **Paste** on Steam's keyboard.
Pasting replaces selected text or inserts at the cursor. FileExplorer uses the
system clipboard; it has no separate clipboard or second Paste implementation.
With a physical keyboard, standard text selection and **Ctrl+C / Ctrl+V** work
inside the text input, and **Ctrl+Z** invokes the editor's Undo.

While Steam's keyboard is open, its own controller mappings apply: **RT / R2 is
Enter**. Hide it before using RT with directions to select text in FileExplorer.

## Editor controls

Press **R3** (click the right stick) to move from the text to the top toolbar.
Use left/right to reach Edit text, Insert line, Delete line, Copy text, Undo,
Save file or Close, then press **A**. **R3** again, or **Down**, returns to your
cursor and selection. If Steam's keyboard is open, R3 hides it and focuses the
toolbar. Moving Up from the first line also reaches the toolbar.

| Control | Action |
| --- | --- |
| Directions | Move the cursor; Up at the first line reaches the toolbar |
| R3 / right-stick click | Switch between text and toolbar; hide the keyboard when entering the toolbar |
| L3 / left-stick click | Hide or show the toolbar, including while the keyboard is open |
| A / Edit text | Open Steam's keyboard at the cursor |
| RT / R2 + directions | Extend a text selection with the keyboard hidden |
| View / Select / Copy text | Copy the selection, or the current line |
| X / Insert line | Insert a line below it, with the same indentation |
| Y / Save file | Save the pending changes |
| Delete line | Remove the selected line |
| Menu / Start / Undo | Undo a recent edit; up to 30 in-memory changes are retained |
| B / Close | Leave the editor; unsaved changes require a discard confirmation |

**Typing or hiding the keyboard does not save the file.** The header shows
**Unsaved changes** until you save. Each keyboard editing session is one Undo
step; line insertion and deletion have their own steps. Saving clears Undo history.
Steam's glyphs follow the active controller; the names above use Xbox-style labels.

## What happens to formatting

Spaces, tabs, blank lines, existing line endings, the final newline, original
encoding and byte-order mark are retained. Mixed LF, CRLF and CR endings are
tracked; inserted lines use the file's prevailing line-ending style. Your
intentional text changes, line insertions and deletions still take effect.

JSON receives a syntax check before saving. An invalid JSON save is refused and
the reported line is brought into view. Other formats keep their text layout,
but have no format-specific syntax validator. Preserving layout does not check
whether an edited CFG, XML or script is valid for the program that reads it.

## Encodings and limits

UTF-8 and BOM-marked UTF-16 are detected automatically. If decoding fails, select
the file's original encoding from the offered choices: UTF-8, UTF-16 LE/BE,
CP1250, CP1252 or Latin-1. Characters that cannot be represented in the original
encoding are refused instead of being silently replaced.

The editor accepts regular text files up to **512 KiB** and **10,000 lines**.
Binary files, symbolic links and UTF-32 are not supported. Files inside archives
must be extracted first.

If the file changed outside FileExplorer after opening it, saving is refused.
Keep a note of the edits you need, reopen the current file and apply them there.
For interrupted SMB saves, inspect any backup path named in the error before
retrying. See [How it works](How-It-Works.md#text-preservation-and-saving).
