[Manual home](Home.md)

# Network shares

Connect directly to SMB shares on a NAS or another computer, or browse network
shares already mounted by SteamOS. Either panel can point to a network location.

## Find an SMB server automatically

1. Select the panel where the share should open.
2. Open **Locations → Add SMB share**.
3. Choose **Find servers** and wait for the results.
4. Select a server to fill **Server / IP** in the connection form.

![Real SMB discovery results with server names and local IP addresses](../../images/screenshots/10-smb-discovery-be509db9bd73.png)

This screenshot shows seven real results from the test LAN. Names appear when
the service advertises them; otherwise the list shows the local IP address.
Finding a server does not automatically log in or guarantee access to its shares.

Discovery combines advertised SMB services with a TCP 445 check on directly
connected private IPv4 networks. It checks up to 512 addresses; on networks
larger than /24 it restricts the route scan to the computer's local /24.
Other subnets, VPN routes and servers hidden by a firewall may require manual entry.
No login details are sent by the discovery scan.

## Choose a share and connect

1. If the server needs authentication, enter **Username**, **Password** and, if
   required, **Domain** before choosing **List shares**.
2. Select a share from the list, or type its exact name in **Share name**.
3. Optionally set a **Display name** and enable **Remember connection**.
4. Choose **Connect**. The share opens in the panel you selected.

![SMB connection form](../../images/screenshots/07-network-share-982884978b24.png)

The form screenshot uses `nas.example` and `Games` as example values. For your
connection, **Server / IP** takes a hostname or IPv4 address without `smb://`;
**Share name** takes only the share name, not a complete path. Leave username and
password blank only for a server that allows guest access.

**List shares** and **Connect** contact the server you selected, using the login
details in the form. If share listing is unavailable but you know the share name,
enter it manually and try Connect.

## Remember or forget a connection

With **Remember connection** enabled, the share appears in Locations on later
sessions. Without it, the connection remains available only for the current
plugin session; a running worker already has the details needed for its job.

Use **Settings → Saved connections → Forget** to remove stored login details.
FileExplorer stores its own connection profiles in a private settings file. It
does not import passwords from KDE Wallet. Details about permissions and storage
are in [How it works](How-It-Works.md#smb-connections-and-credentials).

Direct connections use **SMB2 with NTLMv2 on TCP 445**. SMB1-only servers and
servers requiring SMB3 encryption are not supported by this version. Access still
depends on the server's account and share permissions.

## NFS, GVFS and other mounted shares

Mount these through SteamOS or Desktop Mode first. FileExplorer then accesses
the mounted path as an ordinary folder, using the existing operating-system
session. Mounted locations can appear in **Locations**; **Enter path** also lets
you open their absolute local path.

FileExplorer does not create NFS mounts or change `/etc/fstab`. Keep the mount
available until the operation completes. Direct SMB deletion is permanent;
mounted paths use the local Trash route, which can refuse the operation if that
location does not support Trash.

## Mounts across SteamOS updates

FileExplorer does not manage boot-time mounts. If a drive or share must mount
automatically after a reboot, configure it in SteamOS. Custom `/etc/fstab`
entries can disappear during SteamOS atomic updates. The documented alternative
is an enabled systemd `.mount` unit under `/etc/systemd/system`, with network
credentials stored privately under `/home` instead of an unprotected `/etc` file.
On SteamOS, use canonical paths such as `/var/mnt/...` in the unit, since `/mnt`
can be a symlink.

The [SteamOS NVIDIA mount guide](https://github.com/60plus/SteamOS_Nvidia_Installer/wiki/Updates-and-recovery#keeping-extra-drives-mounted-across-updates)
contains templates and update-test results from
[issue #15](https://github.com/60plus/SteamOS_Nvidia_Installer/issues/15).
This setup is separate from FileExplorer's systemd **transfer workers**.
Direct SMB connections in FileExplorer do not need an operating-system mount.
