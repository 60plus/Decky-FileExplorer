# Testing and validation

## Release 0.8.2

The ZIP contains 183 runtime files and is 2,312,844 bytes. The GitHub updater is
unchanged from 0.8.1.

SHA-256:
`467728523e4c6939334114b3c56cba416842d95258027da0918783c7cf8753d3`.

- 204 Python tests passed on the SteamOS PC and handheld. All eight JavaScript
  tests, TypeScript checking and the production build passed.
- Five real background jobs ran together: copy, move, pack, whole-archive
  extraction and selected extraction from an SMB RAR. Copied bytes matched the
  source, and each progress milestone was recorded once.
- Local and SMB rename and folder creation worked during a copy. Deletion and
  Trash checks used isolated test files. Running, queued and paused transfer
  paths remained protected from conflicting changes.
- Steam UI checks covered operation dialogs during copying, slow SMB RAR
  browsing across transfer completion, the taller options window and opening
  the correct Steam/non-Steam game folders from library menus on both devices.
  These checks used programmatic UI interaction, not physical controller input.
- All installed runtime files matched the ZIP on both devices, and installation
  preserved existing preferences.

## Release 0.8.1

FileExplorer 0.8.1 retains the built-in GitHub updater. Its ZIP contains
177 runtime files and is 2,238,384 bytes.

SHA-256:
`d8a7b3715bbc1a54b13bd7c4126020e1fdfe009ec4665729e092bc85756362f5`.

The sidebar navigation, shutdown, connection-error and failed-move fixes passed
179 Python tests, eight JavaScript tests, TypeScript checking and a production
build. Native navigation and shutdown checks ran on a SteamOS 3.8.28 Stable PC
using the initial backport package labelled 0.8.0.

The final 0.8.1 package changes only the version metadata and compiled version
label from that backport package. All 16 updater tests passed again. After
publication, the original updaters from 0.6.1, 0.6.3, 0.7.1, 0.7.9 and 0.8.0
recognized 0.8.1, downloaded the release ZIP and verified its exact bytes.
The 0.8.0 updater also prepared the download successfully; 0.8.1 did not offer
the same version again. These download checks did not install the package on
a device.

See the [validation report](MAIN-FIXES-2026-10-16.md) for artifact identities
and the scope of each hardware and package check.

## Release 0.8.0

Version 0.8.0 added the optional Support page and retained the GitHub updater.
Its ZIP contains 182 runtime files and is 2,306,466 bytes.

SHA-256:
`20804809de8a78a786925dc3909584689e40c3bcafe9c6bc256f0c21af44adf3`.

Checks on 15 October 2026:

- TypeScript checking and the production build passed. The frontend build
  matched the installed JavaScript and QR assets.
- All 16 updater tests passed against the extracted ZIP on Linux Python 3.12.
  Release fixtures confirmed compatibility with the 0.6.1, 0.6.3, 0.7.1 and
  0.7.9 updater implementations.
- All 182 installed files on the SteamOS PC matched the ZIP. Installation
  preserved the settings file and encrypted SMB connections.
- Support opened in Steam's native UI on PC. QR cards fitted the screen,
  loaded their bundled images and returned one level with Back.
- Local React layout checks at PC and handheld sizes covered all three support
  methods, clipboard values, clipboard failures, Back and opening the support
  URL. The QR payloads decoded correctly from the local preview images.
- Those layout checks used Decky component adapters. This release check did
  not include a native handheld run of Support.
- The 172 backend and dependency files were byte-identical to 0.7.9. The
  hardware scenarios below were not repeated for this UI addition.

## Release 0.7.9

The ZIP contains 179 runtime files and is 2,297,737 bytes. Its contents matched
the package installed on the SteamOS PC and ROG Ally. A frontend build also
matched the packaged JavaScript byte for byte.

SHA-256:
`f62af68ae6d317a34dd1f7a463dee1f607c4c11168607cfe44e8cf50d3614ec9`.

Release checks on 15 October 2026:

- TypeScript checking and the Rollup production build passed.
- All eight frontend tests passed, covering text selection, file classification
  and date formatting, including timezone and daylight-saving cases.
- The extracted package passed the Linux Python 3.12 suite: 170 tests ran,
  169 passed and one was skipped. The compatibility streaming/seek test needed
  system FFmpeg, which was absent from that container.
- Release fixtures confirmed that the original 0.6.1, 0.6.3 and 0.7.1 updaters
  accepted the ZIP's size, SHA-256, plugin identity and version.

The following hardware scenarios ran during development on 13-15 October.
They were not all repeated during release preparation.

### Interface and controller navigation

Steam's native UI and virtual controller input were used on a SteamOS PC and
ROG Ally. This coverage does not establish support for every physical controller
or replace testing on a physical Steam Deck.

- Back returned one level through Options, Locations, Rename, New folder,
  Trash, copying, moving, packing and extraction dialogs.
- Lists and menu columns wrapped at their ends. Selection advanced to the next
  file, and panel switching preserved the focused row.
- R3 reached the toolbar and transfer controls. L3 hid the toolbar. Cancel and
  Transfers remained reachable during systemd copies.
- Setup covered both profiles, editable settings, Back, cancellation, setting
  help, controller glyphs, layout and the three-second startup image.
- File dates matched filesystem timestamps. Sorting and focus persisted.
  ZIP timestamps and missing timestamps were checked; live SMB date sorting
  was checked on the PC.
- Scrollbars and aligned columns were checked with long and short lists,
  including 100% PC scale and 70%/100% handheld scale.
- Add to Steam and Open in FileExplorer worked through Steam's interface.
  The game-menu action opened the demo launcher's directory on both devices.

### Transfers, conflicts and recovery

Integration checks used generated temporary files and isolated SMB servers on
both devices. Coverage included:

- Five simultaneous systemd copies, queued batches, cancellation isolation and
  matching output hashes. Three parallel SMB copies used authenticated loopback.
- Browsing, text editing and media playback during copying, with five progress
  cards fitting the panel.
- Twenty conflict scenarios, including rename, backup, overwrite, cancellation,
  stale responses, concurrent jobs and the six-action interruption dialog.
- Keeping or removing partial files and recovering after worker termination.
  Final hashes matched. Moves continued from waiting name conflicts but did
  not resume partial cross-filesystem data after worker termination. Extraction
  and packing required restarting.
- A 1 GiB copy continuing after its client closed, plus extraction, moving and
  archive creation with verified output.
- Editor draft recovery without modifying the original file. Save rejected
  invalid JSON and preserved tabs and CRLF after a valid edit.

Interruption tests used controlled process termination and injected failures.
They were not physical battery-cut, drained-battery or reboot tests. Queue
pausing across boot IDs was covered by unit tests. Temporarily stopped workers
provided stable observations, not throughput measurements.

### SMB credentials

Both devices used user-scoped systemd credentials with TPM protection. Migration
preserved connection IDs, labels and passwords, verified decryption before
replacing settings, and left no plaintext password fields in active settings
or job JSON. Host-key-only credentials were also tested with TPM unavailable.

Fallback cannot recover a password bound to a lost or reset TPM. Programs running
as the same Steam user can request decryption. See
[Network shares](wiki/Network-Shares.md) for protection and recovery limits.

### Screenshots and notifications

On 15 October 2026, 104 screenshots were captured from the installed UI on both
systems. The two four-mode legend comparisons were retained. PC scenes used
100% scale with Steam-bar hints; handheld scenes used 70% with panel hints,
except where another setting was demonstrated.

Demo transfers supplied queue and progress displays. A 512 MiB ZIP extraction
with the window closed produced 25%, 50%, 75% and 100% notifications on both
devices. Screenshots are unedited Steam captures.

## Run the checks

Install the pinned frontend dependencies and Python runtime requirements:

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
node --test tests/editor-text.mjs tests/file-types.mjs tests/file-date.mjs
python3 -m pip install -r requirements.txt --target vendor
PYTHONPATH=vendor:. python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/package.py
```

Backend tests require Linux and libarchive. System FFmpeg enables optional
compatibility playback tests. Integration checks need a user-systemd session;
SMB scripts also need `impacket` in an isolated test environment:

```sh
PYTHONPATH=vendor:. python3 tests/smb_integration.py
PYTHONPATH=vendor:. python3 tests/systemd_integration.py
PYTHONPATH=vendor:. python3 tests/queue_integration.py
PYTHONPATH=vendor:. python3 tests/power_loss_integration.py
PYTHONPATH=vendor:. python3 tests/conflict_integration.py
```

Loopback SMB tests do not establish support for every NAS, domain or wireless
interruption. Mounted NFS paths use local filesystem operations; these checks
did not include a live NFS server. Checksums verify release bytes, not a separate
publisher signature. See [update verification](UPDATES.md).
