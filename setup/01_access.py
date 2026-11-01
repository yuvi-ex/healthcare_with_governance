#!/usr/bin/env python3
"""Access-on-request layer: HEALTH_ITSM + HEALTH_GOV (sql/*.sql, in order), four roles, four logins.
  DR_PRIYA      HC_CLINICIAN   treating physician, Branch B: own branch, full identity; other branches by ticket
  ANALYST_RAVI  HC_ANALYST     quality analyst: every branch, identities masked; cannot request
  OWNER_ANITA   HC_DATA_OWNER  records officer, Branch A: approves or revokes tickets for Branch A; no patient data
  AUDITOR_SAM   HC_AUDITOR     compliance: tickets and the audit trail; no patient data
Passwords are generated once into secrets/hc_users.env (mode 600) and never printed. Touches nothing outside
HEALTH_ITSM, HEALTH_GOV, the HC_* roles and these four users.
  .venv/bin/python setup/01_access.py
"""
import os
import secrets
import sys
from pathlib import Path

import pyexasol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENV = hcconfig.USERS_FILE
USERS = {"DR_PRIYA": "HC_CLINICIAN", "ANALYST_RAVI": "HC_ANALYST", "OWNER_ANITA": "HC_DATA_OWNER", "AUDITOR_SAM": "HC_AUDITOR"}


def statements(path):
    out, buf = [], []
    for line in open(path):
        s = line.strip()
        if not buf and (not s or s.startswith("--")):
            continue
        buf.append(line)
        if s.split("--", 1)[0].rstrip().endswith(";"):
            stmt = "".join(buf).rstrip()
            out.append(stmt[: stmt.rfind(";")])
            buf = []
    return out


def admin():
    return hcconfig.exasol()


def main():
    con = admin()
    for st in [st for f in sorted((ROOT / "sql").glob("*.sql")) for st in statements(f)]:
        try:
            con.execute(st)
        except pyexasol.ExaQueryError as e:
            if not (st.startswith("CREATE ROLE") and "conflicts" in e.message):
                sys.exit(f"failed: {st[:90]}\n{e.message}")
    pw = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l) if ENV.exists() else {}
    existing = {r[0] for r in con.execute("SELECT USER_NAME FROM EXA_DBA_USERS").fetchall()}
    for u, role in USERS.items():
        pw.setdefault(u, "Hc" + secrets.token_urlsafe(18).replace("-", "x").replace("_", "y"))
        con.execute(f'{"ALTER" if u in existing else "CREATE"} USER {u} IDENTIFIED BY "{pw[u]}"')
        con.execute(f"GRANT CREATE SESSION TO {u}")
        con.execute(f"GRANT {role} TO {u}")
    old = os.umask(0o077)
    ENV.write_text("".join(f"{u}={pw[u]}\n" for u in USERS))
    os.umask(old)
    con.commit()
    print(f"access layer ready: roles {', '.join(sorted(set(USERS.values())))}; users {', '.join(USERS)} (passwords in {ENV})")


if __name__ == "__main__":
    main()
