#!/usr/bin/env bash
# Start the access-desk service (127.0.0.1:HC_GOV_SERVICE_PORT, default 8518) in the background unless it already answers.
# Log: .work/itsm_api.log.  Stop it: pkill -f "$PWD/service/itsm_api.py"
source "$(dirname "$0")/../setup/common.sh"
curl -sf -m 2 "$SVC/health" >/dev/null && { echo "access-desk service already running on $SVC"; exit 0; }
mkdir -p "$ROOT/.work"
nohup "$PY" "$ROOT/service/itsm_api.py" >>"$ROOT/.work/itsm_api.log" 2>&1 &
for _ in $(seq 1 30); do curl -sf -m 1 "$SVC/health" >/dev/null && { echo "access-desk service started on $SVC"; exit 0; }; sleep 0.5; done
echo "access-desk service did not start: see $ROOT/.work/itsm_api.log" >&2; exit 1
