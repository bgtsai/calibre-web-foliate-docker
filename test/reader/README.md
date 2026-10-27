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
  python3 ft_empty.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b   # 搜尋空狀態
  CWFM_MOD_DIR=../../../calibre-web-foliate-mod python3 ft_earlyhide.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b   # v1.81.2：第一個畫面就看不到原生介面（Docker／TM）
  python3 feat_test.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js $b  # 舊版功能（「縮放後重算…標題固定」是 v1.79 起就失敗的舊測試）
done
python3 ft_zh2.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js chromium   # 中文介面
python3 ft_ipad.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js webkit    # iPad 尺寸
python3 ah.py /tmp/cwfm-test/dp.html /tmp/cwfm-test/dr.js chromium       # 自動隱藏
```

- 觸控（手機／平板）只有 Chromium 能模擬（`is_mobile`＋`has_touch`），WebKit／Firefox 會略過那幾項。
- 測試環境已知會出現一則「初始鎖定定位點失敗」（從頭開書時，舊版也有），⚠ 1 屬正常。
- `shot_readme2.py`：重拍 README 截圖（中文書／英文書各一，`SHOT_TM=1` 拍 Tampermonkey 版——沒有伺服器 API、不會出現錯誤紀錄區）。
- `read-0.6.27.html` 是 Calibre-Web 原版 `cps/templates/read.html`（對應版本），測試前由 `patch_read_html.py` 修改。
