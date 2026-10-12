[Manual home](Home.md)

# Copying and background jobs

## Copy from one panel to the other

1. Open the source folder in one panel and the destination in the other.
2. Return to the source with **L1 / LB** or **R1 / RB**.
3. Select items with **X**, or focus one item to copy just that item.
4. Press **Y** or use **Copy** in the toolbar.
5. Check the displayed destination and confirm **Copy**.

Local-to-local, local-to-SMB, SMB-to-local and SMB-to-SMB copies are supported.
Copying a folder includes its contents. Only one background operation runs at a
time; this version has no job queue.

## Read the progress display

![Copy progress, transferred bytes and speed](../../images/screenshots/05-copy-progress-574110153ac8.png)

The bottom status shows the current phase, percentage, copied bytes and total,
live speed and current filename. Preparing a large directory or remote archive
can take time before byte progress begins.

Speed measures the work performed in the current operation, including temporary
staging where needed. Selected extraction and SMB-to-SMB copying have preparation
and destination-writing stages, so the overall percentage does not always equal
destination bytes divided by total bytes. The screenshot is a real transfer
reading, not a benchmark or promised speed.

## Close the window and carry on

Use **Close** to return to Steam. A separate systemd user service continues the
copy or extraction. Reopening FileExplorer reconnects to an operation that is
still running. Completed, cancelled and failed results stay in the bottom
status area for six seconds; reopening does not replay an old result.

![FileExplorer notification while its window is closed](../../images/screenshots/06-background-notification-6d5018c7b427.png)

While the window is closed, native notifications use the FileExplorer icon and
report **Copied / Extracted 25%, 50%, 75% and 100% • Done**. Failures and
cancellations are also reported. Steam and Decky must be running to display them.
When FileExplorer is open, progress stays in the window; milestones seen there
are not replayed as notifications after you close it.

These handheld captures show a real 4 GiB ZIP extraction continuing with the
panel closed. Long filenames may be shortened by Steam's notification layout.

![Background extraction at 25 percent](../../images/screenshots/handheld-21-extracted-25-b35a0844463c.png)

![Background extraction at 50 percent](../../images/screenshots/handheld-22-extracted-50-01021bece75b.png)

![Background extraction at 75 percent](../../images/screenshots/handheld-23-extracted-75-4a45a00f13d4.png)

![Background extraction at 100 percent](../../images/screenshots/handheld-24-extracted-100-c0755efe3ef4.png)

A plugin reload does not stop the worker. **Shutdown, reboot or a stopped user
session interrupts the operation**. Interrupted operations do not resume automatically.

## Existing files, cancellation and interrupted copies

Existing names are not overwritten or merged. If a selected item already exists
in the destination, the operation stops with a message. Rename the source or
choose another destination before trying again.

Press **Cancel** in the progress area to request cancellation. Wait for the final
status before disconnecting a drive. Items completed earlier stay in the
destination; cancellation does not roll them back.

Each top-level copy is staged under a hidden `.fileexplorer-*.partial` name and
renamed when complete. Normal cleanup removes an unfinished staging item. If a
connection failure or abrupt stop leaves one behind, reconnect, check that the
job has stopped and inspect the destination before removing that partial item.

Copies preserve file contents and folder structure. They are not metadata
backups: ownership, permissions, ACLs and extended attributes are not reproduced.
Copying symbolic links and special files is refused.

See [Archives](Archives.md) for extraction and
[How it works](How-It-Works.md#background-job-lifecycle) for the worker lifecycle.
