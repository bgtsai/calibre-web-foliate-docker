# calibre-web-foliate-docker

[English](#english) | **繁體中文**

以 [foliate-js](https://github.com/johnfactotum/foliate-js) 取代 [Calibre-Web](https://github.com/janeczku/calibre-web) 內建 epub.js 閱讀器的 Docker image。不需要安裝 Tampermonkey。

## 功能

- 以 foliate-js 渲染 EPUB，支援多欄版面、精準翻頁定位
- 完整設定面板：字體、字級、行距、字距、色彩主題、翻頁動畫等
- 自訂字體上傳（存入 IndexedDB）
- 閱讀進度自動儲存（localStorage，同源持久）
- 雙語介面（繁體中文 / English，自動偵測或手動切換）
- 完整 Calibre-Web 功能不受影響（書庫、書籤、使用者管理等）

## 快速開始

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

## 與上游的差異

閱讀器程式碼不另存副本，建置 image 時直接從 [calibre-web-foliate-mod](https://github.com/bgtsai/calibre-web-foliate-mod) 的指定 commit（`Dockerfile` 的 `CWFM_MOD_REF`）組裝：

| 檔案 | 說明 |
|---|---|
| `cps/static/js/cwfm/cwfm-reader.js` | foliate-js 引擎 + 閱讀器介面，由 `build/make_reader.py` 從 mod 原始碼產生 |
| `cps/templates/read.html` | 由 `build/patch_read_html.py` 就地修改：移除舊 epub.js 閱讀器的腳本與樣式，加入上面這支程式；頁面其餘結構保留 |

相容性：`cwfm-reader.js` 建置時會用 esbuild 轉譯成舊版 Safari（iOS 15）也能執行的語法，並補上缺少的內建函式（`build/legacy/`）。PDF 專用的部分新函式沒有補，舊版 iOS 開 PDF 可能出錯。

錯誤面板：閱讀頁發生錯誤時，左下角會出現紅色「⚠ 數量」按鈕，點開可看到錯誤清單並一鍵複製，方便在沒有開發者工具的裝置（例如 iPad）上回報問題（`build/error_panel.html`）。

舊閱讀器的檔案本身仍留在 image 裡（其他頁面可能用到），只是 epub 閱讀頁不再載入。

升級閱讀器：把 `Dockerfile` 的 `CWFM_MOD_REF` 改成 mod 新的 commit SHA 並推送即可。這個值同時當作瀏覽器快取破壞參數，換版後不會讀到舊檔。

## 設定儲存

Tampermonkey 版使用 `GM_setValue` 跨網域儲存；Docker 版改用 `localStorage`（同源，Calibre-Web 所在的 domain）。清除瀏覽器資料時設定會一併清除，這是已知的取捨。

## 授權

本專案基於 [linuxserver/docker-calibre-web](https://github.com/linuxserver/docker-calibre-web)（GPL v3）與 [janeczku/calibre-web](https://github.com/janeczku/calibre-web)（GPL v3），以 GPL v3 授權釋出。

foliate-js 以 MIT 授權釋出，已包含在本專案中。

---

## English

A Docker image that replaces [Calibre-Web](https://github.com/janeczku/calibre-web)'s built-in epub.js reader with [foliate-js](https://github.com/johnfactotum/foliate-js). No Tampermonkey required.

See the [Tampermonkey userscript version](https://github.com/bgtsai/calibre-web-foliate-mod) for feature details.

### License

GPL v3. Based on linuxserver/docker-calibre-web (GPL v3) and janeczku/calibre-web (GPL v3). foliate-js is MIT licensed.
