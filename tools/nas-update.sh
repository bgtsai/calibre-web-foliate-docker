#!/bin/bash
# Synology Docker 容器一鍵更新（工作排程器用，使用者選 root）
# 放在 compose 專案資料夾 compose_<名稱>/ 裡，自動找「數字_<名稱>」的容器，交給 Watchtower 只更新這一個。
# 不會建立容器或專案：找不到就提示到 Container Manager 建立（指令列建的專案 Container Manager 不認得）。
# 用法：排程指令欄放 README 裡那一行——每次先抓 GitHub 最新版、檢查過才替換再執行，抓不到就跑現有這份。
# 不照命名規則的容器：在指令前指定 CONTAINER=實際名稱。設定不要改在這個檔案裡（下次會被最新版覆蓋）。

DIR="${DIR:-$(cd "$(dirname "$0")" && pwd)}"
LOG="${LOG:-$DIR/nas-update.log}"
NAME="$(basename "$DIR")"; NAME="${NAME#compose_}"

exec > "$LOG" 2>&1                    # 排程沒有畫面，全部輸出寫進 log
echo "== $(TZ=Asia/Taipei date '+%F %T')"

notify() {                            # 結束前提示：log＋DSM 通知（有這個指令才送）＋失敗結束碼
    echo "$1"; [ -n "$2" ] && echo "$2"; echo "沒有做任何變更"
    N=/usr/syno/bin/synodsmnotify
    [ -x "$N" ] && "$N" @administrators "Docker 更新：$NAME" "$1 $2"
    exit 1
}

DOCKER=""
for p in /usr/local/bin/docker /usr/bin/docker; do [ -x "$p" ] && DOCKER="$p" && break; done
[ -z "$DOCKER" ] && notify "找不到 docker 指令"
echo "docker: $DOCKER"

if [ -z "$CONTAINER" ]; then
    # 比對「數字_<名稱>」：名稱用字串完全相等比，不用正規表示式（名稱裡的 . 之類才不會變成萬用字元）
    mapfile -t HITS < <("$DOCKER" ps -a --format '{{.Names}}' | awk -v n="$NAME" '{ s = $0; if (sub(/^[0-9]+_/, "", s) && s == n) print }')
    if [ "${#HITS[@]}" -eq 0 ]; then
        notify "找不到符合「數字_${NAME}」的容器" \
            "→ 請到 Container Manager「專案 → 新增」，路徑選 ${DIR#/volume1}，用裡面的 compose.yaml 建立專案"
    elif [ "${#HITS[@]}" -gt 1 ]; then
        notify "找到多個：${HITS[*]}" "→ 請刪掉不用的那個，或在指令前用 CONTAINER= 指定"
    fi
    CONTAINER="${HITS[0]}"
elif [ -z "$("$DOCKER" ps -a -q -f "name=^${CONTAINER}$")" ]; then
    notify "找不到容器 $CONTAINER" "→ 請到 Container Manager 用 ${DIR#/volume1} 的 compose.yaml 建立專案"
fi

echo "容器 $CONTAINER → Watchtower 更新"
"$DOCKER" run --rm -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower \
    --run-once --cleanup --include-stopped "$CONTAINER"
rc=$?; echo "Watchtower 結束碼 $rc"; exit $rc
