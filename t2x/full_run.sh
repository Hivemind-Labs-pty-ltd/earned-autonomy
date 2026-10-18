#!/bin/bash
# Full T2-10x run (PREREG-10x): B, C, D x good/sloppy on all 6,000 tasks, one shared spend cap.
cd "$(dirname "$0")/.."
export TRUST_GYM_BASELINE_USD=137.95 TRUST_GYM_CAP_USD=60
mkdir -p report/raw/logs
for v in good sloppy; do
  python3 -m t2x.run --cond B --variant $v --workers 30 > report/raw/logs/full-B-$v.log 2>&1 &
  python3 -m t2x.run --cond C --variant $v --workers 30 > report/raw/logs/full-C-$v.log 2>&1 &
  for a in cs ws it ap of do; do
    python3 -m t2x.loop --arch $a --variant $v --workers 8 > report/raw/logs/full-D-$v-$a.log 2>&1 &
  done
done
wait
echo ALL DONE
