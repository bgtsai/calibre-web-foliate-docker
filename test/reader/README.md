# 閱讀器功能測試（無頭瀏覽器）

給維護者（含 Claude）用的回歸測試。`test/run_test.py` 是開書冒煙測試；這裡是功能測試，每次改閱讀器都要三種瀏覽器跑過。

```
CWFM_MOD_DIR=../calibre-web-foliate-mod OUT=/tmp/cwfm-test sh test/reader/build.sh
cd test/reader
for b in chromium webkit firefox; do
  python3 ft179.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.79：進度、預覽、書籤、搜尋、匯出、CSRF（41 項）
  python3 ft180.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.80：首次預設、跳轉合併、卡片、全螢幕、觸控翻頁、錯誤紀錄卡…
  CWFM_MOD_DIR=../../../calibre-web-foliate-mod python3 ft_load.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b   # 載入提示、預先下載、TM 遇 Docker 自停
  python3 ft182.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.82：分組調整、設定檔存全部設定＋面板同步、錯誤面板〔忽略〕
  python3 ft_icons.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b    # v1.82.1：標籤小圖示、步進器 − ＋ 是 SVG 且垂直置中（±0.5px，截圖寫到 OUT_DIR，預設 /tmp）
  python3 ft_keys.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b     # v1.82.2：快速鍵在各種介面狀態下該不該翻頁（第一章 iframe、進度條、目錄、設定、搜尋、對話框）
  python3 ft183.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.83.0：跳轉紀錄 99+／提示、上一步與書籤的存檔動畫、減少動態效果改淡入（截圖寫到 OUT_DIR）
  python3 ft_empty.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b   # 搜尋空狀態
  CWFM_MOD_DIR=../../../calibre-web-foliate-mod python3 ft_earlyhide.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b   # v1.81.2：第一個畫面就看不到原生介面（Docker／TM）
  python3 ft184.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.84：圖片書並排、翻頁方向、插頁、上一步動畫（圖片書見下）
  python3 ft185.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.85：新書開啟時套用、書名頁、文字書插頁、虛擬頁
  python3 ft186.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.86：翻頁方向一般設定、紙色、扉頁、滑桿不卡
  python3 ft187.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b      # v1.87：設定檔自動存回、內建唯讀→（已調整）、書指向設定檔、還原、圖示 14px
  python3 feat_test.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b  # 舊版功能
done
python3 ft_zh2.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js chromium   # 中文介面
python3 ft_ipad.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js webkit    # iPad 尺寸
python3 ah.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js chromium       # 自動隱藏
```

- 觸控（手機／平板）只有 Chromium 能模擬（`is_mobile`＋`has_touch`），WebKit／Firefox 會略過那幾項。
- 測試環境已知會出現一則「初始鎖定定位點失敗」（從頭開書時，舊版也有），⚠ 1 屬正常。
- `shot_readme2.py`：重拍 README 截圖（中文書／英文書各一，`SHOT_TM=1` 拍 Tampermonkey 版——沒有伺服器 API、不會出現錯誤紀錄區）。
- `read-0.6.27.html` 是 Calibre-Web 原版 `cps/templates/read.html`（對應版本），測試前由 `patch_read_html.py` 修改。
- 圖片書測試（ft184～187）預設用 `make_image_epub.py` 現場產生的純圖片 EPUB（cover＋30 頁、1650×2390、有書名／作者／出版社）；
  `CWFM_EPUB=<路徑>` 可改用真書。單獨產生檔案：`python3 make_image_epub.py out.epub [--no-publisher] [--dir rtl|ltr]`。
