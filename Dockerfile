# syntax=docker/dockerfile:1
# calibre-web-foliate-docker
# 基於 lscr.io/linuxserver/calibre-web，把 epub 閱讀器換成 calibre-web-foliate-mod 的 foliate-js 版本

# 要打包的 calibre-web-foliate-mod 版本（完整 commit SHA）。
# 改這一行就是「升級閱讀器」；它同時是瀏覽器端的快取破壞參數，
# 換版本後瀏覽器一定會重新下載，不會拿到舊檔。
ARG CWFM_MOD_REF=f39b796eef03bdcdccb5a93af1942daa37a28fb6
# 【診斷用】1 = 在閱讀器程式裡插入檢查點，找 iOS 15 載入時當機的位置；找到並修好後改回 0 移除。
ARG CWFM_CHECKPOINTS=1

# ---- 第一階段：從 mod 原始碼組出 cwfm-reader.js ----
# mod 的 src/app-ui.js 與 foliate-src/bundle.js 是唯一來源，這裡不另存副本，
# 每次建置都從指定 commit 抓下來組裝（組法見 build/make_reader.py）。
# 接著轉譯成舊版 Safari（iOS 15）也看得懂的版本（見 build/legacy/make_legacy.py）；
# 新瀏覽器拿到同一份檔案也能正常執行，所以只產出一份。
FROM alpine:3.20 AS reader
ARG CWFM_MOD_REF
ARG CWFM_CHECKPOINTS
RUN apk add --no-cache git python3 nodejs npm
COPY build/legacy/package.json /work/legacy/package.json
RUN cd /work/legacy && npm install --no-audit --no-fund --loglevel=error
COPY build/make_reader.py /work/make_reader.py
COPY build/legacy/ /work/legacy/
RUN set -eu; \
    git init -q /work/mod; \
    cd /work/mod; \
    git remote add origin https://github.com/bgtsai/calibre-web-foliate-mod.git; \
    git fetch -q --depth 1 origin "${CWFM_MOD_REF}"; \
    git checkout -q FETCH_HEAD; \
    short=$(echo "${CWFM_MOD_REF}" | cut -c1-7); \
    ver=$(sed -n 's#^// @version *##p' calibre-web-foliate-mod.user.js); \
    python3 /work/make_reader.py /work/mod /out/cwfm-reader.modern.js "${ver} (docker, mod ${short})"; \
    CWFM_CHECKPOINTS="${CWFM_CHECKPOINTS}" python3 /work/legacy/make_legacy.py /out/cwfm-reader.modern.js /out/cwfm-reader.js /work/legacy/node_modules

# ---- 第二階段：疊在 linuxserver 的 Calibre-Web image 上 ----
FROM lscr.io/linuxserver/calibre-web:latest
ARG CWFM_MOD_REF
ARG CWFM_CHECKPOINTS

LABEL maintainer="bgtsai"
LABEL org.opencontainers.image.source="https://github.com/bgtsai/calibre-web-foliate-docker"
LABEL org.opencontainers.image.description="Calibre-Web with foliate-js reader — no Tampermonkey required"
LABEL org.opencontainers.image.licenses="GPL-3.0"

COPY --from=reader /out/cwfm-reader.js /app/calibre-web/cps/static/js/cwfm/cwfm-reader.js
COPY build/patch_read_html.py build/error_panel.html /tmp/cwfm-build/
# linuxserver 的 image 若沒有把 python3 放進 PATH，改用它內建的 venv
RUN set -eu; \
    PY=$(command -v python3 || echo /lsiopy/bin/python3); \
    "$PY" /tmp/cwfm-build/patch_read_html.py /app/calibre-web/cps/templates/read.html "$(echo "${CWFM_MOD_REF}" | cut -c1-7)-legacy2-chk${CWFM_CHECKPOINTS}"; \
    rm -rf /tmp/cwfm-build
