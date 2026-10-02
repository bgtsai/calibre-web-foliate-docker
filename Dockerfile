# syntax=docker/dockerfile:1
# calibre-web-foliate-docker
# 基於 lscr.io/linuxserver/calibre-web，覆蓋 epub 閱讀器為 foliate-js 版本

FROM lscr.io/linuxserver/calibre-web:latest

LABEL maintainer="bgtsai"
LABEL org.opencontainers.image.source="https://github.com/bgtsai/calibre-web-foliate-docker"
LABEL org.opencontainers.image.description="Calibre-Web with foliate-js reader — no Tampermonkey required"
LABEL org.opencontainers.image.licenses="GPL-3.0"

# 覆蓋 Calibre-Web 靜態資源：以 foliate-js 閱讀器取代原版 epub.js
COPY calibre-web-overlay/cps/templates/read.html /app/calibre-web/cps/templates/read.html
COPY calibre-web-overlay/cps/static/js/cwfm/ /app/calibre-web/cps/static/js/cwfm/
