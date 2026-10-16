# FileExplorer 0.8.1 fixes and validation

Version 0.8.1 fixes sidebar navigation, plugin shutdown and transfer errors.
The built-in GitHub updater remains available, including manual installation
and the optional once-per-boot update notification.

## Changes

- Up reaches Decky's header arrow from the plugin home page, Settings, Update,
  Support and About. Confirm exits to the plugin list. Back on a child page
  returns one level and restores the matching menu selection.
- Shutdown finishes synchronously before Decky's closed RPC socket can prevent
  further event-loop callbacks. Detached transfer workers remain independent.
- Connection resets, broken pipes and socket timeouts show readable errors.
  Permission, missing-file, disk-full and read-only errors remain distinct.
- A failed cross-filesystem move removes empty staging directories while keeping
  nonempty partial data and the source available for recovery.

## Release package

`FileExplorer-0.8.1.zip` contains 177 runtime files and is 2,238,384 bytes.
Its SHA-256 is:

`d8a7b3715bbc1a54b13bd7c4126020e1fdfe009ec4665729e092bc85756362f5`.

The updater backend, Update component and updater regression tests are unchanged
from 0.8.0. FileExplorer's test suite and shutdown fixtures are not included in
the plugin ZIP.

## Automated checks

The fixes passed 179 Python tests with zero skips, including all 16 updater tests,
failed-move recovery, five connection-error checks and shutdown regressions that
distinguish the previous hanging implementation from the fix. TypeScript
checking, the production build and eight JavaScript tests also passed.

These checks initially used a package labelled 0.8.0. The final 0.8.1 package
changes only `package.json` and the compiled version label in `dist/index.js`;
the other 175 runtime files are byte-identical. TypeScript, the build and all
16 updater tests passed again for 0.8.1.

An isolated update test used the final ZIP with a simulated release response.
The unchanged updater recognized 0.8.1 from an installed version of 0.8.0,
verified and cached the exact archive, and did not offer the same version when
0.8.1 was already installed. This check did not use the network or install the
ZIP on a device.

Evidence: [build](evidence/main-backport-20261016/build.json),
[backend tests](evidence/main-backport-20261016/unit-tests.log),
[version and package comparison](evidence/main-backport-20261016/version-081.json),
[updater tests](evidence/main-backport-20261016/updater-081-tests.log).

## Native SteamOS checks

The native run used a SteamOS 3.8.28 Stable PC with Decky Loader 3.2.10 and the
initial package labelled 0.8.0. All 177 installed runtime files matched that
package. Its SHA-256 was
`27474aaf2ae820ec8488963a7422efea8dd5a30e72b0b90537e8ea4df4acc185`.

- Controller navigation passed on all five sidebar pages.
- The Update page and backend read the live GitHub release as 0.8.0 and correctly
  reported no newer version. Disabling the startup check suppressed its notification.
- FileExplorer opened normally. Reload with its media server active completed
  in 0.5 seconds, without SIGKILL. The old media URL became unavailable.

These native results cover the initial 0.8.0 backport package, not a separate
hardware run of the final 0.8.1 package. No native handheld run was included in
this particular check.

Evidence: [navigation](evidence/main-backport-20261016/pc/navigation.json),
[update checking](evidence/main-backport-20261016/pc/updater.json),
[shutdown](evidence/main-backport-20261016/pc/shutdown.json).
