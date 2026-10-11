# GitHub updates

**FileExplorer → Update → Check for updates** queries the latest stable release
from [60plus/Decky-FileExplorer](https://github.com/60plus/Decky-FileExplorer/releases/latest).
It shows the installed version, available version, download size and release notes.
**Download and install** downloads and verifies the plugin ZIP before opening
Decky's native installation prompt. Installation requires confirmation there.

## Startup check

**Settings → Check for updates at startup** is enabled by default. After Decky loads,
the plugin checks GitHub and displays a FileExplorer notification when a newer
stable version is available. A successful check is recorded against Linux's
`/proc/sys/kernel/random/boot_id` in the plugin settings directory.

Reloading the plugin or Steam in the same OS boot does not repeat the check or
notification. A new OS boot allows another check. Network failures retry quietly
after five minutes; they are not recorded as successful checks. Turning the option
off stops automatic checks and notifications. Manual checks remain available and
never produce an extra startup toast. Opening Update does not install anything.

## Download verification

- Only the fixed repository's latest stable release is accepted; drafts,
  prereleases and invalid version tags are refused. A missing release is reported
  separately from an up-to-date installation.
- The release must include `FileExplorer-VERSION.zip` and the matching
  `.zip.sha256` file at the expected release URLs. If GitHub supplies an asset
  digest, it must also match. HTTPS verification uses SteamOS's trust store.
- Downloads are bounded to 32 MiB. ZIPs are limited to 10,000 entries and 128 MiB
  expanded size. Absolute paths, traversal, duplicate paths, links and special
  files are rejected. Package identity, version and required files are checked.
- The verified ZIP is stored privately in the plugin settings directory. Decky's
  native installer receives its local URI and pinned SHA-256 checksum.
- Network and verification failures leave the installed plugin untouched. The
  normal ZIP installation method remains available as a fallback.

Settings and remembered connections live outside the plugin directory. Running
copy/extraction jobs have their own worker code and continue through plugin
replacement. A reboot still interrupts them. There is no automatic installation
or kernel-module compatibility check.

The checksums verify bytes delivered by the trusted GitHub repository over HTTPS;
they are not a separate publisher signature.

## Release assets

Build with `pnpm build`, then run `python3 scripts/package.py`. Attach the resulting
plugin ZIP and SHA-256 sidecar to the corresponding stable release. The package
version, release tag and asset filenames must agree. Publish both assets before
making the release public. Installation documentation links to **latest** instead
of pinning a version number.
