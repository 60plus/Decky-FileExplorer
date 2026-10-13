[Manual home](Home.md)

# How FileExplorer works

This page explains FileExplorer's implementation. For the buttons and everyday
workflow, start with [Everyday use](Daily-Use.md).

## From controller input to files

```text
Steam Gaming Mode + controller
    ↓ Steam focus navigation and controller glyphs
Decky sidebar / FileExplorer React window
    ↓ Decky callable request
Python backend running as the Steam user
    ├─ Local filesystem and existing OS mounts
    ├─ Direct SMB2 connections through pysmb
    ├─ Archive listings through system libarchive
    └─ Background job manager
           ↓ systemd user service
        Independent Python worker → source / destination
           ↓ durable progress
        Open window or native Steam notifications
```

The React interface keeps separate locations, focus and selections for the two
panels. Steam's focus navigation handles rows and horizontal controls; Steam also
supplies the controller glyphs and on-screen keyboard. The plugin backend exposes
explicit operations such as list, connect, read text, save text and start a job.
It runs without Decky's root flag, so access is limited to the Steam user's
filesystem and share permissions.

## PC and handheld layout

PCs and handhelds use the same frontend and backend. The interface responds to
Steam's available viewport: compact windows fill the space between the system
header and controller footer, while large viewports use a centered panel.
Interface scale changes the controls and content inside that space; text size
is a separate setting.

The editor tracks Steam's on-screen keyboard and keeps the active line visible
above it. L3 hides the toolbar for more text space; R3 moves focus between content
and toolbar. The optional panel legend mirrors Steam's active hints, so its labels,
order and controller glyphs match the Steam bar. Hidden legends do not disable
the controls, and their visibility changes are removed when FileExplorer closes.
See the [handheld guide](Handheld-Guide.md) for the settings and examples.

## Background job lifecycle

1. The backend validates the operation and refuses a second job while one runs.
2. It creates a private job directory and copies the worker code and Python
   dependencies there. The worker therefore does not depend on files being
   replaced in the installed plugin directory during an update.
3. `systemd-run --user` starts a transient service named
   `fileexplorer-job-<id>`, running the system Python interpreter.
4. The worker reads the request, removes that temporary request file and performs
   the operation independently of the Decky UI.
5. It atomically updates progress on disk about every 200 ms, recording completion,
   failure or cancellation. The open window polls the status every 500 ms.

The manager stores the current job ID, state and notification acknowledgements
under the plugin's settings directory. Reopening the UI or reloading the plugin
reads that state instead of starting the transfer again. Older completed job
directories are pruned as new jobs begin, keeping the most recent five.

A reboot or stopped user session interrupts the worker. The manager detects a stale running state when its systemd service is no longer active. Copies additionally record an append-only checkpoint journal and a credential-free plan. The latest interrupted copy can be resumed explicitly; nothing resumes automatically. Extraction has no resume journal.

## Copy staging, speed and notifications

The worker estimates the selected data before copying. Each top-level item is
written under a temporary name in the destination and renamed only after that
item is complete. Existing destination names are refused. On failure, earlier
completed items and resumable partial copies remain. Resume compares every saved byte with the source before appending, checks source size and modification time, and verifies completed-file hashes. Start again creates a separate destination folder and leaves previous output intact.

Resumable SMB-to-SMB copies relay bounded chunks in memory. Selected archive extraction stages its output locally before copying it to the final destination. Progress counts those work stages; speed is a recent rate of bytes
processed, rather than a promise about disk or network throughput.

The worker records the **25 / 50 / 75 / 100** milestones. A plugin-level notifier
polls once per second and uses Decky's native toast API with the FileExplorer
icon. When the file-manager window is visible, milestones are acknowledged
without a toast. When it is closed, pending milestones, errors and cancellations
are displayed. Acknowledgements prevent already reported events being replayed
after a normal plugin reload. Steam and Decky are required to show notifications;
the independent worker itself does not need the window to remain open.

## Archive browsing and extraction

An archive location combines the source archive and an internal member path.
The backend builds a manifest for listing folders without writing into the
archive. It caches up to eight manifests and checks source size and modification
time before reusing one. Remote archives are temporarily downloaded for reading.

The system libarchive handles decoding ZIP, RAR, 7z and TAR formats. The wrapper
rejects absolute paths, parent traversal, links and special files, and applies
entry-count and size limits. It validates archive entries even when only part of
the archive was selected. Selected contents are staged locally and then passed
through the ordinary copy path. Whole-archive extraction uses a temporary folder
in the local destination before publishing the completed folder.

## SMB connections and credentials

Discovery reads directly connected private IPv4 routes, checks advertised
`_smb._tcp` services when Avahi is available and probes TCP 445 with a bounded
scan. It does not authenticate. Share listing and connection happen only for
the host chosen in the connection form.

The virtual filesystem uses `pysmb` for direct SMB2 connections with NTLMv2.
Remembered profiles are stored in `settings.json`; the settings directory has
mode **0700** and the file **0600**. Passwords are omitted from state returned
to the UI. These permissions restrict access by other users; they do not encrypt
credentials against programs running as the same Steam user.

Session-only profiles stay in backend memory. A job receives only the profiles
needed for its source and destination through its private temporary request file.
The worker deletes that file after loading it, retaining credentials in memory
while the job runs. Mounted shares instead use the operating system's existing
mount and session. FileExplorer does not read KDE Wallet or manage `/etc/fstab`.

## Image preview

The viewer takes the current panel's image entries in their displayed order and
loads one image at a time. A stale response after switching images is ignored.
The backend bounds reads to 20 MiB, checks raster headers and rejects dimensions
above 40 megapixels or 16,384 pixels per side before sending the original bytes
as a raster data URL to Steam's browser. Chromium handles the final decoding;
a decode failure is shown in the viewer without preventing further navigation.

Local reads reject symbolic links and non-regular files. SMB reads use the same
virtual filesystem with a bounded output buffer. An archive preview validates
the manifest, extracts only the selected image into a private temporary directory
and cleans up after reading. Remote archives are first downloaded temporarily.
The source image and archive are never rewritten.

## Audio and video playback

The player opens one file at a time using an unguessable, revocable URL on a loopback-only HTTP server. The server supports byte ranges for seeking; local files are held by descriptor and SMB reads use bounded offsets. Paths and credentials are not put in media URLs. Closing the player revokes access and stops conversion processes. There are at most four sessions, with inactive access expiring after six hours.

Steam decodes supported audio and video directly. If decoding fails and system FFmpeg is available, the server transcodes on demand to WebM with VP8/Opus, capped at 720p and 30 fps. Seeking restarts conversion at the requested time. No permanent converted copy is written. A bounded system ffprobe call supplies duration for formats Steam cannot inspect. These subprocesses use the same cleaned environment as background workers.

TinyTag reads embedded audio artwork through a seekable view limited to 8 MiB of metadata reads. Cover bytes pass the raster checks used by image preview. Missing or invalid artwork falls back to a speaker icon.

## Text preservation and saving

The editor reads the original bytes, records a SHA-256 revision, encoding, BOM
and line-ending information, then presents normalized lines to the UI. Saving
compares the revision with the current file to detect external changes. It
reconstructs line endings, uses the original encoding with strict character
conversion and preserves the BOM. It does not run a formatter or serialize a
parsed document back to text. JSON is parsed only to validate syntax.

For local files, it writes and flushes a temporary file beside the original,
copies file metadata and checks the original again before replacement. For SMB,
it uploads a temporary replacement, checks the original, renames the original
to a backup and then installs the replacement. The backup is removed after
success; an interrupted remote save can require recovery from the reported
backup. These checks detect ordinary conflicts but are not a distributed lock
against other writers.

## Editor, keyboard and clipboard

The editor uses Steam's native multiline text input and keyboard handle. It
measures the keyboard in the editor window's own document and resizes the complete
panel into the available space, leaving room for Steam's top bar. Scrolling keeps
the active line visible. Hiding the keyboard returns to controller cursor control.
R3 transfers Steam's navigation focus between the text and toolbar while retaining
the cursor. It can also hide the keyboard and focus the toolbar; Down returns to text.

The cursor and selection are text offsets. RT with directions extends the selection
across lines; horizontal movement does not split UTF-16 surrogate pairs. Copy uses
the native document clipboard command also used by Steam's own text fields. Paste
is Steam's existing keyboard action. There is no plugin clipboard or background
clipboard service. Undo retains up to 30 text-and-cursor snapshots in memory;
typing in one keyboard session is grouped into one step, and saving clears them.

The native keyboard owns its controller mappings while open, including RT as
Enter. FileExplorer's RT-selection and Menu-Undo mappings apply after hiding it.
These Steam UI integrations are checked against the installed client; a future
Steam UI change may require a compatibility update.

## Trash uses the desktop's storage

Local removal uses the freedesktop Trash workflow, normally through GIO.
If Trash is unavailable, FileExplorer reports the error instead of permanently
deleting the source. Direct SMB removal is a separate, explicitly confirmed
permanent-delete operation.

Empty Trash enumerates the current user's home and mounted-drive Trash roots.
Linux directory descriptors and no-follow checks protect traversal; symlinks
inside Trash are removed without following their targets. The operation uses
the same storage as Desktop Mode, which is why its confirmation names both.

## GitHub update lifecycle

The startup notifier asks the backend to check the latest stable GitHub release.
A lock and atomic record keyed to Linux's boot ID prevent duplicate notices across
plugin and Steam reloads. Failed checks retry quietly after five minutes. The
Settings toggle disables automatic checks; manual checks work independently.

The Update page displays release notes before downloading. The backend pins the
repository and asset URLs, validates the checksum and GitHub's asset digest when
available, bounds download and expanded sizes, and checks ZIP paths, plugin identity
and version. It saves the verified ZIP in private settings storage, then the UI
passes its file URI and SHA-256 to Decky's installation prompt. The plugin does not
replace itself or install anything without confirmation. Existing job workers use
their own copies of runtime files, so a plugin update does not stop their transfers.

## Source map

| Component | Source |
| --- | --- |
| Sidebar, Settings, Update and About | [src/index.tsx](../../src/index.tsx) |
| Two-panel navigation and operations | [src/Explorer.tsx](../../src/Explorer.tsx) |
| Text editor and native keyboard | [src/Editor.tsx](../../src/Editor.tsx), [keyboard layout](../../src/useKeyboardSpace.ts) |
| Text selection and movement | [src/editorText.ts](../../src/editorText.ts) |
| Image viewer and bounded raster reads | [src/ImageViewer.tsx](../../src/ImageViewer.tsx), [images.py](../../fileexplorer/images.py) |
| Media player and ranged streaming | [src/MediaPlayer.tsx](../../src/MediaPlayer.tsx), [media.py](../../fileexplorer/media.py) |
| Copy checkpoint verification | [copy_resume.py](../../fileexplorer/copy_resume.py) |
| Shared controller hints | [src/Legend.tsx](../../src/Legend.tsx) |
| Appearance settings | [src/appearance.tsx](../../src/appearance.tsx) |
| Decky backend routes | [main.py](../../main.py) |
| Operations and progress | [service.py](../../fileexplorer/service.py) |
| Independent jobs and worker | [jobs.py](../../fileexplorer/jobs.py), [worker.py](../../fileexplorer/worker.py) |
| Local and SMB filesystem access | [vfs.py](../../fileexplorer/vfs.py) |
| Archive reader and extraction | [archive.py](../../fileexplorer/archive.py) |
| Network discovery | [discovery.py](../../fileexplorer/discovery.py) |
| Text decoding and saving | [editor.py](../../fileexplorer/editor.py) |
| Shared Trash handling | [trash.py](../../fileexplorer/trash.py) |
| Native notifications | [notifications.tsx](../../src/notifications.tsx) |
| GitHub updates and boot deduplication | [updates.py](../../fileexplorer/updates.py), [Updates.tsx](../../src/Updates.tsx) |

See [verification notes](../TESTING.md) for automated, protocol and installed-UI
checks, including their limits. [Update verification](../UPDATES.md) documents the GitHub updater.
