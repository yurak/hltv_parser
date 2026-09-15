#!/bin/bash
# Синхронізує дані статті 5 з бакетом S3.
#   ./sync_s3.sh up raw        — залити .dem  (сирі демки, ~18 ГБ)
#   ./sync_s3.sh up processed  — залити .parquet
#   ./sync_s3.sh down raw      — забрати назад
#   ./sync_s3.sh status        — що вже в бакеті
#
# aws s3 sync докачує перерване й пропускає вже залите, тож повторний
# запуск після обриву безпечний.
set -euo pipefail
PROJ="$(cd "$(dirname "$0")/../.." && pwd)"
source "$PROJ/aws-env.sh" >/dev/null
DATA="$PROJ/article5_movement/data"
BUCKET="s3://democs2phd"

case "${1:-status}" in
  up)
    case "${2:-raw}" in
      raw)       aws s3 sync "$DATA/raw/"       "$BUCKET/raw/"       --exclude "*" --include "*.dem"     --storage-class STANDARD ;;
      processed) aws s3 sync "$DATA/processed/" "$BUCKET/processed/" --exclude "*" --include "*.parquet" --storage-class STANDARD ;;
      *) echo "невідомо: $2"; exit 1 ;;
    esac ;;
  down)
    case "${2:-raw}" in
      raw)       aws s3 sync "$BUCKET/raw/"       "$DATA/raw/"       --exclude "*" --include "*.dem" ;;
      processed) aws s3 sync "$BUCKET/processed/" "$DATA/processed/" --exclude "*" --include "*.parquet" ;;
    esac ;;
  status)
    echo "=== у бакеті ==="
    aws s3 ls "$BUCKET/raw/"       --summarize --human-readable | tail -3
    aws s3 ls "$BUCKET/processed/" --summarize --human-readable | tail -3
    echo "=== локально ==="
    printf "raw:       %s файлів, %s\n" "$(ls -1 "$DATA"/raw/*.dem 2>/dev/null | wc -l | tr -d ' ')" "$(du -sh "$DATA/raw" | cut -f1)"
    printf "processed: %s файлів, %s\n" "$(ls -1 "$DATA"/processed/*.parquet 2>/dev/null | wc -l | tr -d ' ')" "$(du -sh "$DATA/processed" | cut -f1)" ;;
  *) echo "вживання: $0 {up|down} {raw|processed} | $0 status"; exit 1 ;;
esac
