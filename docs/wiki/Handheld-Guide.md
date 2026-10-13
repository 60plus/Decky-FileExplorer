[Manual home](Home.md) · [Handheld gallery](Handheld-Gallery.md)

# Using FileExplorer on a handheld

The same plugin works on a SteamOS PC and a SteamOS handheld. There is no separate
handheld download or layout switch. FileExplorer adapts to Steam's available
window size, including when using an external display. Installation and updates
use the same [Decky procedure](Installation.md).

On a smaller screen, the file manager and its viewers fill the space between
Steam's system header and controller bar. Larger viewports use a centered window.
The screenshots in this guide were captured on a **ROG Ally running SteamOS**;
they are real handheld captures, not scaled-down PC screenshots.

## Start with the two panels

Open **Decky → FileExplorer → Launch FileExplorer**. Press **L1 / LB** for the
left panel or **R1 / RB** for the right, then use the D-pad or left stick to move
through its files. **A** opens a folder or supported preview, **X** selects items,
and **Y** copies them into the other panel. **Menu / Start** opens file options.
Steam draws the glyphs for the active controller.

![Two file panels on a SteamOS handheld](../../images/screenshots/handheld-01-two-panels-c2e9c0a15101.png)

For archives, **A** enters the archive, **X** selects its contents and **Y**
extracts them into the other panel. See [Everyday use](Daily-Use.md) and
[Archives](Archives.md) for the complete controls.

## Make more room without shrinking the window

1. Open **Decky → FileExplorer → Settings → Interface scale**.
2. Choose **90%, 80% or 70%** for smaller controls, or **100%** for the default.
3. Reopen FileExplorer to apply the appearance settings.
4. Adjust **Text size** separately if file names or editor text need to be larger.

The outer window keeps its available size. A smaller interface scale fits more
content into it, including in the text editor and media player. For an initial
comparison, try 80%, then keep the size that is comfortable to read on your screen.

![Interface scale in the handheld sidebar](../../images/screenshots/handheld-17-scale-setting-0820bec3fafd.png)

Settings remain in Decky's compact sidebar. Use **up/down** to choose a setting,
**left/right** to change a slider and **X** to expand its explanation. Moving
up/down closes the explanation. **B** returns to FileExplorer's own menu.

## Choose where controller hints appear

**Settings → Controller legend** offers **Panel only**, **Steam bar only**,
**Both** and **Hidden**. Reopen FileExplorer after changing it. Hiding the hints
keeps controller actions available; closing FileExplorer restores Steam's normal
controls. The panel and Steam bar use the same active hints and order.

[![Four controller legend modes on a handheld](../../images/screenshots/handheld-legend-comparison-9301ecfb7c8a.png)](../../images/screenshots/handheld-legend-comparison-9301ecfb7c8a.png)

## Edit text above Steam's keyboard

Press **A** on a text file, move to the desired position and press **A** again
to open Steam's keyboard. The editor keeps its width and reduces its height to
fit above the keyboard, scrolling the active line into view.

- **L3** hides or shows the toolbar, including while the keyboard is open.
- **R3** reveals and focuses the toolbar; it hides the keyboard when necessary.
  Use left/right to choose an action. R3 again returns to the text.
- **Menu / Start** performs Undo. **Y** saves; hiding the keyboard does not save.
- With the keyboard hidden, hold **RT / R2 + directions** to select text and use
  **View / Select** to copy. Open Steam's keyboard and choose **Paste** to insert it.
  While that keyboard is open, RT/R2 belongs to its Enter action.

![Editor at 80 percent scale with the toolbar hidden above the keyboard](../../images/screenshots/handheld-scaled-keyboard-9542e7a3a971.png)

See [Text editor](Text-Editor.md) for formatting, encodings and limits.

## Pictures, audio and video

**A** opens a supported picture, audio or video file. In the image viewer,
left/right changes pictures. In the media player, **A** plays or pauses,
left/right seeks ten seconds, **L1/R1** changes files, **X** stops and **Y**
switches video fullscreen. **R3** reaches the media toolbar. **B** leaves
fullscreen first, then closes the player.

See [Image viewer](Image-Viewer.md), [Media player](Media-Player.md) and the
[supported formats](Supported-Formats.md). Those guides include handheld captures.

## Transfers and network shares

The handheld has the same [SMB discovery and connection controls](Network-Shares.md)
as the PC. Both panels can use a local folder or SMB share. A copy or extraction
continues when FileExplorer closes, with progress notifications at 25%, 50%, 75%
and completion. Keep the device awake and the source and destination available.
Closing the panel is different from shutting down, restarting or ending the
SteamOS user session, which interrupts the worker.

A failed background copy offers Resume, Start again, Cancel and Open FileExplorer.
See [Copying and background jobs](Copy-and-Background-Jobs.md) for recovery details
and actual handheld extraction notifications. For display or control issues, use
[Troubleshooting](Troubleshooting.md#handheld-display-and-controls).
