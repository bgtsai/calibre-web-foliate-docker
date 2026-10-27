#!/bin/bash
# calibre-web-foliate 一鍵更新（Synology 工作排程器用，使用者選 root）
# 容器在（執行中或停止）→ Watchtower 只更新這一個；不在 → 用 compose.yaml 建立專案。
# 用法：排程指令欄只放一行  bash /volume1/docker/compose/compose_calibre-web-foliate/update.sh
# 下面四個值改成你自己的。

CONTAINER="11_calibre-web-foliate"
PROJECT="calibre-web-foliate"          # 要跟 Container Manager 裡的專案名稱相同，否則會變成另一個專案
DIR="/volume1/docker/compose/compose_calibre-web-foliate"
LOG="$DIR/update.log"

exec > "$LOG" 2>&1                    # 排程沒有畫面，全部輸出寫進 log
echo "== $(TZ=Asia/Taipei date '+%F %T')"

DOCKER=""
for p in /usr/local/bin/docker /usr/bin/docker; do [ -x "$p" ] && DOCKER="$p" && break; done
[ -z "$DOCKER" ] && { echo "找不到 docker 指令，結束"; exit 1; }
echo "docker: $DOCKER"

if [ -n "$("$DOCKER" ps -a -q -f "name=^${CONTAINER}$")" ]; then
    echo "容器 $CONTAINER 存在 → Watchtower 更新"
    "$DOCKER" run --rm -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower \
        --run-once --cleanup --include-stopped "$CONTAINER"
    rc=$?; echo "Watchtower 結束碼 $rc"; exit $rc
fi

echo "容器 $CONTAINER 不存在 → 用 compose 建立"
YML=""
for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
    [ -f "$DIR/$f" ] && YML="$DIR/$f" && break
done
[ -z "$YML" ] && { echo "$DIR 裡找不到 compose 檔，不做任何事"; exit 1; }
echo "compose 檔: $YML"

# Container Manager 版本不同，compose 可能是 docker compose 或獨立的 docker-compose
if "$DOCKER" compose version >/dev/null 2>&1; then
    COMPOSE=("$DOCKER" compose)
elif [ -x /usr/local/bin/docker-compose ]; then
    COMPOSE=(/usr/local/bin/docker-compose)
else
    echo "找不到 compose 指令，結束"; exit 1
fi
echo "compose: ${COMPOSE[*]}"

"${COMPOSE[@]}" -p "$PROJECT" -f "$YML" pull && "${COMPOSE[@]}" -p "$PROJECT" -f "$YML" up -d
rc=$?; echo "compose 結束碼 $rc"; exit $rc
