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
echo "OK → $OUT/dp.html $OUT/dr.js"
