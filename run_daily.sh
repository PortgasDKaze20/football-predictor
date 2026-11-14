#!/bin/bash
# Copy today's refresh file from Downloads into the project, then predict.
cd "$(dirname "$0")"
DL="${1:-$HOME/mnt/Downloads}"
# wait up to 30s for a refresh file downloaded in the last 15 minutes
for i in $(seq 1 30); do
  f=$(find "$DL" -maxdepth 1 -name 'fp_refresh_*.csv' -mmin -15 2>/dev/null | xargs -r ls -t 2>/dev/null | head -1)
  [ -n "$f" ] && break; sleep 1
done
if [ -n "$f" ]; then
  base=$(basename "$f" | sed -E 's/ ?\([0-9]+\)//')
  cp "$f" "data/raw/$base"; echo "using $base"
else
  echo "WARNING: no fresh refresh file found in Downloads; using existing data"
fi
python3 -W ignore predict.py && python3 -W ignore build_page.py
