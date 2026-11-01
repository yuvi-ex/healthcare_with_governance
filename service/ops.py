"""The named operations behind the access-desk console. Every one runs as the SIGNED-IN person's own Exasol login.

There is no service account and no SQL from the page: the page names an operation, the service opens a session as that
person (Exasol checks the password), runs the fixed statement, closes the session. What a person may see or do is
decided by Exasol (roles, the governed views, the ticket rules), never here. A refused statement comes back as data
({"refused": "..."}) so the page can show Exasol's own words.
"""
import secrets
import sys
import threading
import time
from pathlib import Path

import pyexasol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DSN = hcconfig.EXA_DSN
HERO = "WC-000468"                           # Meenakshi Sundaram in the patient index
SESSION_TTL = 8 * 3600
_SESSIONS = {}                               # token -> {"user", "password", "at", ...}; memory only, gone on restart
_LOCK = threading.Lock()


class Refused(Exception):
    pass


# Exasol Personal allows 20 parallel connections for everything on this machine (both demos, dash-server). This service
# never holds more than MAX_SESSIONS of them: extra work waits its turn instead of starving the others.
MAX_SESSIONS = 6
_SLOTS = threading.BoundedSemaphore(MAX_SESSIONS)


class _Session:
    """A session as one person, counted against MAX_SESSIONS, always closed."""
    def __init__(self, user, password):
        if not _SLOTS.acquire(timeout=60):
            raise Refused("Exasol is busy (all sessions in use). Try again in a moment.")
        try:
            self.con = _connect_raw(user, password)
        except Exception:
            _SLOTS.release()
            raise

    def __enter__(self):
        return self.con

    def __exit__(self, *exc):
        try:
            self.con.close()
        finally:
            _SLOTS.release()


def _connect_raw(user, password):
    return pyexasol.connect(dsn=DSN, user=user, password=password, encryption=True, websocket_sslopt={"cert_reqs": 0},
                            autocommit=True, client_name="health-access-desk", socket_timeout=60)


def _run(con, sql, params=None):
    t = time.time()
    try:
        st = con.execute(sql, params)
    except pyexasol.ExaQueryError as e:
        return {"sql": sql, "params": params, "rows": [], "refused": e.message.split(" (Session")[0], "secs": time.time() - t}
    if st.result_type == "rowCount":
        return {"sql": sql, "params": params, "rows": [], "written": st.rowcount(), "secs": time.time() - t}
    cols = st.column_names()
    return {"sql": sql, "params": params, "rows": [dict(zip(cols, r)) for r in st.fetchall()], "secs": time.time() - t}


def _as(token, *steps):
    """Open a session as the signed-in person, run the steps, close it. Each step: (sql, params)."""
    with _LOCK:
        s = _SESSIONS.get(token)
    if not s or time.time() - s["at"] > SESSION_TTL:
        raise Refused("Signed out. Sign in again.")
    with _Session(s["user"], s["password"]) as con:
        return [_run(con, sql, params) for sql, params in steps]


# ---------------------------------------------------------------- sign in / out
def login(user, password):
    user = (user or "").strip().upper()
    t = time.time()
    try:
        sess = _Session(user, password or "")
    except pyexasol.ExaError as e:
        msg = getattr(e, "message", str(e)).split(" (Session")[0]
        return {"ok": False, "refused": msg or "Exasol refused the login", "secs": time.time() - t}
    with sess as con:
        roles = [r[0] for r in con.execute("SELECT GRANTED_ROLE FROM EXA_USER_ROLE_PRIVS ORDER BY 1").fetchall()]
        who = con.execute("SELECT DISPLAY_NAME, JOB FROM HEALTH_ITSM.PEOPLE WHERE USER_NAME = CURRENT_USER").fetchone() or (user, "")
    token = secrets.token_urlsafe(24)
    with _LOCK:
        _SESSIONS[token] = {"user": user, "password": password, "at": time.time()}
    return {"ok": True, "token": token, "user": user, "name": who[0], "job": who[1], "roles": roles, "secs": time.time() - t}


def demo_login(user):
    """One-click sign-in for the stage: the password is read from secrets/hc_users.env and checked by Exasol as usual."""
    pw = dict(l.strip().split("=", 1) for l in open(hcconfig.USERS_FILE) if "=" in l)
    if user not in pw:
        return {"ok": False, "refused": "Unknown demo user"}
    return login(user, pw[user])


def logout(token):
    with _LOCK:
        _SESSIONS.pop(token, None)
    return {"ok": True}


# ---------------------------------------------------------------- reads, per job (the views decide what comes back)
Q_ACCESS = "SELECT BASIS, BRANCH, PHI_LEVEL, TICKET, UNIFIED_ID, VALID_UNTIL, SECONDS_LEFT FROM HEALTH_GOV.MY_ACCESS ORDER BY BASIS DESC"
Q_RECORDS = ("SELECT PATIENT_NAME, BRANCH, SOURCE_SYSTEM, ACCESS, RECORD_ID, TICKET FROM HEALTH_GOV.PATIENT_RECORDS "
             "WHERE UNIFIED_ID = {uid} ORDER BY BRANCH DESC")
Q_ORDERS = "SELECT BRANCH, DRUG, DOSE, ORDER_STATUS FROM HEALTH_GOV.ORDERS WHERE UNIFIED_ID = {uid} ORDER BY ORDER_STATUS, DRUG"
Q_ALERTS_ONE = ("SELECT PATIENT_NAME, DRUG, DOSE, ORDER_STATUS, ORDER_BRANCH, DRUG_CLASS, ALLERGY_AS_RECORDED, SEVERITY, "
                "ALLERGY_BRANCH, KNOWN_WHERE_PRESCRIBED, TICKET FROM HEALTH_GOV.ALLERGY_ALERTS WHERE UNIFIED_ID = {uid}")
Q_ALERTS_ALL = ("SELECT PATIENT_NAME, DRUG, ORDER_STATUS, ORDER_BRANCH, DRUG_CLASS, ALLERGY_AS_RECORDED, SEVERITY, ALLERGY_BRANCH "
                "FROM HEALTH_GOV.ALLERGY_ALERTS ORDER BY PATIENT_NAME")
Q_MINE = ("SELECT TICKET, REQ_NO, BRANCH, REASON, MINUTES_REQUESTED, CREATED_AT, STATUS, APPROVED_BY, VALID_UNTIL, SECONDS_LEFT, "
          "CLOSED_AS, CLOSED_BY FROM HEALTH_ITSM.MY_REQUESTS ORDER BY REQ_NO DESC")
Q_QUEUE = ("SELECT TICKET, REQ_NO, REQUESTER, REQUESTER_NAME, REQUESTER_JOB, UNIFIED_ID, BRANCH, REASON, MINUTES_REQUESTED, "
           "CREATED_AT, STATUS, VALID_UNTIL, SECONDS_LEFT, CLOSED_AS FROM HEALTH_ITSM.APPROVAL_QUEUE ORDER BY REQ_NO DESC")
Q_TICKETS = ("SELECT TICKET, REQUESTER, REQUESTER_NAME, UNIFIED_ID, BRANCH, REASON, CREATED_AT, STATUS, SECONDS_LEFT, APPROVED_BY, APPROVED_AT, "
             "VALID_UNTIL, CLOSED_AS, CLOSED_BY, CLOSED_AT FROM HEALTH_ITSM.TICKETS ORDER BY REQ_NO DESC")
Q_AUDIT = ("SELECT USER_NAME, DISPLAY_NAME, START_TIME, COMMAND_NAME, SUCCESS, ERROR_TEXT, SECS, SQL_TEXT, TICKET "
           "FROM HEALTH_ITSM.AUDIT_TRAIL ORDER BY START_TIME DESC LIMIT 150")
INS_REQUEST = ("INSERT INTO HEALTH_ITSM.REQUESTS (REQUESTER, UNIFIED_ID, BRANCH, REASON, MINUTES_REQUESTED, CREATED_AT) "
               "VALUES (CURRENT_USER, {uid}, {branch}, {reason}, {minutes!d}, SYSTIMESTAMP)")
INS_DECISION = ("INSERT INTO HEALTH_ITSM.DECISIONS (REQ_NO, DECISION, DECIDED_BY, DECIDED_AT, VALID_UNTIL, NOTE) "
                "VALUES ({req!d}, {decision}, CURRENT_USER, SYSTIMESTAMP, {until}, {note})")
# The ways round the rules a person might try. Each is refused by Exasol for that role.
PROBES = {
    "raw": ("Read the allergy data directly, past the governed views", "SELECT * FROM HOSP_CORE.ALLERGIES LIMIT 5"),
    "patients": ("Read patient data", "SELECT PATIENT_NAME, BRANCH, ACCESS FROM HEALTH_GOV.PATIENT_RECORDS LIMIT 5"),
    "request": ("Raise an access request",
                "INSERT INTO HEALTH_ITSM.REQUESTS (REQUESTER, UNIFIED_ID, BRANCH, REASON, MINUTES_REQUESTED, CREATED_AT) "
                "VALUES (CURRENT_USER, 'WC-000468', 'CHN', 'probe', 15, SYSTIMESTAMP)"),
    "approve": ("Approve a ticket for themselves",
                "INSERT INTO HEALTH_ITSM.DECISIONS (REQ_NO, DECISION, DECIDED_BY, DECIDED_AT, VALID_UNTIL) "
                "VALUES (12340, 'APPROVE', 'OWNER_ANITA', SYSTIMESTAMP, ADD_MINUTES(SYSTIMESTAMP, 600))"),
    "audit": ("Read the audit trail", "SELECT USER_NAME, SQL_TEXT FROM HEALTH_ITSM.AUDIT_TRAIL LIMIT 5"),
}


def clinician(token, uid=HERO):
    a, rec, orders, alerts, mine = _as(token, (Q_ACCESS, None), (Q_RECORDS, {"uid": uid}), (Q_ORDERS, {"uid": uid}),
                                       (Q_ALERTS_ONE, {"uid": uid}), (Q_MINE, None))
    return {"access": a, "records": rec, "orders": orders, "alerts": alerts, "mine": mine}


def analyst(token):
    a, alerts = _as(token, (Q_ACCESS, None), (Q_ALERTS_ALL, None))
    return {"access": a, "alerts": alerts}


def owner(token):
    (q,) = _as(token, (Q_QUEUE, None))
    return {"queue": q}


def auditor(token):
    t, au = _as(token, (Q_TICKETS, None), (Q_AUDIT, None))
    return {"tickets": t, "audit": au}


def request_access(token, uid, branch, reason, minutes):
    w, mine = _as(token, (INS_REQUEST, {"uid": uid, "branch": branch, "reason": (reason or "")[:500], "minutes": int(minutes)}),
                  (Q_MINE, None))
    return {"insert": w, "mine": mine}


def decide(token, req_no, decision, minutes=None, note=""):
    if decision not in ("APPROVE", "REJECT", "REVOKE"):
        raise Refused("Unknown decision")
    sql = INS_DECISION.replace("{until}", "ADD_MINUTES(SYSTIMESTAMP, {minutes!d})" if decision == "APPROVE" else "NULL")
    params = {"req": int(req_no), "decision": decision, "note": (note or "")[:300]}
    if decision == "APPROVE":
        params["minutes"] = int(minutes or 15)
    w, q = _as(token, (sql, params), (Q_QUEUE, None))
    return {"insert": w, "queue": q}


def probe(token, kind):
    label, sql = PROBES[kind]
    (r,) = _as(token, (sql, None))
    r["label"] = label
    return r


def health():
    """Is Exasol listening? A TCP check, no session: signing in as a person would put the check in their audit trail."""
    import socket
    t = time.time()
    try:
        socket.create_connection((hcconfig.EXA_HOST, hcconfig.EXA_PORT), timeout=3).close()
        return {"exa": True, "secs": time.time() - t}
    except OSError as e:
        return {"exa": False, "error": str(e)[:200]}


# ---------------------------------------------------------------- the whole chart, scans included
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
import json as _json  # noqa: E402

# The PACS bucket and the read-only key of the hospital-chain build (GetObject + ListBucket on this one bucket), from its
# config.env. Read here, never shown. Links are made ONLY for keys the governed view returned to the signed-in person.
S3_KEYFILE = hcconfig.S3_KEY_FILE
BUCKET, REGION = hcconfig.S3_BUCKET, hcconfig.S3_REGION
_S3 = {}

Q_IDENT = ("SELECT BRANCH, SOURCE_SYSTEM, RECORD_ID, NAME_AS_RECORDED, BIRTH_DATE_AS_RECORDED, MOBILE, SEX, BIRTH_YEAR, TICKET "
           "FROM HEALTH_GOV.PATIENT_IDENTITY WHERE UNIFIED_ID = {uid} ORDER BY BRANCH DESC")
Q_ENC = ("SELECT BRANCH, SOURCE_SYSTEM, ENCOUNTER_CLASS, DEPARTMENT, ADMIT_DATE, DISCHARGE_DATE, STATUS, DIAGNOSIS, TICKET "
         "FROM HEALTH_GOV.ENCOUNTERS WHERE UNIFIED_ID = {uid} ORDER BY ADMIT_DATE DESC")
Q_NOTES = ("SELECT BRANCH, SOURCE_SYSTEM, NOTE_TYPE, NOTE_DATE, NOTE_TEXT, TICKET FROM HEALTH_GOV.NOTES "
           "WHERE UNIFIED_ID = {uid} ORDER BY NOTE_DATE DESC")
Q_MEDS = ("SELECT BRANCH, DRUG, DOSE, ORDER_STATUS, DRUG_CLASS, TICKET FROM HEALTH_GOV.MEDICATIONS WHERE UNIFIED_ID = {uid} "
          "ORDER BY CASE WHEN ORDER_STATUS IN ('draft', 'active') THEN 0 ELSE 1 END, BRANCH DESC, DRUG")
Q_ALLERGIES = "SELECT BRANCH, ALLERGY_AS_RECORDED, DRUG_CLASS, SEVERITY, TICKET FROM HEALTH_GOV.ALLERGIES WHERE UNIFIED_ID = {uid}"
Q_IMAGING = ("SELECT BRANCH, STUDY_DATE, MODALITY, BODY_PART, STUDY_DESCRIPTION, ACCESSION_NUMBER, S3_KEY, THUMB_KEY, FILE_BYTES, TICKET "
             "FROM HEALTH_GOV.IMAGING WHERE UNIFIED_ID = {uid} ORDER BY STUDY_DATE DESC")


def _s3():
    if "c" not in _S3:
        import boto3
        from botocore.config import Config
        k = _json.loads(S3_KEYFILE.read_text())["AccessKey"]
        _S3["c"] = boto3.client("s3", region_name=REGION, endpoint_url=f"https://s3.{REGION}.amazonaws.com",
                                config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
                                aws_access_key_id=k["AccessKeyId"], aws_secret_access_key=k["SecretAccessKey"])
    return _S3["c"]


def _sign(key, secs):
    try:
        return _s3().generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=max(60, int(secs)))
    except Exception:  # noqa: BLE001
        return ""


def chart(token, uid=HERO):
    """Every part of the patient's chart the signed-in person may open, read in parallel (one session per part)."""
    steps = {"access": (Q_ACCESS, None), "records": (Q_RECORDS, {"uid": uid}), "identity": (Q_IDENT, {"uid": uid}),
             "encounters": (Q_ENC, {"uid": uid}), "notes": (Q_NOTES, {"uid": uid}), "meds": (Q_MEDS, {"uid": uid}),
             "allergies": (Q_ALLERGIES, {"uid": uid}), "alerts": (Q_ALERTS_ONE, {"uid": uid}), "imaging": (Q_IMAGING, {"uid": uid}),
             "mine": (Q_MINE, None)}
    t = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {k: ex.submit(_as, token, v) for k, v in steps.items()}
        out = {k: f.result()[0] for k, f in futs.items()}
    # a ticket's scans get links that expire no later than the ticket; standing access gets 15 minutes
    left = {r["TICKET"]: float(r["SECONDS_LEFT"] or 0) for r in out["access"]["rows"] if r.get("TICKET")}
    for r in out["imaging"]["rows"]:
        secs = min(900, left.get(r["TICKET"], 900)) if r["TICKET"] else 900
        r["THUMB_URL"], r["DICOM_URL"], r["LINK_SECS"] = _sign(r["THUMB_KEY"], secs), _sign(r["S3_KEY"], secs), int(secs)
        r.pop("S3_KEY"), r.pop("THUMB_KEY")          # the page gets links, not keys
    out["secs"] = time.time() - t
    return out


# ---------------------------------------------------------------- the six questions, answered as the signed-in person
QUESTIONS = {
    "who": [("identity", Q_IDENT), ("records", Q_RECORDS), ("imaging", Q_IMAGING), ("encounters", Q_ENC)],
    "allergy": [("alerts", Q_ALERTS_ONE), ("records", Q_RECORDS), ("allergies", Q_ALLERGIES)],
    "scans": [("imaging", Q_IMAGING), ("records", Q_RECORDS)],
    "similar": [("similar", "SELECT PATIENT_NAME, AGE, BRANCH, DIAGNOSIS, ADMIT_DATE, LENGTH_OF_STAY, SIMILARITY, ANTIBIOTIC, READMITTED_30D "
                            "FROM HEALTH_GOV.SIMILAR_TO_HER ORDER BY SIMILARITY DESC LIMIT 6")],
    "readmit": [("readm", "SELECT BRANCH, COUNT(*) AS READMISSIONS, SUM(CASE WHEN VISIBLE_TO_ONE_SYSTEM THEN 0 ELSE 1 END) AS CROSS_BRANCH "
                          "FROM HEALTH_GOV.READMISSIONS GROUP BY BRANCH ORDER BY BRANCH")],
    "risk": [("alerts", "SELECT PATIENT_NAME, DRUG, DOSE, ORDER_STATUS, ORDER_BRANCH, ALLERGY_AS_RECORDED, SEVERITY, ALLERGY_BRANCH, "
                        "KNOWN_WHERE_PRESCRIBED, TICKET FROM HEALTH_GOV.ALLERGY_ALERTS ORDER BY SEVERITY DESC, PATIENT_NAME")],
}


def ask(token, key, uid=HERO):
    parts = QUESTIONS[key]
    t = time.time()
    steps = [(Q_ACCESS, None)] + [(sql, {"uid": uid} if "{uid}" in sql else None) for _, sql in parts]
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda s: _as(token, s)[0], steps))
    out = {"access": res[0], **{name: r for (name, _), r in zip(parts, res[1:])}}
    if "imaging" in out and key == "scans":
        left = {r["TICKET"]: float(r["SECONDS_LEFT"] or 0) for r in out["access"]["rows"] if r.get("TICKET")}
        for r in out["imaging"]["rows"]:
            secs = min(900, left.get(r["TICKET"], 900)) if r["TICKET"] else 900
            r["THUMB_URL"], r["DICOM_URL"], r["LINK_SECS"] = _sign(r["THUMB_KEY"], secs), _sign(r["S3_KEY"], secs), int(secs)
    for r in out.get("imaging", {}).get("rows", []):
        r.pop("S3_KEY", None), r.pop("THUMB_KEY", None)
    out["secs"] = time.time() - t
    return out
