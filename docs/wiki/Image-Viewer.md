[Manual home](Home.md)

# Image viewer

Open pictures directly in Gaming Mode. FileExplorer previews **BMP, PNG, JPEG,
GIF and WebP**, fitted to the available space while keeping the image's aspect
ratio. On handhelds and smaller screens, the viewer fills the space between
Steam's header and controller controls.

## Open and browse pictures

1. Open a folder containing pictures in either panel.
2. Focus an image and press **A**. Mouse users can double-click it.
3. Use **left/right** on the D-pad or left stick to change the image. **L1/R1**
   or **LB/RB** does the same. The Previous and Next buttons also work with a mouse.
4. Press **B** or choose **Close** to return to the file list.

| SteamOS PC | SteamOS handheld |
| --- | --- |
| [![Image preview on PC](../../images/screenshots/13-image-viewer-b9b28a6b4bd2.png)](../../images/screenshots/13-image-viewer-b9b28a6b4bd2.png) | [![Image preview on handheld](../../images/screenshots/handheld-06-image-34c223c97b74.png)](../../images/screenshots/handheld-06-image-34c223c97b74.png) |

The header shows the filename, its position in the folder's image list, dimensions
and file size. The viewer uses the panel's current sort order and hidden-file
setting. Folders and unrelated files are skipped; after the last picture it wraps
to the first. A folder with one image simply keeps that image open.

## Pictures in archives and network folders

The same controls work on direct **SMB shares**, existing operating-system mounts
and inside supported **archives**. Open the archive with **A**, enter the folder
containing pictures and press **A** again on the image. Left/right stays within
that archive folder.

| SteamOS PC | SteamOS handheld |
| --- | --- |
| [![Image inside an archive on PC](../../images/screenshots/14-archive-image-ef37a7c65758.png)](../../images/screenshots/14-archive-image-ef37a7c65758.png) | [![Image inside an archive on handheld](../../images/screenshots/handheld-07-archive-image-99f769bea171.png)](../../images/screenshots/handheld-07-archive-image-99f769bea171.png) |

Previewing leaves the source unchanged. An archive preview temporarily extracts
only the selected image and cleans up that temporary file. An archive stored on
SMB is downloaded temporarily for reading, so opening a large remote archive can
take longer than opening a standalone picture. To keep a copy, return to the file
list and use the ordinary **X** selection and **Y** copy/extract controls.

## Supported files and limits

Each image can be up to **20 MiB**, **40 megapixels** and **16,384 pixels on either
side**. The backend identifies the raster format from its contents; the file
extension determines whether **A** offers the image viewer. Supported extensions
include `.bmp`, `.png`, `.apng`, `.jpg`, `.jpeg`, `.jpe`, `.jfif`, `.gif` and `.webp`.
Steam's browser performs the final decoding and any supported animation.

SVG, TIFF, HEIC and AVIF are not supported. Symbolic links and special files are
not previewed. If an image is damaged or uses unsupported encoding, the viewer
shows an error and still lets you move to the next picture.

These are real screenshots of the installed plugin. The lake and coastal artworks
inside the viewer were generated for the demonstration; the interface and button
glyphs were captured from SteamOS. See [How it works](How-It-Works.md#image-preview).
