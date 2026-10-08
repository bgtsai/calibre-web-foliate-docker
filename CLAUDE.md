# CLAUDE.md — calibre-web-foliate-docker 工作守則

給 Claude 看的：在這個 repo 工作前先讀完。互動原則另見 `bgtsai/claude-knowledge-base` 的 `01_與我互動的原則.html`。

## 這個 repo 是什麼
把 [calibre-web-foliate-mod](https://github.com/bgtsai/calibre-web-foliate-mod)（Tampermonkey 腳本）的 foliate-js 閱讀器，
直接打包進 `lscr.io/linuxserver/calibre-web` image，不需要 Tampermonkey。使用者在 Synology Container Manager 上跑，
也要支援 iPad（iOS 15.3，舊版 Safari）。

## 最重要的規則：閱讀器程式碼不在這裡
- **閱讀器功能（介面、設定、顏色、游標…）一律去 mod repo 改**，這個 repo 不放閱讀器原始碼副本，也不要在這裡打補丁改功能。
- 這個 repo 只負責：抓 mod 的指定版本 → 組裝 → 轉成舊 Safari 可執行 → 塞進 Calibre-Web 的 `read.html`。
- 使用者說「改閱讀器」時，就算他是叫你看這個 repo，也要去 mod repo 改。

## 改閱讀器的完整流程
（使用者訂定的測試順序：mod 所有修改改完、自檢通過後**只推送一次**，給 Tampermonkey 安裝連結；使用者換回上游原版 linuxserver image 用 Tampermonkey 測試——Docker 版與腳本同時存在會互相干擾；使用者確認 OK 後才做下面第 3 步更新 Docker。）
1. **mod repo**（`bgtsai/calibre-web-foliate-mod`），細節照它的 `CLAUDE.md`：
   - 只改 `src/app-ui.js`（介面）或 `foliate-src/bundle.js`（引擎）
   - 改 `calibre-web-foliate-mod.user.js` 第 4 行 `@version`
   - `python3 tools/pack.py`（或 `pack.py app`）→ `python3 tools/pack.py --check`
   - 原始碼與 user.js 一起 commit、push，記下完整 commit SHA
2. **本機測試**（見下面「測試」），三種瀏覽器都要過
3. **這個 repo**：`Dockerfile` 的 `ARG CWFM_MOD_REF=` 改成新的完整 SHA → commit、push
   - 這個值同時是瀏覽器快取破壞參數，不用另外處理快取
4. GitHub Actions（`.github/workflows/build.yml`）自動建置推到 GitHub Container Registry（ghcr.io/bgtsai/calibre-web-foliate-docker）；用 `gh run list` 確認成功
5. 回報使用者：mod 版本號、兩邊 commit、請他在 Synology 更新 image

## 建置流程（各檔案職責）
- `Dockerfile`：兩階段。第一階段 alpine 抓 mod → 組裝 → 轉譯；第二階段疊在 linuxserver 的 image 上。
- `build/make_reader.py`：把 mod 的 `foliate-src/bundle.js` + `src/app-ui.js` 組成一支 `cwfm-reader.js`，
  開書所需資訊改讀 `window.__cwfmBoot`（由 read.html 提供）。
- `build/legacy/make_legacy.py`：轉成 iOS 15 可執行：
  - 改寫唯一一處正規表示式往回比對、拿掉 pdf.js 的頂層 await（iOS 15.3 執行到會整頁當掉）
  - esbuild `target=safari15`（主要轉 class static 區塊）
  - `check_output.mjs` 用語法樹確認沒有殘留 static 區塊 / 往回比對 / 頂層 await
  - 前面接 `polyfills.js`（`.at()`、`Object.groupBy`、webkit 前綴全螢幕等）與 fflate 做的 `DecompressionStream` 代用品
  - 若引擎改版讓「剛好 1 處」的檢查失敗，建置會中止——要重新確認改寫方式，不要放寬檢查
- `build/patch_read_html.py`：直接修改 Calibre-Web 的 `read.html`：移除舊閱讀器、最前面插入錯誤面板、
  加開機腳本（localStorage 取代 GM_setValue）。網址加 `?cwfm=safe` 是安全模式（不載入閱讀器、只看上次錯誤紀錄）。
- `build/error_panel.html`：iPad 上沒有開發者工具，錯誤直接顯示在畫面上（ES5 寫法）。

## 測試
`test/run_test.py`：無頭瀏覽器模擬 Calibre-Web 開書頁（含相同 CSP、壓縮過的測試 EPUB）。
```
# 準備：pip install playwright jinja2；npm install（在 build/legacy）
python3 build/make_reader.py <mod 目錄> /tmp/m.js test
CWFM_CHECKPOINTS=0 python3 build/legacy/make_legacy.py /tmp/m.js /tmp/r.js build/legacy/node_modules
cp <Calibre-Web 原版 read.html> /tmp/p.html && python3 build/patch_read_html.py /tmp/p.html test
python3 test/run_test.py /tmp/p.html /tmp/r.js chromium   # 再跑 webkit、firefox
```
環境變數：`DELETE_APIS=1`（刪掉 iOS 15 沒有的內建函式，確認代用品有補上）、`FS_TEST=1`（全螢幕）、
`COLOR_TEST=1`（配色/跟隨系統）、`NAV_TEST=1`（換章節後游標隱藏與面板深淺）、`SAFE_AFTER=1`（安全模式）、`WAIT=毫秒`。
原版 `read.html` 取自 janeczku/calibre-web 對應版本的 `cps/templates/read.html`。
已知：測試環境會出現一則 `[cwfm:align] Failed to lock initial anchor`，舊版也有，與功能無關。

## 上游 Calibre-Web 自動更新
- `build.yml` 每天台北時間 12:00（cron `0 4 * * *` UTC）比對 `lscr.io/linuxserver/calibre-web:latest` 的 digest
  與 `.state/upstream_digest.txt`，不同才建置；建置成功才寫回記錄（`.state/` 不在觸發路徑內，不會連鎖觸發）。
- 推送或手動觸發一律建置；手動觸發勾 `check_only` 可比照排程只在有新版時建置（用來測試偵測邏輯）。
- 上游改版若讓 `patch_read_html.py` 對不上，建置會失敗、記錄不更新，隔天會再試——收到失敗通知時要去修 patch。

## 待辦
- `Dockerfile` 的 `ARG CWFM_CHECKPOINTS=1` 是診斷 iOS 15 當機用的檢查點，iPad 確認穩定後改成 0（使用者同意後另一輪做）。
