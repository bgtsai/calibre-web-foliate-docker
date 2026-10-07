# calibre-web-foliate-docker

**English** | [繁體中文](README.zh.md)

A Docker image that replaces [Calibre-Web](https://github.com/janeczku/calibre-web)'s built-in epub.js reader with [foliate-js](https://github.com/johnfactotum/foliate-js). No Tampermonkey required.

## Features

- EPUB rendering with foliate-js, with multi-column layout and precise page-turn positioning
- Full settings panel: font, font size, line spacing, letter spacing, color themes, page-turn animation, and more
- Custom font upload (stored in IndexedDB)
- Reading progress saved automatically (localStorage, persistent per origin)
- Bilingual interface (Traditional Chinese / English, auto-detected or set manually)
- All other Calibre-Web features unaffected (library, bookmarks, user management, etc.)

## Quick start

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

## Differences from upstream

The reader code is not duplicated here. When the image is built, it is assembled directly from a pinned commit of [calibre-web-foliate-mod](https://github.com/bgtsai/calibre-web-foliate-mod) (`CWFM_MOD_REF` in the `Dockerfile`):

| File | Description |
|---|---|
| `cps/static/js/cwfm/cwfm-reader.js` | foliate-js engine + reader interface, generated from the mod source by `build/make_reader.py` |
| `cps/templates/read.html` | Patched in place by `build/patch_read_html.py`: the old epub.js reader's scripts and styles are removed and the script above is added; the rest of the page is kept |

Compatibility: at build time, `cwfm-reader.js` is transpiled with esbuild into syntax that older Safari (iOS 15) can run, and missing built-in functions are polyfilled (`build/legacy/`). Some newer functions used only for PDF are not polyfilled, so opening PDFs on older iOS may fail.

Error panel: when an error occurs on the reader page, a red "⚠ count" button appears in the bottom-left corner. Tap it to see the error list and copy it in one click — handy for reporting problems from devices without developer tools, such as an iPad (`build/error_panel.html`).

The old reader's files remain in the image (other pages may use them); the EPUB reader page simply no longer loads them.

Upgrading the reader: change `CWFM_MOD_REF` in the `Dockerfile` to the mod's new commit SHA and push. The value also serves as a browser cache-busting parameter, so the old file is never served after an upgrade.

## Build status RSS

The image is rebuilt automatically when the upstream `linuxserver/calibre-web` image changes (checked daily at 12:00 Taipei time). Each run posts an item to:

https://raw.githubusercontent.com/bgtsai/calibre-web-foliate-docker/main/build_status.xml

🟢 no upstream update · 🔵 rebuilt and pushed · 🔴 failed (the previous image stays in place).

## Settings storage

The Tampermonkey version stores settings across domains with `GM_setValue`; the Docker version uses `localStorage` instead (same-origin, i.e. the domain Calibre-Web is served from). Clearing browser data clears the settings too — a known trade-off.

## License

This project is based on [linuxserver/docker-calibre-web](https://github.com/linuxserver/docker-calibre-web) (GPL v3) and [janeczku/calibre-web](https://github.com/janeczku/calibre-web) (GPL v3), and is released under GPL v3.

foliate-js is released under the MIT license and is included in this project.
