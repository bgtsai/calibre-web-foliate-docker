#!/bin/sh
# 從 mod 原始碼組出測試用的閱讀器與 read.html（不推送、不動 Dockerfile）
# 用法：CWFM_MOD_DIR=<mod 的 clone> OUT=<輸出資料夾> sh test/reader/build.sh   （在 docker repo 根目錄執行）
# 需要：pip install playwright jinja2；cd build/legacy && npm install（產生 node_modules）
set -e
MOD=${CWFM_MOD_DIR:-../calibre-web-foliate-mod}
OUT=${OUT:-/tmp/cwfm-test}
mkdir -p "$OUT"
(cd "$MOD" && python3 tools/pack.py --check >/dev/null)
python3 build/make_reader.py "$MOD" "$OUT/dm.js" test >/dev/null
CWFM_CHECKPOINTS=0 python3 build/legacy/make_legacy.py "$OUT/dm.js" "$OUT/dr.js" build/legacy/node_modules | tail -1
cp test/reader/read-0.6.27.html "$OUT/dp.html" && python3 build/patch_read_html.py "$OUT/dp.html" test >/dev/null
# v1.88.0：首次教學的遮罩會蓋住其他測試的點擊——測試頁預設擋掉自動開始（測試裡先設 sessionStorage 的 cwfm-tut-test 就不擋）；
# v1.88 的新預設（工具列自動隱藏、分組收合）讓舊測試點不到東西——預設沿用舊預設（測試裡先設 cwfm-v188-test 就用新預設）
if [ "${CWFM_TUT:-0}" != "1" ]; then
  python3 -c "import sys;p=sys.argv[1];s=open(p,encoding='utf-8').read();s=s.replace('<head>','<head><script>try{if(!sessionStorage.getItem(\'cwfm-v188-test\'))sessionStorage.setItem(\'cwfm-test-legacy-defaults\',\'1\');if(!sessionStorage.getItem(\'cwfm-tut-test\'))sessionStorage.setItem(\'cwfm-no-tutorial\',\'1\')}catch(e){}</script>',1);open(p,'w',encoding='utf-8').write(s)" "$OUT/dp.html"
fi
echo "OK → $OUT/dp.html $OUT/dr.js"
