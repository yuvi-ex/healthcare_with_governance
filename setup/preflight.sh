#!/usr/bin/env bash
# Demo-day check for the access desk: GO / NO-GO.   setup/preflight.sh [--reset]
# --reset clears every ticket and starts the audit trail fresh (do it right before the demo, not during).
# Touches nothing of the hospital-chain demo. The VM clock matters here too (expiry and the audit trail compare times):
# the hospital-chain preflight keeps it in sync, so run that one first.
source "$(dirname "$0")/common.sh"
export SVC ROOT
FAIL=0
bad() { printf '    \033[0;31mNO\033[0m  %s\n' "$*"; FAIL=1; }

say "1. Access-desk service ($SVC)"
"$ROOT/service/run.sh" >/dev/null && ok "running" || bad "not starting: see .work/itsm_api.log"

say "2. Each login signs in, and its role is what Exasol says"
"$PY" - <<'PYEOF' || FAIL=1
import json, os, sys, urllib.request
def call(fn, *a):
    r = json.loads(urllib.request.urlopen(urllib.request.Request(os.environ["SVC"] + "/rpc", data=json.dumps({"fn": fn, "args": a}).encode()), timeout=60).read())
    return r.get("result") or {}
want = {"DR_PRIYA": "HC_CLINICIAN", "OWNER_ANITA": "HC_DATA_OWNER", "ANALYST_RAVI": "HC_ANALYST", "AUDITOR_SAM": "HC_AUDITOR"}
bad = 0
for u, role in want.items():
    r = call("demo_login", u)
    good = r.get("ok") and role in r.get("roles", [])
    print(f"    {'ok' if good else 'NO'}  {u}: {', '.join(r.get('roles', [])) or r.get('refused')}")
    bad += not good
    if r.get("token"):
        call("logout", r["token"])
sys.exit(1 if bad else 0)
PYEOF
[[ "${1:-}" == "--reset" ]] && { say "3. Reset"; "$PY" "$ROOT/setup/reset.py" | sed 's/^/    /'; }

say "3b. Claude (for typed questions; the six fixed questions work without it)"
"$PY" - <<'PYEOF' && ok "Claude answers" || printf '    \033[0;33mwarn\033[0m  Claude not reachable: typed questions will say so; use the six questions\n'
import json, os, sys, urllib.request
sys.path.insert(0, os.environ["ROOT"]); import hcconfig as C
k = dict(l.strip().split("=", 1) for l in open(C.ANTHROPIC_KEY_FILE) if "=" in l)["ANTHROPIC_API_KEY"]
req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps({"model": C.CLAUDE_MODEL, "max_tokens": 20,
      "thinking": {"type": "between_tools"}, "messages": [{"role": "user", "content": "Reply ok"}]}).encode(),
      headers={"x-api-key": k, "anthropic-version": "2023-06-01", "content-type": "application/json"})
sys.exit(0 if urllib.request.urlopen(req, timeout=30).status == 200 else 1)
PYEOF

say "4. Console"
curl -s -o /dev/null -w '%{http_code}' "$APP_URL/" | grep -q 200 \
  && ok "$APP_URL" || bad "dash-server page not answering: .venv/bin/python dash/deploy.py"
echo
(( FAIL == 0 )) && printf '\033[1;32mGO\033[0m\n' || { printf '\033[1;31mNO-GO\033[0m (fix the NO lines above)\n'; exit 1; }
