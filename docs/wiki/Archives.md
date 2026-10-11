[Manual home](Home.md)

# Archives

FileExplorer can browse **ZIP, RAR, 7z and TAR**, including common compressed TAR
files, using SteamOS's libarchive. You can open archives stored locally or on a
direct SMB share.

## Open an archive like a folder

1. Focus the archive and press **A**.
2. Open its folders with **A** and go up with **B** or **..**.
3. At the archive root, **B** returns to the folder containing the archive.

The panel marks the location **Archive • read-only**. Browsing does not modify the
archive. Rename, delete, editing and copying into an archive are unavailable.

![Selected profiles inside a ZIP archive](../../images/screenshots/02-archive-browsing-63332a829c46.png)

## Extract selected files or folders

1. Open a writable destination in the other panel. It can be local or SMB.
2. Return to the archive and select the desired entries with **X**.
3. Press **Y**, review the destination and confirm **Extract**.

A focused item is used when nothing is selected. A selected folder includes its
contents. Items appear by their selected names in the destination: selecting
`Profiles/Balanced.json` creates `Balanced.json`, while selecting `Profiles`
creates the `Profiles` folder with its contents.

The original archive remains unchanged. Extraction continues after closing the
window and uses the same [progress and notifications](Copy-and-Background-Jobs.md)
as copying.

## Extract the whole archive

Focus the archive in its containing folder, then choose
**Options → Extract whole archive to other panel**. This creates a new folder
named after the archive in a **local** destination. For example,
`Controller profiles.zip` becomes `Controller profiles`.

For a direct SMB destination, open the archive and extract selected entries
instead, or extract the whole archive locally and then copy the result.

## Space and format limits

- Selected extraction uses temporary local space before copying the selected
  contents to the destination. Remote archives are downloaded temporarily for
  reading, so allow local space as well as destination space.
- **Settings → Extraction limit** sets the maximum unpacked size per archive:
  10, 50, 100 or 500 GiB. The default is 100 GiB.
- Archives have a 100,000-entry limit. Unsafe paths, links and special files are
  rejected, including unsafe entries outside the selected subset.
- Password-protected and multipart archives are not supported. Some uncommon RAR
  methods may not be supported by the installed system library.
- To open an archive inside another archive, extract the inner archive first.
- Extract a text file before editing it. Archive contents are read-only.

An existing destination name stops extraction instead of overwriting it.
If extraction fails, read the status message and check the destination before
retrying. See [Troubleshooting](Troubleshooting.md).
