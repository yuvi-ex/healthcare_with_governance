#!/usr/bin/env bash
# Remove everything this project created: the console app, the access-desk service, the HEALTH_ITSM and HEALTH_GOV
# schemas, the four roles and the four logins. The hospital_chain build underneath is not touched.
#   setup/uninstall.sh --yes
source "$(dirname "$0")/common.sh"
set -euo pipefail
export ROOT
[[ "${1:-}" == "--yes" ]] || die "this deletes the access layer, its logins, tickets and the console app; run with --yes"

say "1. Console app on dash-server"
"$PY" - <<'PYEOF'
import json, os, sys, urllib.request
sys.path.insert(0, os.environ["ROOT"]); import hcconfig as C
body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "app_delete", "arguments": {"name": C.APP, "confirmation": C.APP}}}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{C.DASH_PORT}/mcp", data=body,
                             headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
try:
    raw = urllib.request.urlopen(req, timeout=120).read().decode()
    print(f"    ok  {C.APP} " + ("deleted" if '"deleted":true' in raw.replace(" ", "") or "deleted" in raw else "was not there"))
except Exception as e:  # noqa: BLE001
    print(f"    skip  dash-server not reachable ({type(e).__name__})")
PYEOF

say "2. Access-desk service"
pkill -f "$ROOT/service/itsm_api.py" && ok "stopped" || ok "was not running"

say "3. Database objects"
"$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["ROOT"]); import hcconfig as C
con = C.exasol()
for u in ("DR_PRIYA", "OWNER_ANITA", "ANALYST_RAVI", "AUDITOR_SAM"):
    con.execute(f"DROP USER IF EXISTS {u} CASCADE")
for r in ("HC_CLINICIAN", "HC_ANALYST", "HC_DATA_OWNER", "HC_AUDITOR"):
    if con.execute(f"SELECT COUNT(*) FROM EXA_DBA_ROLES WHERE ROLE_NAME = '{r}'").fetchval():
        con.execute(f"DROP ROLE {r} CASCADE")
for s in ("HEALTH_GOV", "HEALTH_ITSM"):
    con.execute(f"DROP SCHEMA IF EXISTS {s} CASCADE")
print("    ok  HEALTH_GOV, HEALTH_ITSM, 4 roles, 4 logins removed")
PYEOF
rm -f "$ROOT/secrets/hc_users.env"
ok "secrets/hc_users.env removed (secrets/anthropic.env kept)"
