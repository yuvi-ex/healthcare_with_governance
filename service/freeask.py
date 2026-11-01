"""Ask your own question: Claude writes ONE read-only query from the views the signed-in person may read, the query runs
as that person, and Claude says the answer in plain words.

Safety does not depend on the model. Claude only sees the catalogue of views this login can read (read from Exasol AS this
login), the query must be a single SELECT, and it runs in a session of the signed-in person: Exasol decides what comes back,
exactly as for the six fixed questions. The API key is read from HC_ANTHROPIC_KEY_FILE (secrets/anthropic.env) and never leaves this service.
"""
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import ops

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.anthropic.com/v1/messages"
SQL_MODEL = SAY_MODEL = ops.hcconfig.CLAUDE_MODEL
MAX_ROWS = 50
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|GRANT|REVOKE|TRUNCATE|EXECUTE|IMPORT|EXPORT|COMMIT|ROLLBACK|IMPERSONATE|OPEN|CLOSE)\b", re.I)


def _key():
    f = ops.hcconfig.ANTHROPIC_KEY_FILE
    key = dict(l.strip().split("=", 1) for l in open(f) if "=" in l).get("ANTHROPIC_API_KEY", "") if f.exists() else ""
    if not key:
        raise RuntimeError("Claude is not set up (no ANTHROPIC_API_KEY in secrets/anthropic.env). Ask one of the six questions instead.")
    return key


def _claude(model, system, user, max_tokens=4000, think=True):
    body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]}
    if not think:
        # a two-sentence summary needs no thinking budget; Sonnet 5.5 spells "off" as between_tools
        body["thinking"] = {"type": "between_tools" if "sonnet" in model else "disabled"}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"x-api-key": _key(), "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=45).read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("Claude is not set up: the API key in secrets/anthropic.env was rejected. "
                               "Ask one of the six questions instead.") from e
        raise RuntimeError(f"Claude API {e.code}") from e
    except Exception as e:  # noqa: BLE001 - no network on the day
        raise RuntimeError("Claude is not reachable (no internet?). Ask one of the six questions instead.") from e
    return "".join(c.get("text", "") for c in r.get("content", []))


CATALOG_SQL = ("SELECT v.VIEW_SCHEMA, v.VIEW_NAME, v.VIEW_COMMENT FROM EXA_ALL_VIEWS v "
               "WHERE v.VIEW_SCHEMA IN ('HEALTH_GOV', 'HEALTH_ITSM') ORDER BY 1, 2")
COLS_SQL = ("SELECT COLUMN_SCHEMA, COLUMN_TABLE, COLUMN_NAME, COLUMN_TYPE FROM EXA_ALL_COLUMNS "
            "WHERE COLUMN_SCHEMA IN ('HEALTH_GOV', 'HEALTH_ITSM') ORDER BY 1, 2, COLUMN_ORDINAL_POSITION")
HIDE = {"VISIBLE_RECORDS", "VISIBLE", "PERSON", "VISIBLE_BRANCHES", "TICKET_STATE"}   # plumbing, not for questions


def catalog(token):
    """The views THIS login may read, with their descriptions and columns, read from Exasol as this login."""
    views, cols = ops._as(token, (CATALOG_SQL, None), (COLS_SQL, None))
    by = {}
    for c in cols["rows"]:
        by.setdefault((c["COLUMN_SCHEMA"], c["COLUMN_TABLE"]), []).append(f'{c["COLUMN_NAME"]} {c["COLUMN_TYPE"]}')
    out = []
    for v in views["rows"]:
        if v["VIEW_NAME"] in HIDE:
            continue
        k = (v["VIEW_SCHEMA"], v["VIEW_NAME"])
        out.append(f'{k[0]}.{k[1]}: {v["VIEW_COMMENT"] or ""}\n  columns: {", ".join(by.get(k, []))}')
    return out


SYSTEM_SQL = """You write ONE Exasol SQL query that answers a hospital user's question, using ONLY the views listed below.
Those are the only views this person may read. Rules:
- A single SELECT (WITH ... SELECT is fine). Never write to the database. No semicolon.
- Exasol dialect. Reserved words must be avoided as aliases. Use LIMIT 50 at most.
- Branch codes: CHN = Branch A (legacy HIS), BLR = Branch B (modern EHR), HYD = Branch C (both).
- The patient Meenakshi Sundaram has UNIFIED_ID 'WC-000468'. "her" / "the patient" means her unless the question says otherwise.
- Prefer few, readable columns. Do not invent columns. Names may be pseudonyms for some people: that is expected.
- If the question cannot be answered from these views, do not guess: say so.
Reply with JSON only: {"sql": "...", "about": "<one short sentence: what the query does>"} or {"cannot": "<one short sentence why>"}."""

SYSTEM_SAY = """You turn a database result into a short, plain answer for a business audience at a hospital group.
At most 2 sentences, no SQL, no jargon, no lists of more than 4 names. Count carefully before you write; never correct yourself.
Use only the rows given. Names like 'Patient 1a2b3c', or empty name, birth date or phone fields, mean those details are HIDDEN
from this person by their access: say so plainly ("names and phone numbers are hidden from you"), never call them missing.
Do not comment on data quality. If there are no rows, say that nothing this person may see matches.
If exactly 50 rows came back, the list was cut at 50: say "at least 50", and do not describe the 50 as all of them."""


def _parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("Claude did not return a query")
    return json.loads(m.group(0))


def safe(sql):
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        return None, "more than one statement"
    if not re.match(r"^(SELECT|WITH)\b", s, re.I):
        return None, "not a SELECT"
    if FORBIDDEN.search(re.sub(r"'[^']*'", "''", s)):
        return None, "it would change something"
    return s, None


def ask_free(token, question):
    t0 = time.time()
    question = (question or "").strip()[:500]
    if not question:
        raise ops.Refused("Type a question first.")
    cat = catalog(token)
    if not cat:
        return {"question": question, "cannot": "Your job includes no patient data: there is nothing you may ask about.",
                "access": ops._as(token, (ops.Q_ACCESS, None))[0], "secs": time.time() - t0}
    plan = None
    for _ in range(2):  # one retry if the reply is not the JSON asked for
        try:
            plan = _parse(_claude(SQL_MODEL, SYSTEM_SQL + "\n\nViews this person may read:\n" + "\n".join(cat), question))
            break
        except (RuntimeError, ValueError) as e:
            err = str(e)
    if plan is None:
        return {"question": question, "cannot": err if ("reachable" in err or "not set up" in err) else "Claude could not turn that into a query. Try rephrasing it.",
                "secs": time.time() - t0}
    if "cannot" in plan:
        return {"question": question, "cannot": plan["cannot"], "access": ops._as(token, (ops.Q_ACCESS, None))[0], "secs": time.time() - t0}
    sql, why = safe(plan.get("sql", ""))
    if not sql:
        return {"question": question, "cannot": f"The suggested query was not run: {why}.", "sql": plan.get("sql"), "secs": time.time() - t0}
    access, res = ops._as(token, (ops.Q_ACCESS, None), (sql, None))
    res["rows"] = res.get("rows", [])[:MAX_ROWS]
    answer = ""
    if not res.get("refused"):
        names = {"CHN": "Branch A", "BLR": "Branch B", "HYD": "Branch C"}
        sample = json.dumps([{k: names.get(v, v) if isinstance(v, str) else v for k, v in r.items()} for r in res["rows"][:25]], default=str)
        try:
            answer = _claude(SAY_MODEL, SYSTEM_SAY, f"Question: {question}\nRows ({len(res['rows'])}): {sample}", max_tokens=300, think=False).strip()
        except RuntimeError:
            answer = f"{len(res['rows'])} rows came back (the summary could not be written: no connection to Claude)."
    return {"question": question, "sql": sql, "about": plan.get("about", ""), "result": res, "access": access,
            "answer": answer, "secs": time.time() - t0}
