# syntax=docker/dockerfile:1
# calibre-web-foliate-docker
# 基於 linuxserver/docker-calibre-web，以 foliate-js 取代內建 epub.js 閱讀器

FROM ghcr.io/linuxserver/unrar:latest AS unrar
FROM ghcr.io/linuxserver/baseimage-ubuntu:noble

# 版本標籤
ARG BUILD_DATE
ARG VERSION
ARG CALIBREWEB_RELEASE
LABEL build_version="calibre-web-foliate version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="bgtsai"
LABEL org.opencontainers.image.source="https://github.com/bgtsai/calibre-web-foliate-docker"
LABEL org.opencontainers.image.description="Calibre-Web with foliate-js reader — no Tampermonkey required"
LABEL org.opencontainers.image.licenses="GPL-3.0"

ENV \
    QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox"

RUN \
    echo "**** install build packages ****" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        python3-dev && \
    echo "**** install runtime packages ****" && \
    apt-get install -y --no-install-recommends \
        imagemagick \
        ghostscript \
        libasound2t64 \
        libldap2 \
        libmagic1t64 \
        libsasl2-2 \
        libxi6 \
        libxslt1.1 \
        libxfixes3 \
        python3-venv \
        sqlite3 \
        xdg-utils && \
    echo "**** install calibre-web ****" && \
    if [ -z ${CALIBREWEB_RELEASE+x} ]; then \
        CALIBREWEB_RELEASE=$(curl -sX GET "https://api.github.com/repos/janeczku/calibre-web/releases/latest" \
        | jq -r '.tag_name'); \
    fi && \
    curl -o \
        /tmp/calibre-web.tar.gz -L \
        https://github.com/janeczku/calibre-web/archive/${CALIBREWEB_RELEASE}.tar.gz && \
    mkdir -p \
        /app/calibre-web && \
    tar xf \
        /tmp/calibre-web.tar.gz -C \
        /app/calibre-web --strip-components=1 && \
    cd /app/calibre-web && \
    python3 -m venv /lsiopy && \
    pip install -U --no-cache-dir \
        pip \
        wheel && \
    pip install -U --no-cache-dir --find-links https://wheel-index.linuxserver.io/ubuntu/ -r \
        requirements.txt -r \
        optional-requirements.txt && \
    echo "***install kepubify" && \
    if [ -z ${KEPUBIFY_RELEASE+x} ]; then \
        KEPUBIFY_RELEASE=$(curl -sX GET "https://api.github.com/repos/pgaskin/kepubify/releases/latest" \
        | jq -r '.tag_name'); \
    fi && \
    curl -o \
        /usr/bin/kepubify -L \
        https://github.com/pgaskin/kepubify/releases/download/${KEPUBIFY_RELEASE}/kepubify-linux-64bit && \
    echo "**** cleanup ****" && \
    apt-get -y purge \
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        python3-dev && \
    apt-get -y autoremove && \
    rm -rf \
        /tmp/* \
        /var/lib/apt/lists/* \
        /var/tmp/* \
        /root/.cache

# 覆蓋 Calibre-Web 靜態資源：注入 foliate-js 閱讀器
COPY calibre-web-overlay/cps/templates/read.html /app/calibre-web/cps/templates/read.html
COPY calibre-web-overlay/cps/static/js/cwfm/ /app/calibre-web/cps/static/js/cwfm/

# 加入 linuxserver 的系統設定（s6-overlay 初始化腳本等）
COPY root/ /

# add unrar
COPY --from=unrar /usr/bin/unrar-ubuntu /usr/bin/unrar

EXPOSE 8083
VOLUME /config
