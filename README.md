# calibre-web-foliate-docker

**English** | [繁體中文](README.zh.md)

A Docker image of [Calibre-Web](https://github.com/janeczku/calibre-web) with its built-in epub.js reader replaced by a [foliate-js](https://github.com/johnfactotum/foliate-js) reader. It is the server-side version of the [calibre-web-foliate-mod](https://github.com/bgtsai/calibre-web-foliate-mod) Tampermonkey userscript: the same reader, built straight into Calibre-Web, so **no browser extension is needed** — every device that opens an EPUB on your Calibre-Web (desktop, phone or tablet, including iPhone and iPad) gets the new reader automatically. The interface supports Traditional Chinese and English.

![Settings panel (English)](docs/screenshot_en.png)

## Why this exists

Calibre-Web's built-in epub.js reader has limited typography controls (font size, letter spacing, line spacing, and margins are either missing or imprecise), and its interface can't be customized. foliate-js offers much finer typography control and deep visual customization. The userscript version swaps the reader in the browser, but needs Tampermonkey — which isn't available on iOS. This image does the swap on the server instead, while keeping Calibre-Web's existing bookmark sync and reading-progress mechanisms intact, so your usual workflow stays the same; only the rendering engine and interface change.

## Features

### Typography

- **Font size**: adjustable from 70% to 300%.
- **Letter spacing**: adjustable from −0.05em to 0.5em.
- **Line spacing**: adjustable from 1× to 5×.
- **Justification**: toggle full justification on or off.
- **Auto-hyphenation**: toggle automatic hyphenation on or off.
- **Disable ligatures**: turn off OpenType ligature substitution. Useful when a font uses the ligature mechanism for advanced purposes such as glyph-level character mapping (common in fonts that implement display-layer script conversion, e.g. simplified-to-traditional Chinese). When letter spacing is applied, such fonts may show uneven spacing within certain word groups; enabling this option normalizes spacing at the cost of disabling those substitutions.

> [!NOTE]
> If you notice certain words or character groups appearing noticeably tighter than the surrounding text when using a custom letter spacing, try enabling **Disable Ligatures**. This is most commonly seen with fonts that perform glyph substitution for script conversion.

> [!TIP]
> Every numeric field can be typed into directly or adjusted with the **− / +** buttons on either side (hold to repeat). After clicking a slider or number box to focus it, you can also fine-tune with the arrow keys or the mouse wheel: ↑→ / ↓← on sliders, ↑ / ↓ in number boxes. The step follows the decimal places of the current value (e.g. line spacing 1.25 steps by 0.01), but is never coarser than the field's own minimum step.

### Layout

- **Page flow**: switch between Paginated and Scroll mode.
- **Default margins**: left/right margins default to 120px, the same as the default tap-zone width, so the tap zones never cover the text.
- **Horizontal mode**: choose between Margin Priority (fixed margin) and Content Priority (fixed content width). In Content Priority mode, set the target content width in pixels; the margin absorbs any leftover space, keeping content width consistent when toggling fullscreen.
- **Vertical mode**: choose between Margin Priority (fixed margin) and Content Priority (fixed content height), with the same logic as horizontal mode.
- **Column control**: set the maximum number of columns and the gap between them in paginated mode. Both settings are automatically disabled in scroll mode (locked to 1 column).

### Themes and colors

- **Themes**: save your current typography, layout and color settings as a named theme and switch between them in one click. Themes can be reordered by drag-and-drop, and an existing theme can be overwritten with your current settings.
- **Apply Colors**: five built-in color presets (Follow System, Light, Dark, Sepia, Old Gold) plus any color schemes you save. Clicking a preset fills its colors into the custom text and background color fields and turns both on; the preset stays highlighted until you change a color or toggle a field yourself. While **Follow System** is highlighted, the colors are refilled automatically whenever your system switches between light and dark mode.
- **Custom colors**: text and background colors each have their own on/off switch — on applies the color you set, off keeps the book's own color. Colors can be entered in HEX / RGB / HSV format or chosen with the built-in color picker. **+ Save Current Color Scheme** stores the current pair; saved schemes can be renamed and reordered by drag-and-drop.
- **Toolbar and panels follow the page**: the toolbar, settings panel and table of contents switch between light and dark based on the actual background color of the page you're reading.

### Fonts

- Manually enter the name of a font already installed on your system, or upload a font file (.ttf / .otf / .woff) to embed it directly. Font files are stored in the browser's IndexedDB and persist across sessions. The font list supports drag-and-drop reordering.

### Page-turn shortcuts

- Fully customizable keyboard shortcuts for previous/next page. Multiple key combinations can be recorded per direction. Defaults: ← / Page Up for the previous page, → / Page Down for the next page.
- **Page-flip debounce**: set a minimum interval (in milliseconds) between consecutive page-turn triggers from the same shortcut, to prevent accidental double-flips.
- Pages can also be turned with the **mouse wheel** (over the page, or over the progress bar at the bottom).
- While the settings panel is open, page-turn shortcuts and wheel paging are paused so the arrow keys and wheel can adjust values instead; shortcuts keep working while the table of contents is open.

### Reading behavior

- **Precise page alignment** (on by default): after toggling fullscreen, resizing the window or changing typography settings, the **first character** of the page you were on stays exactly at the top of the new layout, and paging forward or back continues from there. Going back through the jump history (below) also returns to that exact first character. Jumping via the table of contents, a link or the progress bar restores the chapter's normal pagination. Automatically disabled in scroll mode.
- **Local reading progress**: reading position is saved locally on every page turn. On reopening a book, the reader restores the last position automatically.
- **Auto-sync to server**: optionally sync the local reading position back to Calibre-Web's server-side bookmark after a configurable idle period. Can also be triggered manually.
- **Auto-hide cursor**: the cursor hides automatically after a configurable number of seconds of inactivity, and reappears on mouse movement. It never hides while the pointer is over the toolbars, the table of contents, the settings panel or the jump button, and stays hidden when you move to the next chapter.
- **Auto-hide toolbar**: the toolbar and progress bar slide out of view after a few seconds of inactivity and reappear on hover or click.
- **Left/right tap zones**: clickable zones on the left and right edges of the screen for previous/next page navigation. The zone can be enabled (click-to-page) independently of its visual hint (whether the zone boundary is visible). Zone width is configurable in pixels. Automatically disabled in scroll mode.
- **Page-turn animation**: a brief directional chevron animation plays at the tap zone position on each page turn, confirming the direction. Color is configurable, or set to **Auto** (the default) to follow the text color actually shown on the page. Automatically disabled when the tap-zone visual hint is on.

### Jump history (back / forward)

Every way of jumping somewhere else in the book keeps its own history, with **↩ Back**, **↪ Forward** and a clear button. Each history can go back several steps (the number of remaining steps is shown on the icon), and going somewhere new drops the old "forward" path, like a web browser.

- **Footnotes and other in-book links**: after you click a link (e.g. a footnote marker like `[284]`), a small floating button appears at the top right. Click ↩ to return to where you were reading; once you're back at the starting point it disappears on its own. ✕ closes it early (with a confirmation).
- **Table of contents**: the buttons sit in the table-of-contents header and record chapter jumps made from the table of contents. The table of contents now stays open after you pick a chapter; close it with its ✕ or by clicking outside it.
- **Progress bar**: the buttons sit at the far left of the bottom bar and record jumps made by dragging the progress bar (one entry per release).

With precise page alignment on, every back/forward step returns to the exact first character of the page — even if you toggled fullscreen or changed the layout in between.

### Interface

- **Settings panel**: groups keep their designed order and are split into columns so the tallest column is as short as possible, using the fewest columns that fit; if they still don't fit, the panel scrolls vertically only. The panel header stays fixed while scrolling, and the layout recalculates automatically when content changes (adding tags, uploading fonts, collapsing groups) or the window is resized.
- **Buttons**: all icon buttons share one size and style; the toolbar and panel headers line up at the same height.

- **Language**: defaults to Traditional Chinese or English based on your browser's preferred language for web content. Can be manually set to either language; a page reload is required for the change to take effect.

## Quick start

**Image**: `ghcr.io/bgtsai/calibre-web-foliate-docker:latest` — [package page (versions, pull command)](https://github.com/bgtsai/calibre-web-foliate-docker/pkgs/container/calibre-web-foliate-docker)

```yaml
services:
  calibre-web-foliate:
    image: ghcr.io/bgtsai/calibre-web-foliate-docker:latest
    container_name: calibre-web-foliate
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Taipei
    volumes:
      - /path/to/config:/config
      - /path/to/books:/books
    ports:
      - 8083:8083
    restart: unless-stopped
```

It is based on [linuxserver/docker-calibre-web](https://github.com/linuxserver/docker-calibre-web) and used the same way: if you already run that image, just replace the `image:` line — config and library paths stay the same. Then open any EPUB in Calibre-Web and click the gear icon in the top-right corner to open the settings panel.

## Differences from the userscript version

The reader is built from the userscript's source at a pinned version, so the features are the same. The differences:

- **Settings are stored per browser and per address.** Settings live in the browser's `localStorage` (uploaded fonts in IndexedDB) instead of Tampermonkey storage. Browsers keep these separately for each address, so opening the same Calibre-Web through two different addresses (e.g. a LAN IP and a domain name) gives you two independent sets of settings. Clearing the browser's site data clears them too.
- **Works on older iPhone / iPad.** The reader is converted at build time so that iOS 15's Safari can run it, with missing built-in functions filled in. Some newer functions used only for PDF are not filled in, so opening PDFs on older iOS may fail.
- **Error panel.** When an error occurs on the reader page, a red "⚠ count" button appears in the bottom-left corner. Tap it to see the error list and copy it in one click — handy for reporting problems from devices without developer tools. If the reader page crashes outright, add `?cwfm=safe` to the reader address: the page then skips loading the reader and shows the error log from the previous attempt.

## Interface language not as expected?

The interface defaults to Traditional Chinese or English based on your browser's reported "preferred language for web content" — if it starts with `zh`, Chinese is shown; otherwise English. This setting is independent of your browser's own UI language (menus, buttons, etc.) — a browser with a Chinese interface doesn't necessarily report Chinese as the preferred web content language. If the auto-detected result isn't what you want, you can:

- Go to the "語言 / Language" section at the bottom of the settings panel and manually set the display language (a page reload is required for the change to take effect); or
- Adjust your browser's "preferred language for web content" setting (in Firefox: Settings → General → Language → Choose your preferred language for displaying pages, and move Traditional Chinese to the top of the list).

## How it works

The reader code is not duplicated here. When the image is built, it is assembled directly from a pinned commit of [calibre-web-foliate-mod](https://github.com/bgtsai/calibre-web-foliate-mod) (`CWFM_MOD_REF` in the `Dockerfile`):

| File | Description |
|---|---|
| `cps/static/js/cwfm/cwfm-reader.js` | foliate-js engine + reader interface, generated from the mod source by `build/make_reader.py` |
| `cps/templates/read.html` | Patched in place by `build/patch_read_html.py`: the old epub.js reader's scripts and styles are removed and the script above is added; the rest of the page is kept |

The patch only changes the files in the table: the rest of Calibre-Web (server, other pages, library, bookmarks, users) is untouched. Before writing anything, the patch checks that every anchor it relies on in `read.html` is present exactly once; if an upstream release changes that page, the build stops with an error and the previous image stays in place instead of producing a broken page. The iOS 15 conversion lives in `build/legacy/`, the error panel in `build/error_panel.html`.

The old reader's files remain in the image (other pages may use them); the EPUB reader page simply no longer loads them.

Upgrading the reader: change `CWFM_MOD_REF` in the `Dockerfile` to the mod's new commit SHA and push. The value also serves as a browser cache-busting parameter, so the old file is never served after an upgrade.

## Build status RSS

The image is rebuilt automatically when the upstream `linuxserver/calibre-web` image changes (checked daily at 12:00 Taipei time). Each run posts an item to:

https://raw.githubusercontent.com/bgtsai/calibre-web-foliate-docker/main/build_status.xml

🟢 no upstream update · 🔵 rebuilt and pushed · 🔴 failed (the previous image stays in place).

## License

This project is based on [linuxserver/docker-calibre-web](https://github.com/linuxserver/docker-calibre-web) (GPL v3) and [janeczku/calibre-web](https://github.com/janeczku/calibre-web) (GPL v3), and is released under GPL v3.

foliate-js is released under the MIT license and is included in this project.
