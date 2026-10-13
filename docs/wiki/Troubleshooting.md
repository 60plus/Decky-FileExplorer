[Manual home](Home.md)

# Troubleshooting

Start with the message shown at the bottom of FileExplorer or in the current
dialog. A stopped operation can leave completed items in its destination; inspect
them before retrying.

## Installation and navigation

| Symptom | What to check |
| --- | --- |
| Plugin does not appear | Install the `FileExplorer-VERSION.zip` release asset, not a source-code archive. Check Decky finished installation. |
| A remembered folder no longer opens | Use Locations to choose Home or another available folder. Reconnect or mount the missing drive/share. |
| Hidden file is missing | Enable Settings → Show hidden files, then refresh or reopen the file manager. |
| An action is disabled | Check the selection, whether a job is running, and whether either panel is inside a read-only archive. |
| Permission denied | FileExplorer runs as the Steam user. Choose a writable location or correct access through the appropriate system/share settings. |
| Update does not offer a download | Select **Check for updates**, check the network connection and read any error shown. GitHub may temporarily limit requests. As a fallback, install the plugin ZIP from the [latest release](https://github.com/60plus/Decky-FileExplorer/releases/latest). |

## Handheld display and controls

| Symptom | What to check |
| --- | --- |
| Too few files or editor lines fit | Reduce Settings → Interface scale to 90% or 80%, then reopen FileExplorer. The outer window keeps its size. |
| Text is too small | Increase Text size or return Interface scale to 100%; reopen the window. |
| The editor toolbar uses too much room | Press L3 to hide it, including while Steam's keyboard is open. L3 shows it again; R3 reveals and focuses it. |
| I cannot reach the editor or player toolbar | Press R3, then navigate left/right. R3 again returns to the content. |
| Text selection does not work with RT | Hide Steam's keyboard first; while it is open, RT/R2 is its Enter action. |
| Controller hints appear twice or have disappeared | Settings → Controller legend selects Panel only, Steam bar only, Both or Hidden. Reopen FileExplorer to apply. |

The [handheld guide](Handheld-Guide.md) shows the controls and settings, and the
[handheld gallery](Handheld-Gallery.md) includes native captures at both 100%
and 80% interface scale.

## Copy or extraction problems

| Message or symptom | Next step |
| --- | --- |
| Another operation is already running | Reopen FileExplorer to view it. Wait, or use Cancel and wait for its final status. |
| Destination already exists | Rename the source or choose a destination without that name. Copies do not merge or overwrite existing items. |
| Progress remains at Preparing | Folder enumeration or a remote archive download may still be running. Check available local space and the network. |
| Background service could not start | The systemd user session must be available. Collect the service diagnostics below. No files are transferred when startup fails. |
| Background service stopped | A reboot, stopped session or worker failure may have interrupted it. Reconnect missing storage and use Options → Resume interrupted copy for a checkpointed copy. Extraction must be started again; nothing resumes automatically. |
| No notification | Notifications appear while the FileExplorer window is closed and need Steam and Decky running. Milestones already shown in the open window are not replayed. |
| Archive cannot be opened or extracted | Check the size limit, format, available local space and whether it is encrypted, multipart or contains rejected entries. |
| Cannot copy links or special files | Use another suitable tool for those items; this version copies regular files and folders. |

Remote archives and selected extraction require temporary
local storage. Free space on the destination alone is not sufficient.

## SMB connection problems

If **Find servers** returns nothing, try the server's IPv4 address manually.
Check that both devices can communicate and that the server accepts TCP 445.
Discovery is bounded and does not search every subnet or VPN route.

For **List shares** or **Connect** errors, check the username, password, optional
domain and share permissions. Type the hostname without `smb://`, and only the
share name in its own field. If listing is blocked, a known share name can be
entered manually. SMB1-only servers and mandatory SMB3 encryption are unsupported.

If a password changed, forget the old connection in Settings and add it again.
After a network interruption, reconnect and inspect the destination before
repeating an operation. An incomplete copy may leave a hidden
`.fileexplorer-*.partial` item; an interrupted editor save may report a backup.

## Text editor problems

- **Cannot decode:** choose the original encoding. Do not guess an encoding merely
  to make the error disappear; verify that the displayed characters are correct.
- **Invalid JSON:** correct the reported line and column, then save again. The
  failed save leaves the original file unchanged.
- **File changed outside the editor:** keep a note of your intended edits and
  reopen the current version before applying them.
- **Unsupported character:** the original encoding cannot represent the new text.
  Use an external editor if you need to intentionally convert the encoding.
- **Too large / binary file:** the editor supports regular text up to 512 KiB and
  10,000 lines. Use Desktop Mode for files outside those limits.

## Media playback

- **No A action:** the extension has no supported preview. For plain text, use Options → Edit file. PDF and Office document rendering is not included.
- **Cannot play this file:** reconnect an unavailable share or try another file. A container such as MKV can hold different codecs. Steam decodes supported codecs directly; system FFmpeg provides compatibility playback when available.
- **Compatibility playback is slow:** it converts video while playing, up to 720p/30 fps. Performance depends on the original codec, device and network.
- **Media inside an archive:** extract it to a local folder or SMB share before playing it.
- **No cover:** only embedded artwork is used. Missing, oversized or unreadable cover tags show a speaker icon.

## Trash problems

A location without working Trash support produces an error instead of a permanent
local delete. Use Desktop Mode to inspect that location. **Empty Trash** affects
the shared Desktop Mode Trash, including connected drives; it has no undo.

## Collect useful diagnostics

Include the FileExplorer version from **About**, SteamOS and Decky versions,
the action you took, the displayed error, and whether each panel was local, SMB
or inside an archive. A screenshot of the problem is useful.

For background-job problems, these read-only commands can be run as your normal
Steam user in Desktop Mode:

```sh
systemctl --user list-units --all 'fileexplorer-job-*'
journalctl --user -u 'fileexplorer-job-*' --since '30 minutes ago' --no-pager
```

Completed transient units may no longer appear in the unit list. The latest job
state is also kept under FileExplorer's Decky settings directory; on the tested
installation this is `/home/deck/homebrew/settings/FileExplorer/jobs`.

Do not attach `settings.json` or a running job's `request.json`: they can contain
SMB passwords. Prefer the error text and relevant log excerpt, checking any
private filenames before sharing. Submit reports through
[repository issues](https://github.com/60plus/Decky-FileExplorer/issues).
