# Documentation

The manual source is in [docs/wiki](wiki/Home.md). The online version is the
[GitHub wiki](https://github.com/60plus/Decky-FileExplorer/wiki).

The README and manual share screenshots from `images/screenshots`. Image filenames
include a short content hash so that updated screenshots use new URLs.

## Update screenshots

After replacing screenshots, update their filenames and document links:

```sh
python3 scripts/refresh_screenshots.py
python3 scripts/refresh_screenshots.py --check
```

The second command checks the filenames without modifying files.

## Export the manual

Clone the wiki separately and export the Markdown pages:

```sh
git clone https://github.com/60plus/Decky-FileExplorer.wiki.git ../Decky-FileExplorer.wiki
python3 scripts/export_wiki.py ../Decky-FileExplorer.wiki
git -C ../Decky-FileExplorer.wiki diff --check
git -C ../Decky-FileExplorer.wiki diff
```

The exporter converts local page links and heading anchors into wiki URLs. Image
and source links point to the repository. It updates the exported files without
creating commits or pushing changes.

For an existing wiki checkout, pull its latest changes before exporting. Commit
and push the exported pages after checking the diff. New screenshots must also
be committed to the main repository so the wiki can display them.
