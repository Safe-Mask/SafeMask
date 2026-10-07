#!/usr/bin/env bash
# Aquece a instancia Gratuita do Render antes da demo (cold start > 60s).
#
# Uso:
#   scripts/warmup.sh                       # 12 pings de 10s (~2 min)
#   scripts/warmup.sh --url https://safemask-backend.onrender.com --pings 30 --interval 10
#
# Rode ~10 minutos antes de apresentar; se quiser, agende o ping com cron.

set -euo pipefail

URL="https://safemask-backend.onrender.com"
PINGS=12
INTERVAL=10

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url) URL="$2"; shift 2 ;;
        --pings) PINGS="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done

echo "Aquecedor: $URL (pings=$PINGS, intervalo=${INTERVAL}s)"
for ((i = 1; i <= PINGS; i++)); do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 90 "$URL/")
    echo "  ping $i/$PINGS -> HTTP $code ($(date +%H:%M:%S))"
    [[ $i -lt $PINGS ]] && sleep "$INTERVAL"
done
echo "Warm-up concluido."