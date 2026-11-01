#!/usr/bin/env bash
# Build the access-on-request layer from a fresh clone, in order. Every step is re-runnable; a failed step stops the build.
#   setup/build_all.sh        all steps
#   setup/build_all.sh 3      from step 3 on
# Needs the hospital-chain demo built first (github.com/yuvi-ex/hospital_chain, at HC_BASE_DIR): this layer reads its
# HOSP_* views and its S3 settings, and changes nothing there.
source "$(dirname "$0")/common.sh"
set -euo pipefail
export ROOT
FROM="${1:-0}"
step() { local n="$1"; shift; (( n >= FROM )) || return 1; say "STEP $n · $*"; }

if step 0 "Python environment"; then "$ROOT/setup/venv.sh"; fi
if step 1 "The hospital-chain build is there"; then
  [[ -f "$BASE/config.env" ]] || die "no hospital-chain checkout at $BASE: clone github.com/yuvi-ex/hospital_chain there and build it, or set HC_BASE_DIR"
  "$PY" - <<'PYEOF' || die "the hospital-chain objects are missing in Exasol: run setup/build_all.sh in $BASE first"
import os, sys
sys.path.insert(0, os.environ["ROOT"]); import hcconfig as C
con = C.exasol()
need = {"HOSP_CORE": ["MPI", "PATIENT_RECORDS", "ENCOUNTERS", "ALLERGIES", "MEDICATIONS", "IMAGING_STUDIES"], "HOSP_LEGACY": ["DIS_SUMM"], "HOSP_EHR_ENCOUNTERS": ["ENCOUNTERS"]}
have = {(s, t) for s, t in con.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM EXA_ALL_TABLES UNION ALL SELECT VIEW_SCHEMA, VIEW_NAME FROM EXA_ALL_VIEWS").fetchall()}
missing = [f"{s}.{t}" for s, ts in need.items() for t in ts if (s, t) not in have]
print("    missing: " + ", ".join(missing) if missing else f"    ok  HOSP_* objects present; S3 bucket {C.S3_BUCKET or '(not set!)'}, key {'found' if C.S3_KEY_FILE.exists() else 'MISSING'}")
sys.exit(1 if missing or not C.S3_BUCKET or not C.S3_KEY_FILE.exists() else 0)
PYEOF
fi
if step 2 "Access layer: HEALTH_ITSM, HEALTH_GOV, four roles, four logins"; then "$PY" "$ROOT/setup/01_access.py"; fi
if step 3 "Claude key for typed questions (optional)"; then
  if [[ -s "$ROOT/$HC_ANTHROPIC_KEY_FILE" || -s "$HC_ANTHROPIC_KEY_FILE" ]]; then ok "key file present"
  else printf '    \033[0;33mskip\033[0m  no %s: typed questions will say Claude is not set up (see anthropic.env.example)\n' "$HC_ANTHROPIC_KEY_FILE"; fi
fi
if step 4 "Access-desk service"; then "$ROOT/service/run.sh"; fi
if step 5 "Console on dash-server"; then "$PY" "$ROOT/dash/deploy.py"; fi
if step 6 "Preflight, with a clean start"; then "$ROOT/setup/preflight.sh" --reset; fi
