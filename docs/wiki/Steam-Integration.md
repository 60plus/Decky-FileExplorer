[Manual home](Home.md)

# Steam integration

## Add a non-Steam application

1. Open the folder containing the executable or script.
2. Focus the file and press **Menu / Start → Add to Steam…**. With a mouse, right-click the file.
3. Check the library name. For native applications without execute permission, enable **Allow this file to run**.
4. Choose **Add to Steam**. The shortcut appears in Steam's non-Steam library without restarting Steam.

Adding a shortcut does not run the file. Script shortcuts use their interpreter
and the script's folder as the working directory. The dialog recognizes EXE, COM,
BAT, CMD, SH, BASH, ZSH, FISH, PY, PL, RB, AppImage, RUN, BIN and executable native
files. The required interpreter must already be installed.

Windows applications may need a Proton version selected under the shortcut's
**Properties → Compatibility**. BAT/CMD scripts may also need Windows
`cmd.exe /c` in their launch configuration. Adding a shortcut alone does not
guarantee an application will run on SteamOS.

Direct SMB locations cannot be used as Steam launch targets. Copy the application
and its required files to a local folder first, or use a share already mounted as
a local folder. The mount must be available whenever the application starts.


| SteamOS PC | SteamOS handheld |
| --- | --- |
| [![Add a non-Steam shortcut on PC](../../images/screenshots/pc-add-steam-ac50c28e3484.png)](../../images/screenshots/pc-add-steam-ac50c28e3484.png) | [![Add a non-Steam shortcut on handheld](../../images/screenshots/handheld-add-steam-9869350e498b.png)](../../images/screenshots/handheld-add-steam-9869350e498b.png) |

## Open a game's folder

Select an installed game in the Steam library and press **Menu / Start**.
Choose **Open in FileExplorer** to open that game's folder. The action is also
available from the game's gear menu and supports non-Steam shortcuts.

While a game is running, open Steam's menu. In the game's column, choose
**Open in FileExplorer**, below **View game details**.

FileExplorer opens the game's folder in the left panel. The right panel keeps
its saved location. For non-Steam shortcuts, the executable's actual parent
folder is preferred; script launchers use their working folder. Steam games use
the installation folder reported by Steam.

If the drive is disconnected or the game is only available by streaming, the
plugin explains that the local folder is unavailable. This menu integration
uses Steam's own controls and is removed when the plugin unloads. Steam client
updates can change the internal menu component; ordinary FileExplorer functions
remain available if the menu integration cannot be installed.

| SteamOS PC | SteamOS handheld |
| --- | --- |
| [![Open the running application folder from Steam on PC](../../images/screenshots/pc-game-menu-48fe6dd10f5d.png)](../../images/screenshots/pc-game-menu-48fe6dd10f5d.png) | [![Open the running application folder from Steam on handheld](../../images/screenshots/handheld-game-menu-ee7e057ed9e2.png)](../../images/screenshots/handheld-game-menu-ee7e057ed9e2.png) |
