"""HTML builders for the access-desk console. Pure functions of what the service returned; no data access here."""
import html as _h
from datetime import datetime, timezone

BR = {"CHN": "Branch A", "BLR": "Branch B", "HYD": "Branch C", "every branch": "every branch"}
SYS = {"LEGACY_HIS": "Legacy HIS", "MODERN_EHR": "Modern EHR"}
PEOPLE = {  # one-click sign-in cards; the password is never in the page
    "DR_PRIYA": ("Dr. Priya Nair", "Treating physician, Branch B", "HC_CLINICIAN", "#0B1B34"),
    "OWNER_ANITA": ("Anita Rao", "Records officer, Branch A (data owner)", "HC_DATA_OWNER", "#C56A00"),
    "ANALYST_RAVI": ("Ravi Kumar", "Quality analyst, all branches", "HC_ANALYST", "#5B5FE0"),
    "AUDITOR_SAM": ("Sam Thomas", "Compliance auditor", "HC_AUDITOR", "#12796A"),
}

CSS = """
.ubar { display:flex; align-items:center; gap:.8rem; flex-wrap:wrap; border-radius:16px; border:1px solid var(--edge); background:#fff;
  padding:.55rem .8rem; margin:.2rem 0 .6rem; }
.ubar .who { font-size:.92rem; color:var(--ink2); } .ubar .who b { font-weight:800; }
.ubar .who code { font-size:.78rem; } .ubar .sp { flex:1; }
.role { display:inline-block; font-size:.62rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; border-radius:999px;
  padding:.15rem .55rem; background:#E3F5F1; color:#12796A; margin-left:.3rem; }
.role.none { background:#F1F4F9; color:var(--faint); }
.cards4 { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem; margin:.6rem 0 1rem; }
.pc { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.9rem 1rem; cursor:pointer; text-align:left;
  font-family:inherit; box-shadow:var(--shadow); border-top:5px solid var(--c); display:flex; flex-direction:column; gap:.2rem; }
.pc:hover { filter:brightness(.98); transform:translateY(-1px); }
.pc .n { font-weight:900; font-size:1.05rem; color:var(--ink2); } .pc .j { font-size:.84rem; color:var(--muted); }
.pc .u { font-family:'JetBrains Mono',monospace; font-size:.74rem; color:var(--ink2); margin-top:.35rem; }
.pc .r { font-size:.62rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--c); }
.lform { display:grid; grid-template-columns:minmax(0,14rem) minmax(0,14rem) auto; gap:.5rem; align-items:center; }
.blk { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.9rem 1rem; margin:.6rem 0; }
.blk .k { font-size:.64rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); margin-bottom:.35rem; }
.blk .t { font-weight:900; font-size:1.15rem; color:var(--ink2); }
.meta { font-size:.72rem; color:var(--faint); margin-top:.45rem; } .meta code { font-size:.7rem; }
.acc { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; }
.chip { display:inline-flex; gap:.35rem; align-items:center; border-radius:999px; padding:.3rem .75rem; font-size:.84rem; font-weight:700;
  background:#F1F4F9; color:var(--ink2); }
.chip.std { background:#E2F4FF; color:#0B4F7A; } .chip.tk { background:#E3F5F1; color:#0E5E52; border:1px solid #9ED9CE; }
.chip.lock { background:#FFF4E5; color:#9A4A00; } .chip.open { background:#E3F5F1; color:#12796A; }
.chip .m { font-family:'JetBrains Mono',monospace; font-size:.74rem; font-weight:700; }
.recs { display:grid; gap:.45rem; margin-top:.5rem; }
.rr { display:grid; grid-template-columns:7.5rem minmax(0,1fr) auto; gap:.6rem; align-items:center; border-radius:12px; border:1px solid var(--edge);
  padding:.45rem .7rem; } .rr.locked { background:repeating-linear-gradient(135deg,#FFFBF4 0 10px,#FFF4E5 10px 20px); border-color:#F1D2A6; }
.rr .b { font-weight:800; font-size:.9rem; } .rr .s { font-size:.82rem; color:var(--muted); } .rr .s code { font-size:.76rem; }
.ok { border-radius:14px; border:1px solid #CDEBE4; border-left:6px solid #1FA08B; background:#F2FBF8; padding:.65rem .85rem; margin:.4rem 0; }
.warn { border-radius:14px; border:1px solid #F1D2A6; border-left:6px solid #D98A00; background:#FFFBF2; padding:.65rem .85rem; margin:.4rem 0; color:#6B3E00; }
.warn b, .ok b { font-weight:900; }
.alert { border-radius:14px; border:1px solid #F3C2C8; border-left:6px solid #C8102E; background:#FFF7F8; padding:.7rem .9rem; margin:.4rem 0; }
.alert .h { font-weight:900; color:#C8102E; font-size:1.08rem; } .alert .d { font-size:.9rem; color:var(--ink2); margin-top:.2rem; line-height:1.45; }
.refused { border-radius:12px; border:1px solid #F3C2C8; background:#FFF5F6; padding:.55rem .8rem; font-size:.88rem; color:#8E0A20; margin:.4rem 0; }
.refused b { font-weight:900; } .refused code { font-size:.76rem; color:#5B0A18; }
.tbl { width:100%; border-collapse:collapse; font-size:.84rem; }
.tbl th { text-align:left; font-size:.62rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); padding:.35rem .5rem;
  border-bottom:1px solid var(--edge); } .tbl td { padding:.42rem .5rem; border-bottom:1px solid #EEF2F7; vertical-align:top; color:var(--ink2); }
.tbl tr.no td { background:#FFF7F8; } .tbl code { font-size:.72rem; } .tblw { overflow-x:auto; }
.st { display:inline-block; font-size:.62rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; border-radius:999px; padding:.12rem .5rem; }
.st.PENDING { background:#FFF4E5; color:#9A4A00; } .st.ACTIVE { background:#E3F5F1; color:#12796A; } .st.EXPIRED { background:#F1F4F9; color:#5B6B80; }
.st.REVOKED, .st.REJECTED { background:#FDE7EA; color:#C8102E; } .st.ran { background:#E3F5F1; color:#12796A; } .st.refused { background:#FDE7EA; color:#C8102E; }
.rq { display:grid; gap:.5rem; } .rq textarea { min-height:3.6rem; resize:vertical; }
.btns { display:flex; gap:.4rem; flex-wrap:wrap; }
.btn.red { background:linear-gradient(135deg,#8E0A20 0%,#C8102E 100%); border-color:#C8102E; }
.btn.amber { background:linear-gradient(135deg,#9A4A00 0%,#C56A00 100%); border-color:#C56A00; }
.grid2 { display:grid; grid-template-columns:minmax(0,1.15fr) minmax(0,1fr); gap:1.2rem; align-items:start; }
.steps { list-style:none; margin:.3rem 0; padding:0; counter-reset:s; }
.steps li { counter-increment:s; display:grid; grid-template-columns:1.5rem minmax(0,1fr) auto; gap:.5rem; padding:.4rem 0; border-top:1px dashed #E5EAF1; font-size:.86rem; }
.steps li:first-child { border-top:0; } .steps li::before { content:counter(s); width:1.4rem; height:1.4rem; border-radius:50%; background:#12796A; color:#fff;
  font-weight:800; font-size:.72rem; display:flex; align-items:center; justify-content:center; } .steps li .s { color:var(--faint); font-size:.74rem; }
.sec { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; }
.sec .c { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.75rem .9rem; display:grid; grid-template-columns:2rem minmax(0,1fr); gap:.6rem; }
.sec .c svg { width:26px; height:26px; } .sec .c b { display:block; font-size:.98rem; color:var(--ink2); } .sec .c span { font-size:.84rem; color:var(--muted); line-height:1.4; }
.sec .c.gap { border-color:#F1D2A6; background:#FFFBF2; }
.matrix td:first-child { font-weight:800; white-space:nowrap; } .matrix td.y { color:#12796A; font-weight:700; } .matrix td.n { color:#C8102E; font-weight:700; }
@media (max-width:1100px) { .cards4 { grid-template-columns:1fr 1fr; } .grid2, .sec { grid-template-columns:1fr; } .lform { grid-template-columns:1fr; } }
"""


def e(x):
    return _h.escape("" if x is None else str(x))


def hm(ts):
    """Exasol returns SYSTIMESTAMP values (UTC); show them in the presenter's local time."""
    s = str(ts or "")
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone().strftime("%H:%M")
    except ValueError:
        return s[11:16] if len(s) >= 16 else s


def left(secs):
    try:
        s = int(float(secs))
    except (TypeError, ValueError):
        return ""
    return f"{s // 60} min {s % 60:02d} s left" if s < 3600 else f"{s // 3600} h {s % 3600 // 60} min left"


def meta(user, view, res):
    return f'<div class="meta">as <code>{e(user)}</code> &middot; <code>{e(view)}</code> &middot; {res.get("secs", 0):.2f} s</div>'


def refused(res, label=None):
    what = f"<b>{e(label)}:</b> " if label else ""
    return f'<div class="refused"><b>Refused by Exasol.</b> {what}{e(res.get("refused"))}<div class="meta">statement: <code>{e(res.get("sql"))[:200]}</code></div></div>'


def access_banner(user, res):
    if res.get("refused"):
        return refused(res)
    chips = []
    for r in res["rows"]:
        if r["BASIS"] == "Standing":
            lvl = "full identity" if r["PHI_LEVEL"] == "FULL" else "identities masked"
            chips.append(f'<span class="chip std">Standing access &middot; {e(BR.get(r["BRANCH"], r["BRANCH"]))} &middot; {lvl}</span>')
        else:
            chips.append(f'<span class="chip tk"><span class="m">{e(r["TICKET"])}</span> {e(BR.get(r["BRANCH"], r["BRANCH"]))} records of '
                         f'<span class="m">{e(r["UNIFIED_ID"])}</span> &middot; {left(r["SECONDS_LEFT"])}</span>')
    return (f'<div class="blk"><div class="k">What you may see right now</div><div class="acc">{"".join(chips) or "nothing"}</div>'
            f'{meta(user, "HEALTH_GOV.MY_ACCESS", res)}</div>')


def records(user, rec, orders):
    if rec.get("refused"):
        return refused(rec)
    rows = rec["rows"]
    name = rows[0]["PATIENT_NAME"] if rows else "Patient"
    lines = []
    for r in rows:
        b, s = BR.get(r["BRANCH"], r["BRANCH"]), SYS.get(r["SOURCE_SYSTEM"], r["SOURCE_SYSTEM"])
        if r["ACCESS"] == "locked":
            lines.append(f'<div class="rr locked"><div class="b">{e(b)}</div><div class="s">{e(s)} &middot; the patient index knows this record exists</div>'
                         f'<span class="chip lock">locked</span></div>')
        else:
            via = f'via <span class="m">{e(r["TICKET"])}</span>' if r["TICKET"] else "standing access"
            lines.append(f'<div class="rr"><div class="b">{e(b)}</div><div class="s">{e(s)} &middot; <code>{e(r["RECORD_ID"])}</code></div>'
                         f'<span class="chip open">open &middot; {via}</span></div>')
    od = "".join(f'<div class="s" style="margin-top:.25rem">{e(BR.get(o["BRANCH"], o["BRANCH"]))}: <b>{e(o["DRUG"])}</b> {e(o["DOSE"])} '
                 f'<span class="st {"PENDING" if o["ORDER_STATUS"] == "draft" else "ACTIVE"}">{e(o["ORDER_STATUS"])}</span></div>'
                 for o in orders.get("rows", []))
    return (f'<div class="blk"><div class="k">Your patient today</div><div class="t">{e(name)}</div>'
            f'<div class="recs">{"".join(lines)}</div><div class="k" style="margin-top:.7rem">Current orders you can see</div>{od or "none"}'
            f'{meta(user, "HEALTH_GOV.PATIENT_RECORDS + ORDERS", rec)}</div>')


def safety(user, alerts, rec):
    if alerts.get("refused"):
        return refused(alerts)
    locked = [BR.get(r["BRANCH"], r["BRANCH"]) for r in rec.get("rows", []) if r["ACCESS"] == "locked"]
    head = '<div class="k">Is the prescription drafted now safe for her?</div>'
    if alerts["rows"]:
        a = alerts["rows"][0]
        body = (f'<div class="alert"><div class="h">Stop: {e(a["DRUG"])} is a {e(str(a["DRUG_CLASS"]).lower())}</div>'
                f'<div class="d">{e(BR.get(a["ALLERGY_BRANCH"]))} recorded <b>{e(a["ALLERGY_AS_RECORDED"])}</b> ({e(a["SEVERITY"])}). '
                f'The order was drafted at {e(BR.get(a["ORDER_BRANCH"]))}, whose system holds no allergy for her.</div>'
                f'<div class="meta">The {e(BR.get(a["ALLERGY_BRANCH"]))} record was opened by ticket <code>{e(a["TICKET"])}</code>; '
                f'when it closes, so does this view of it.</div></div>')
    elif locked:
        body = (f'<div class="warn"><b>No conflict in the records you can open.</b> But her record at {e(", ".join(BR.get(b, b) for b in locked))} is locked, '
                f'so an allergy recorded there cannot be checked.</div>')
    else:
        body = '<div class="ok"><b>No conflict</b> in any of her records.</div>'
    return f'<div class="blk">{head}{body}{meta(user, "HEALTH_GOV.ALLERGY_ALERTS", alerts)}</div>'


def ticket_table(rows, cols, empty="No tickets yet."):
    if not rows:
        return f'<div class="s" style="color:var(--muted)">{empty}</div>'
    head = "".join(f"<th>{e(c)}</th>" for c, _ in cols)
    body = "".join("<tr>" + "".join(f"<td>{f(r)}</td>" for _, f in cols) + "</tr>" for r in rows)
    return f'<div class="tblw"><table class="tbl"><tr>{head}</tr>{body}</table></div>'


def status(r):
    extra = f' &middot; {left(r.get("SECONDS_LEFT"))}' if r.get("STATUS") == "ACTIVE" else ""
    return f'<span class="st {e(r["STATUS"])}">{e(r["STATUS"]).lower()}</span>{extra}'


def my_requests(user, res):
    if res.get("refused"):
        return refused(res)
    cols = [("Ticket", lambda r: f'<code>{e(r["TICKET"])}</code>'), ("Records at", lambda r: e(BR.get(r["BRANCH"]))),
            ("Reason", lambda r: e(r["REASON"])), ("Raised", lambda r: hm(r["CREATED_AT"])), ("Status", status),
            ("Decided by", lambda r: e(r["APPROVED_BY"] or r["CLOSED_BY"] or ""))]
    return (f'<div class="blk"><div class="k">Your access requests</div>{ticket_table(res["rows"], cols)}'
            f'{meta(user, "HEALTH_ITSM.MY_REQUESTS", res)}</div>')


def masked_alerts(user, res):
    if res.get("refused"):
        return refused(res)
    cols = [("Patient", lambda r: f'<b>{e(r["PATIENT_NAME"])}</b>'), ("Order", lambda r: f'{e(r["DRUG"])} ({e(r["ORDER_STATUS"])}) &middot; {e(BR.get(r["ORDER_BRANCH"]))}'),
            ("Allergy", lambda r: f'{e(r["ALLERGY_AS_RECORDED"])} &middot; {e(BR.get(r["ALLERGY_BRANCH"]))}')]
    return (f'<div class="blk"><div class="k">Allergy conflicts across every branch, identities masked</div>'
            f'<div class="t">{len(res["rows"])} current orders clash with an allergy</div>{ticket_table(res["rows"], cols, "None.")}'
            f'<div class="s" style="font-size:.82rem;color:var(--muted);margin-top:.4rem">Pseudonyms come from the view: the names never leave the database for this login.</div>'
            f'{meta(user, "HEALTH_GOV.ALLERGY_ALERTS", res)}</div>')


def tickets(user, res):
    if res.get("refused"):
        return refused(res)
    cols = [("Ticket", lambda r: f'<code>{e(r["TICKET"])}</code>'), ("Requester", lambda r: e(r["REQUESTER_NAME"] or r["REQUESTER"])),
            ("Patient", lambda r: f'<code>{e(r["UNIFIED_ID"])}</code>'), ("Records at", lambda r: e(BR.get(r["BRANCH"]))),
            ("Reason", lambda r: e(r["REASON"])), ("Status", status), ("Approved", lambda r: f'{e(r["APPROVED_BY"] or "")} {hm(r["APPROVED_AT"])}'),
            ("Closed", lambda r: f'{e((r["CLOSED_AS"] or "").lower())} {e(r["CLOSED_BY"] or "")} {hm(r["CLOSED_AT"])}')]
    return f'<div class="blk"><div class="k">Every ticket</div>{ticket_table(res["rows"], cols)}{meta(user, "HEALTH_ITSM.TICKETS", res)}</div>'


def audit(user, res):
    if res.get("refused"):
        return refused(res)
    groups = {}  # the same statement by the same person under the same ticket: one row, with how often and when last
    own = 0
    for r in res["rows"]:
        if r["USER_NAME"] == user and r["COMMAND_NAME"] == "SELECT" and "CURRENT_USER" not in r["SQL_TEXT"]:
            own += 1  # this screen's own refreshes: logged like everything else, left out of the view
            continue
        k = (r["USER_NAME"], r["SQL_TEXT"], str(r["SUCCESS"]), r["TICKET"])
        if k in groups:
            groups[k]["N"] += 1
        else:
            groups[k] = dict(r, N=1)
    body = ""
    for r in list(groups.values())[:30]:
        ran = r["SUCCESS"] in (True, "true", "TRUE", 1)
        tk = f'<code>{e(r["TICKET"])}</code>' if r["TICKET"] else ""
        err = f'<div class="meta">{e(r["ERROR_TEXT"])}</div>' if r["ERROR_TEXT"] else ""
        body += (f'<tr class="{"" if ran else "no"}"><td>{hm(r["START_TIME"])}</td>'
                 f'<td><b>{e(r["DISPLAY_NAME"])}</b><div class="meta" style="margin:0">{e(r["USER_NAME"])}</div></td>'
                 f'<td><span class="st {"ran" if ran else "refused"}">{"ran" if ran else "refused"}</span></td>'
                 f'<td>{tk}</td><td><code>{e(r["SQL_TEXT"])}</code>{err}</td><td>{"&times;" + str(r["N"]) if r["N"] > 1 else ""}</td></tr>')
    return (f'<div class="blk"><div class="k">Audit trail: every statement by these people, with the ticket in force</div>'
            f'<div class="tblw"><table class="tbl"><tr><th>Last</th><th>Who</th><th></th><th>Ticket in force</th><th>Statement</th><th>Times</th></tr>{body}</table></div>'
            f'<div class="s" style="font-size:.8rem;color:var(--muted);margin-top:.4rem">Written by Exasol itself, not by this console, since the demo was last reset. '
            f'A statement appears here about a minute after it runs. This screen\'s own {own} reads of the trail are logged too, and left out here.</div>'
            f'{meta(user, "HEALTH_ITSM.AUDIT_TRAIL", res)}</div>')


CHART_CSS = """
.pt { display:flex; align-items:baseline; gap:.8rem; flex-wrap:wrap; } .pt .n { font-weight:900; font-size:1.4rem; color:var(--ink2); }
.pt .d { font-size:.88rem; color:var(--muted); }
.lockcard { border-radius:18px; border:2px dashed #E3B068; background:repeating-linear-gradient(135deg,#FFFBF4 0 12px,#FFF4E5 12px 24px);
  padding:.9rem 1rem; margin:.6rem 0; display:grid; grid-template-columns:2.4rem minmax(0,1fr); gap:.8rem; align-items:center; }
.lockcard svg { width:34px; height:34px; } .lockcard b { font-size:1.02rem; color:#7A3E00; display:block; }
.lockcard span { font-size:.88rem; color:#6B3E00; line-height:1.45; }
.tl { display:grid; gap:.35rem; margin-top:.3rem; text-align:left; }
.tl .v { display:grid; grid-template-columns:6.2rem 5.6rem minmax(0,1fr) auto; gap:.6rem; align-items:center; border-bottom:1px solid #EEF2F7; padding:.35rem 0; font-size:.88rem; }
.tl .v:last-child { border-bottom:0; } .tl .v .dt { font-variant-numeric:tabular-nums; font-weight:700; color:var(--ink2); }
.tl .v .dx { color:var(--ink2); text-align:left; } .tl .v .dx span { color:var(--muted); font-size:.8rem; }
.br { display:inline-block; font-size:.62rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; border-radius:8px; padding:.15rem .45rem; text-align:center; }
.br.CHN { background:#FFF4E5; color:#9A4A00; } .br.BLR { background:#E2F4FF; color:#0076AD; } .br.HYD { background:#EEF0FF; color:#3B3FB8; }
.tk { font-family:'JetBrains Mono',monospace; font-size:.68rem; color:#0E5E52; background:#E3F5F1; border-radius:6px; padding:.05rem .35rem; white-space:nowrap; }
.scans { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin-top:.4rem; }
.scan { border-radius:14px; border:1px solid var(--edge); overflow:hidden; background:#fff; }
.scan img { display:block; width:100%; height:11rem; object-fit:contain; background:#000; }
.scan .c { padding:.5rem .65rem; font-size:.82rem; } .scan .c b { display:block; font-size:.9rem; color:var(--ink2); }
.scan .c a { font-weight:800; color:#0076AD; text-decoration:none; font-size:.8rem; }
details.note { border-top:1px dashed #E5EAF1; padding:.35rem 0; } details.note:first-of-type { border-top:0; }
details.note summary { cursor:pointer; font-size:.88rem; color:var(--ink2); } details.note summary b { font-weight:800; }
details.note p, details.note div.tx { font-family:'JetBrains Mono',monospace; font-size:.74rem; line-height:1.55; color:#3B3000; background:#FFFBEA;
  border:1px solid #F5E3A1; border-radius:10px; padding:.5rem .7rem; margin:.35rem 0 .2rem; }
.meds { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.25rem 1rem; font-size:.86rem; margin-top:.3rem; }
@media (max-width:1100px) { .scans, .meds { grid-template-columns:1fr; } .tl .v { grid-template-columns:5.6rem 1fr; } }
"""
LOCK_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="#C56A00" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>')
SYSL = {"LEGACY_HIS": "Legacy HIS", "MODERN_EHR": "Modern EHR"}


def br(code):
    return f'<span class="br {e(code)}">{e(BR.get(code, code))}</span>'


def tk(t):
    return f'<span class="tk">{e(t)}</span>' if t else ""


def dmy(d):
    s = str(d or "")[:10]
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}" if len(s) == 10 else s


def chart(user, d):
    """The doctor's view of one patient: what she may open, live from every branch; locked branches shown as locked."""
    rec, ident = d["records"], d["identity"]
    if rec.get("refused"):
        return refused(rec)
    locked = sorted({r["BRANCH"] for r in rec["rows"] if r["ACCESS"] == "locked"})
    name = (rec["rows"] or [{}])[0].get("PATIENT_NAME", "Patient")
    idr = ident.get("rows", [])
    age = next((2026 - int(r["BIRTH_YEAR"]) for r in idr if r.get("BIRTH_YEAR")), None)
    ids = " ".join(f'{br(r["BRANCH"])} <code>{e(r["RECORD_ID"])}</code> {tk(r["TICKET"])}' for r in idr)
    head = (f'<div class="blk"><div class="k">Patient chart &middot; live from every branch she may open</div>'
            f'<div class="pt"><span class="n">{e(name)}</span><span class="d">{"F" if (idr[:1] or [{}])[0].get("SEX") in ("F", "female") else ""}'
            f'{f" &middot; {age} years" if age else ""}</span></div><div class="s" style="margin-top:.35rem;font-size:.86rem">{ids}</div>'
            f'{meta(user, "HEALTH_GOV.PATIENT_IDENTITY", ident)}</div>')
    lock = "".join(f'<div class="lockcard">{LOCK_SVG}<div><b>Her {e(BR.get(b))} record is locked</b><span>Visits, diagnoses, discharge notes, '
                   f'medications, allergies and scans held at {e(BR.get(b))} stay closed to you. The patient index knows the record exists; '
                   f'the data owner of {e(BR.get(b))} can open it for a set time.</span></div></div>' for b in locked)
    enc = d["encounters"]
    visits = "".join(f'<div class="v"><span class="dt">{dmy(r["ADMIT_DATE"])}</span>{br(r["BRANCH"])}'
                     f'<span class="dx">{e(r["DIAGNOSIS"])} <span>&middot; {e(r["ENCOUNTER_CLASS"])}, {e(r["DEPARTMENT"])}'
                     f'{" &middot; in a bed now" if r["STATUS"] == "in-progress" else ""}</span></span>{tk(r["TICKET"])}</div>' for r in enc.get("rows", []))
    visits = refused(enc) if enc.get("refused") else (f'<div class="blk"><div class="k">Visits and admissions ({len(enc["rows"])})</div>'
                                                       f'<div class="tl">{visits}</div>{meta(user, "HEALTH_GOV.ENCOUNTERS", enc)}</div>')
    img = d["imaging"]
    cards = "".join(f'<div class="scan"><img src="{e(r["THUMB_URL"])}" alt="{e(r["STUDY_DESCRIPTION"])}"/><div class="c">'
                    f'<b>{dmy(r["STUDY_DATE"])} &middot; {e(r["STUDY_DESCRIPTION"])}</b>{br(r["BRANCH"])} {e(r["MODALITY"])} &middot; '
                    f'{int(r["FILE_BYTES"] or 0) / 1e6:.1f} MB DICOM {tk(r["TICKET"])}<div style="margin-top:.3rem">'
                    f'<a href="{e(r["DICOM_URL"])}" target="_blank" rel="noopener">Original DICOM &rarr;</a> '
                    f'<span class="meta" style="display:inline">{("by ticket " + e(r["TICKET"]) + " · closes in " + str(max(1, r["LINK_SECS"] // 60)) + " min") if r["TICKET"] else "your branch · always available"}</span></div></div></div>' for r in img.get("rows", []))
    scans = refused(img) if img.get("refused") else (
        f'<div class="blk"><div class="k">Imaging: from the PACS on Amazon S3 ({len(img["rows"])})</div><div class="scans">{cards}</div>'
        f'<div class="s" style="font-size:.8rem;color:var(--muted);margin-top:.45rem">The images never pass through the database. The governed '
        f'view returns a study only for a record you may open; only then does the service sign a link, and a ticket\'s links expire with the ticket.</div>'
        f'{meta(user, "HEALTH_GOV.IMAGING", img)}</div>')
    nt = d["notes"]
    notes = "".join(f'<details class="note"><summary><b>{dmy(r["NOTE_DATE"])}</b> {br(r["BRANCH"])} {e(r["NOTE_TYPE"])} '
                    f'&middot; {e(SYSL.get(r["SOURCE_SYSTEM"], r["SOURCE_SYSTEM"]))} {tk(r["TICKET"])}</summary><div class="tx">{e(r["NOTE_TEXT"])}</div></details>'
                    for r in nt.get("rows", []))
    notes = refused(nt) if nt.get("refused") else (f'<div class="blk"><div class="k">Clinical notes, read live from where they were written ({len(nt["rows"])})</div>'
                                                   f'{notes}{meta(user, "HEALTH_GOV.NOTES", nt)}</div>')
    md, al = d["meds"], d["allergies"]
    meds = "".join(f'<div>{br(r["BRANCH"])} <b>{e(r["DRUG"])}</b> {e(r["DOSE"])} <span class="st {"PENDING" if r["ORDER_STATUS"] == "draft" else "ACTIVE" if r["ORDER_STATUS"] == "active" else "EXPIRED"}">'
                   f'{e(r["ORDER_STATUS"])}</span></div>' for r in md.get("rows", []))
    alg = "".join(f'<div>{br(r["BRANCH"])} <b style="color:#C8102E">{e(r["ALLERGY_AS_RECORDED"])}</b> &middot; {e(r["SEVERITY"])} {tk(r["TICKET"])}</div>'
                  for r in al.get("rows", [])) or '<div class="s" style="color:var(--muted)">None on file in the records you can open.</div>'
    medblk = (f'<div class="blk"><div class="k">Allergies</div>{alg}<div class="k" style="margin-top:.7rem">Medications ({len(md.get("rows", []))})</div>'
              f'<div class="meds">{meds}</div>{meta(user, "HEALTH_GOV.ALLERGIES + MEDICATIONS", md)}</div>')
    return head + lock + visits + scans + notes + medblk
