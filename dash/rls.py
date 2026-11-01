"""Row-level security, shown inside every question, for the SIGNED-IN person: their access list right now, what Exasol did to
this answer (rows kept and why, rows withheld, masking), the rule that did it, and why this is the better way. Built from
the answer itself, so it works the same for 4 users or 4,000."""
from views import BR, PEOPLE, e

CSS = """
.rlsband { margin-top:1rem; border-radius:20px; border:2px solid #1FA08B; background:linear-gradient(180deg,#F2FBF8 0%,#fff 70%); padding:.9rem 1rem; }
.rlsband .k { font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#12796A; }
.rlsband .h { font-weight:900; font-size:1.15rem; color:var(--ink2); margin:.1rem 0 .15rem; }
.rlsband .s { font-size:.86rem; color:var(--muted); margin-bottom:.6rem; }
.rls3 { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:.7rem; align-items:start; }
.rls3 > .rule { grid-column:1 / -1; }
.rls3 > .c, .rls3 > div > .c { border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.6rem .75rem; min-width:0; }
.rls3 .t { font-weight:900; font-size:.95rem; color:var(--ink2); } .rls3 .d { font-size:.8rem; color:var(--muted); margin:.1rem 0 .2rem; }
ul.al { list-style:none; margin:.3rem 0 0; padding:0; display:grid; gap:.3rem; }
ul.al li { font-size:.84rem; color:var(--ink2); border-radius:9px; padding:.35rem .55rem; background:#F6F9FC; border-left:4px solid #9FB0C4; line-height:1.4; }
ul.al li.g-ok { border-left-color:#0076AD; background:#F2F8FC; } ul.al li.g-tk { border-left-color:#1FA08B; background:#F2FBF8; }
ul.al li.g-no { border-left-color:#C8102E; background:#FFF5F6; } ul.al li.g-mk { border-left-color:#5B5FE0; background:#F5F6FF; }
ul.al .why { display:block; font-size:.72rem; color:var(--muted); } ul.al code { font-size:.74rem; }
.rc { border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.6rem .7rem; border-top:5px solid var(--c); min-width:0; }
.rc.me { box-shadow:0 0 0 3px rgba(31,160,139,.35); }
.rc .r { font-size:.58rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--c); }
.rc .n { font-weight:900; color:var(--ink2); font-size:.95rem; } .rc .j { font-size:.74rem; color:var(--muted); }
.rc .acc { font-size:.7rem; color:#0B4F7A; background:#E2F4FF; border-radius:7px; padding:.15rem .4rem; margin:.3rem 0 .1rem; display:inline-block; }
.rc .acc.tk { background:#E3F5F1; color:#0E5E52; } .rc .acc.none { background:#F1F4F9; color:var(--muted); }
.rc .v { font-size:1.45rem; font-weight:900; color:var(--ink2); line-height:1.1; margin-top:.3rem; }
.rc .l { font-size:.78rem; color:var(--muted); margin-top:.1rem; line-height:1.35; } .rc .l i { color:#5B5FE0; }
.rc .no { border-radius:10px; background:#FFF5F6; border:1px solid #F3C2C8; color:#8E0A20; padding:.4rem .5rem; font-size:.76rem; margin-top:.4rem; }
.rc .no b { font-weight:900; }
.rule2 { display:grid; grid-template-columns:minmax(0,1.05fr) minmax(0,1fr); gap:.8rem; margin-top:.8rem; align-items:start; }
.rule2 .c { border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.6rem .75rem; min-width:0; }
.rule2 .c .t { font-weight:900; font-size:.95rem; color:var(--ink2); } .rule2 .c .d { font-size:.8rem; color:var(--muted); margin:.1rem 0 .3rem; }
.tag { display:inline-block; font-size:.58rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; border-radius:999px; padding:.1rem .45rem; margin:.25rem .2rem 0 0; }
.tag.row { background:#E2F4FF; color:#0076AD; } .tag.col { background:#EEF0FF; color:#3B3FB8; } .tag.grant { background:#FDE7EA; color:#C8102E; } .tag.time { background:#E3F5F1; color:#12796A; }
.better { border-radius:14px; background:#0B1B34; color:#fff; padding:.7rem .9rem; }
.better .k2 { font-size:.62rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#5EE0C2; }
.better ol { margin:.35rem 0 0 1.1rem; padding:0; font-size:.86rem; line-height:1.5; } .better b { color:#5EE0C2; }
@media (max-width:1200px) { .rls3 { grid-template-columns:1fr; } }
"""

from collections import Counter

# per question: which part of the answer to explain, what one row is called, and its branch column
PARTS = {"who": [("records", "record", "BRANCH")], "allergy": [("allergies", "allergy", "BRANCH"), ("alerts", "alert", "ORDER_BRANCH")],
         "scans": [("imaging", "scan", "BRANCH")], "similar": [("similar", "patient like her", "BRANCH")],
         "readmit": [("readm", "readmission", "BRANCH")], "risk": [("alerts", "alert", "ORDER_BRANCH")]}


def _plural(n, noun):
    return f"{n} {noun}" if n == 1 else f"{n} {noun.replace('patient like her', 'patients like her')}{'' if noun.startswith('patient like') else 's'}"


def _left(secs):
    try:
        s = int(float(secs))
        return f"{s // 60} min left" if s < 3600 else f"{s // 3600} h {s % 3600 // 60} min left"
    except (TypeError, ValueError):
        return ""


def access_list(tok, d):
    acc = d.get("access") or {}
    roles = ", ".join(tok.get("roles", [])) or "no role"
    if acc.get("refused"):
        items = '<li class="g-no">No patient data: this role reads no governed view.</li>'
    else:
        items = ""
        for a in acc.get("rows", []):
            if a["BASIS"] == "Standing":
                items += (f'<li><b>{e(BR.get(a["BRANCH"], a["BRANCH"]))}</b>, every patient &middot; '
                          f'{"full identity" if a["PHI_LEVEL"] == "FULL" else "identities masked"} <span class="why">by your job</span></li>')
            else:
                items += (f'<li class="g-tk"><b>{e(BR.get(a["BRANCH"]))}</b>, one patient (<code>{e(a["UNIFIED_ID"])}</code>) &middot; full identity '
                          f'<span class="why">by ticket {e(a["TICKET"])} &middot; {_left(a["SECONDS_LEFT"])}</span></li>')
    return (f'<div class="c"><div class="t">1 &middot; Your access list, right now</div><div class="d">Exasol login <code>{e(tok["user"])}</code> &middot; '
            f'{e(roles)}</div><ul class="al">{items}</ul></div>')


def what_it_did(key, d):
    lines, masked, named = [], False, False
    refused = next((v for k, v in d.items() if isinstance(v, dict) and k != "access" and v.get("refused")), None)
    for part, noun, bcol in PARTS[key]:
        res = d.get(part) or {}
        if res.get("refused"):
            continue
        rows = res.get("rows", [])
        if part == "records":
            rows = [r for r in rows if r.get("ACCESS") == "open"]
        if part == "readm":
            cnt = Counter({(r["BRANCH"], None): int(r["READMISSIONS"]) for r in rows})
        else:
            cnt = Counter((r.get(bcol), r.get("TICKET")) for r in rows)
        for (b, t), n in sorted(cnt.items(), key=lambda x: (x[0][1] is None, str(x[0][0]))):
            why = f"by ticket {e(t)}" if t else "by your standing access"
            where = "at"
            if part == "readm":
                why = "both stays in records on your access list"
            lines.append(f'<li class="{"g-tk" if t else "g-ok"}"><b>{_plural(n, noun)}</b> {where} {e(BR.get(b, b))} <span class="why">{why}</span></li>')
        for r in rows:
            nm = r.get("PATIENT_NAME") or r.get("NAME_AS_RECORDED")
            if nm:
                masked |= str(nm).startswith("Patient ")
                named |= not str(nm).startswith("Patient ")
    locked = sorted({r["BRANCH"] for r in (d.get("records") or {}).get("rows", []) if r.get("ACCESS") == "locked"})
    for b in locked:
        lines.append(f'<li class="g-no"><b>Withheld:</b> her {e(BR.get(b, b))} record <span class="why">not on your access list</span></li>')
    if refused:
        lines.append(f'<li class="g-no"><b>Refused:</b> {e(refused["refused"])} <span class="why">your role has no grant on this view</span></li>')
    if not lines:
        lines.append('<li class="g-ok">Nothing in your access list matches this question.</li>')
    if masked:
        lines.append('<li class="g-mk"><b>Masked:</b> names replaced by pseudonyms; birth dates, mobiles and record IDs left out</li>')
    elif named:
        lines.append('<li class="g-ok"><b>Names shown in full</b> <span class="why">your access is full identity</span></li>')
    tail = "" if (locked or refused) else '<div class="d" style="margin-top:.35rem">Rows outside your access list are simply not returned. Exasol does not even say how many.</div>'
    return f'<div class="c"><div class="t">2 &middot; What Exasol did to this answer</div><ul class="al">{"".join(lines)}</ul>{tail}</div>'


def panel_head(tok):
    return (f'<div class="k">Row-level security, for you</div><div class="h">How Exasol filtered this answer for {e(tok["name"])}</div>'
            f'<div class="s">Everything below comes from the answer itself: this screen filters nothing. Switch person in the bar above and ask again: '
            f'the same question, a different filter.</div>')


# The Exasol rule behind each question: the view it reads and the lines that make the difference (from sql/*.sql).
ACCESS_LIST = """-- HEALTH_GOV.VISIBLE_RECORDS: the access list, for CURRENT_USER, on every query
SELECT r.RECORD_ID, s.PHI_LEVEL
FROM   PATIENT_RECORDS r
JOIN   STANDING_ACCESS s ON s.USER_NAME = CURRENT_USER
       AND (s.BRANCH = '*' OR s.BRANCH = r.BRANCH)    -- by job
UNION ALL
SELECT r.RECORD_ID, 'FULL'
FROM   PATIENT_RECORDS r
JOIN   TICKET_STATE t ON t.REQUESTER = CURRENT_USER
       AND t.STATUS = 'ACTIVE'                         -- by ticket, until it runs out
       AND t.BRANCH = r.BRANCH AND t.UNIFIED_ID = r.UNIFIED_ID"""
RULE = {
    "who": ("HEALTH_GOV.PATIENT_RECORDS", """LEFT JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = r.RECORD_ID
--> ACCESS = 'open' or 'locked', record by record
CASE WHEN p.PHI_RANK = 2 THEN s.PATIENT_NAME
     ELSE 'Patient ' || SUBSTR(HASH_SHA1(p.UNIFIED_ID), 1, 6) END
--> the name, or a pseudonym"""),
    "allergy": ("HEALTH_GOV.ALLERGY_ALERTS", """JOIN HEALTH_GOV.VISIBLE vo ON vo.RECORD_ID = c.PRESCRIBED_UNDER
JOIN HEALTH_GOV.VISIBLE va ON va.RECORD_ID = c.ALLERGY_RECORD_ID
--> the alert needs BOTH rows: the order and the allergy
CASE WHEN p.PHI_RANK = 2 THEN s.PATIENT_NAME
     ELSE 'Patient ' || ... END            --> the name, or a pseudonym"""),
    "scans": ("HEALTH_GOV.IMAGING", """JOIN HEALTH_GOV.VISIBLE v ON v.RECORD_ID = i.RECORD_ID
--> a study (and its S3 key) only for a record you may open;
--  no key, no signed link to the file
GRANT SELECT ON HEALTH_GOV.IMAGING TO HC_CLINICIAN   -- not to analysts"""),
    "similar": ("HEALTH_GOV.SIMILAR_TO_HER", """JOIN HEALTH_GOV.VISIBLE vv ON vv.RECORD_ID = n.RECORD_ID
--> only notes from records you may open are compared
CASE WHEN p.PHI_RANK = 2 THEN s.PATIENT_NAME
     ELSE 'Patient ' || ... END            --> the name, or a pseudonym"""),
    "readmit": ("HEALTH_GOV.READMISSIONS", """JOIN HEALTH_GOV.VISIBLE v1 ON v1.RECORD_ID = e1.RECORD_ID   -- the readmission
JOIN HEALTH_GOV.VISIBLE v2 ON v2.RECORD_ID = e2.RECORD_ID   -- the stay before
--> counted only when you may open BOTH stays"""),
    "risk": ("HEALTH_GOV.ALLERGY_ALERTS", """JOIN HEALTH_GOV.VISIBLE vo ON vo.RECORD_ID = c.PRESCRIBED_UNDER
JOIN HEALTH_GOV.VISIBLE va ON va.RECORD_ID = c.ALLERGY_RECORD_ID
CASE WHEN p.PHI_RANK = 2 THEN s.PATIENT_NAME
     ELSE 'Patient ' || ... END            --> the name, or a pseudonym"""),
}
BETTER = """<div class="better"><div class="k2">Why this is the better way</div><ol>
<li><b>One rule, in the database.</b> Written once, in the governed view. This screen, a BI tool and an AI agent get exactly the same rows; no tool can forget to apply it.</li>
<li><b>Nobody gets the table.</b> The base tables are never granted, so there is nothing to go round. Try it: Exasol refuses.</li>
<li><b>Access follows the job, and the ticket.</b> Another branch opens for one patient, for a set time, and closes by itself.</li>
<li><b>It protects data where it lives.</b> The branch systems and the scans on S3 are read in place: no copy to secure separately.</li>
<li><b>Every answer is on record</b>, with the person and the ticket in force.</li></ol></div>"""


def rule_head(key):
    view, _ = RULE[key]
    return (f'<div class="t">3 &middot; The rule that did it</div><div class="d">This question reads <code>{e(view)}</code>. '
            f'The same lines decide for every person who asks:</div>')


TAGS = ('<span class="tag row">which rows: the join to VISIBLE</span><span class="tag col">what is in them: the CASE</span>'
        '<span class="tag time">for how long: the ticket</span><span class="tag grant">the table: never granted</span>')


# ---------------------------------------------------------------- the business version: one sentence, three tiles
SIMPLE_CSS = """
.whybox { margin-top:1rem; border-radius:20px; border:2px solid #1FA08B; background:#F2FBF8; padding:.9rem 1.1rem; }
.whybox .k { font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#12796A; }
.whybox .say { font-size:1.12rem; color:var(--ink2); line-height:1.5; margin:.2rem 0 .7rem; } .whybox .say b { font-weight:900; }
.lanes { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem; }
.lane { border-radius:16px; background:#fff; border:1px solid var(--edge); padding:.65rem .8rem; display:grid; grid-template-columns:2.4rem minmax(0,1fr); gap:.6rem; align-items:center; }
.lane .ic { width:2.4rem; height:2.4rem; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:1.2rem; font-weight:900; }
.lane.job .ic { background:#E2F4FF; color:#0076AD; } .lane.tkt .ic { background:#E3F5F1; color:#12796A; }
.lane.hid .ic { background:#FFF4E5; color:#C56A00; } .lane.msk .ic { background:#EEF0FF; color:#3B3FB8; } .lane.no .ic { background:#FDE7EA; color:#C8102E; }
.lane .n { font-size:1.35rem; font-weight:900; color:var(--ink2); line-height:1.1; } .lane .t { font-size:.86rem; color:var(--ink2); font-weight:700; }
.lane .s { font-size:.78rem; color:var(--muted); } .lane.off { opacity:.45; }
.whybox .bottom { margin-top:.7rem; font-size:.9rem; color:#0E5E52; font-weight:700; }
@media (max-width:1100px) { .lanes { grid-template-columns:1fr; } }
"""
NOUN = {"who": "record", "allergy": "allergy", "scans": "scan", "similar": "patient like her", "readmit": "readmission", "risk": "alert"}
OWNER = {"CHN": "Anita Rao"}  # the data owner who approves tickets for that branch


def _n(n, noun):
    if n == 1:
        return f"1 {noun}"
    return f"{n} " + ("patients like her" if noun == "patient like her" else ("allergies" if noun == "allergy" else noun + "s"))


def simple(key, tok, d):
    """Why the signed-in person sees what they see, in plain words. Built from the answer itself."""
    noun = NOUN[key]
    refused = next((v for k, v in d.items() if isinstance(v, dict) and k != "access" and v.get("refused")), None)
    acc = (d.get("access") or {})
    if acc.get("refused") or (refused and key not in ("who", "scans")):
        return (f'<div class="whybox"><div class="k">Why you see this</div><div class="say">Your job, <b>{e(tok["job"])}</b>, includes no patient data, '
                f'so Exasol shows you <b>nothing</b> here. Not one name, not one number.</div>'
                f'<div class="lanes"><div class="lane no"><div class="ic">&#10005;</div><div><div class="t">Refused by the database</div>'
                f'<div class="s">The app did not hide it: Exasol never sent it</div></div></div></div>'
                f'<div class="bottom">The database decides this, not the app: the same way for every screen, report and AI assistant.</div></div>')
    tickets = {a["TICKET"]: a for a in acc.get("rows", []) if a.get("TICKET")}
    job_branches = [BR.get(a["BRANCH"], a["BRANCH"]) for a in acc.get("rows", []) if a["BASIS"] == "Standing"]
    by_job, by_ticket, masked, sample = 0, {}, False, None
    for part, _noun, bcol in PARTS[key]:
        if part == "alerts" and key == "allergy":
            continue  # count the allergies she sees; the alert is the answer above
        res = d.get(part) or {}
        for r in res.get("rows", []):
            if part == "records" and r.get("ACCESS") != "open":
                continue
            n = int(r["READMISSIONS"]) if part == "readm" else 1
            if r.get("TICKET"):
                by_ticket[r["TICKET"]] = by_ticket.get(r["TICKET"], 0) + n
            else:
                by_job += n
            nm = r.get("PATIENT_NAME")
            if nm and str(nm).startswith("Patient "):
                masked, sample = True, sample or nm
    locked = sorted({BR.get(r["BRANCH"]) for r in (d.get("records") or {}).get("rows", []) if r.get("ACCESS") == "locked"})
    total = by_job + sum(by_ticket.values())
    parts = []
    if by_job:
        parts.append(f'<b>{by_job}</b> because of your job ({e(", ".join(job_branches))})')
    for t, n in by_ticket.items():
        a = tickets.get(t, {})
        parts.append(f'<b>{n}</b> because {e(OWNER.get(a.get("BRANCH"), "the data owner"))} approved ticket {e(t)} ({_left(a.get("SECONDS_LEFT"))})')
    if len(parts) == 1:
        say = f'You see <b>{_n(total, noun)}</b>, ' + parts[0].split("</b> ", 1)[1] + "."
    else:
        say = f'You see <b>{_n(total, noun)}</b>' + (": " + ", ".join(parts) if parts else "") + "."
    if locked:
        say += f' Her <b>{e(", ".join(locked))}</b> record stays <b>locked</b> until a ticket opens it.'
    else:
        say += " Everything else stays hidden."
    if masked:
        say += f' Names are hidden from you: patients appear as <i>{e(sample)}</i>.'
    job_lane = (f'<div class="lane job{"" if by_job else " off"}"><div class="ic">&#10003;</div><div><div class="n">{by_job}</div>'
                f'<div class="t">Because of your job</div><div class="s">{e(", ".join(job_branches) or "none")}, every day</div></div></div>')
    if by_ticket:
        t, n = next(iter(by_ticket.items()))
        a = tickets.get(t, {})
        tk_lane = (f'<div class="lane tkt"><div class="ic">&#10003;</div><div><div class="n">{n}</div><div class="t">Because of a ticket</div>'
                   f'<div class="s">{e(t)}, approved by {e(OWNER.get(a.get("BRANCH"), "the data owner"))} &middot; {_left(a.get("SECONDS_LEFT"))}</div></div></div>')
    elif masked:
        tk_lane = (f'<div class="lane msk"><div class="ic">&#9673;</div><div><div class="t">Names hidden</div>'
                   f'<div class="s">You see <i>{e(sample)}</i>, never the real name, birth date or phone</div></div></div>')
    else:
        tk_lane = ('<div class="lane tkt off"><div class="ic">&#10003;</div><div><div class="n">0</div><div class="t">Because of a ticket</div>'
                   '<div class="s">No ticket yet: ask the data owner</div></div></div>')
    hid = (f'<div class="lane hid"><div class="ic"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#C56A00" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></div><div><div class="t">{"Her " + e(", ".join(locked)) + " record: locked" if locked else "Everything else: hidden"}</div>'
           f'<div class="s">{"Opens only with an approved ticket" if locked else "Not shown, not even counted"}</div></div></div>')
    return (f'<div class="whybox"><div class="k">Why you see this</div><div class="say">{say}</div>'
            f'<div class="lanes">{job_lane}{tk_lane}{hid}</div>'
            f'<div class="bottom">The database decides this, not the app: the same way for every screen, report and AI assistant, and it ends by itself when the ticket does.</div></div>')


def simple_free(tok, d):
    """'Why you see this' for a typed question: from the person's access list and the rows that came back."""
    acc = d.get("access") or {}
    r = d.get("result") or {}
    if d.get("cannot") or r.get("refused") or acc.get("refused"):
        if acc.get("refused") or (r.get("refused") and "privilege" in r.get("refused", "")):
            return simple("allergy", tok, {"access": {"refused": "x"}, "x": {"refused": "x"}})
        return ""
    rows = r.get("rows", [])
    job = [BR.get(a["BRANCH"], a["BRANCH"]) for a in acc.get("rows", []) if a["BASIS"] == "Standing"]
    tks = [a for a in acc.get("rows", []) if a.get("TICKET")]
    by_ticket = sum(1 for x in rows if x.get("TICKET"))
    hidden = any((c in x and (x[c] is None or str(x[c]).startswith("Patient "))) for x in rows
                 for c in ("PATIENT_NAME", "NAME_AS_RECORDED", "MOBILE"))
    say = f'You see <b>{len(rows)} row{"s" if len(rows) != 1 else ""}</b>, all from what your job allows ({e(", ".join(job))})'
    if tks:
        say += f' plus ticket {e(tks[0]["TICKET"])} ({_left(tks[0]["SECONDS_LEFT"])})'
    say += ". Everything else stays hidden, however the question is asked."
    if hidden:
        say += " Names and phone numbers are hidden from you."
    lane2 = ((f'<div class="lane tkt"><div class="ic">&#10003;</div><div><div class="n">{by_ticket}</div><div class="t">Because of a ticket</div>'
              f'<div class="s">{e(tks[0]["TICKET"])} &middot; {_left(tks[0]["SECONDS_LEFT"])}</div></div></div>') if tks else
             ('<div class="lane msk"><div class="ic">&#9673;</div><div><div class="t">Names hidden</div><div class="s">by your job</div></div></div>') if hidden else
             ('<div class="lane tkt off"><div class="ic">&#10003;</div><div><div class="n">0</div><div class="t">Because of a ticket</div><div class="s">No ticket</div></div></div>'))
    lock = ('<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#C56A00" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>')
    return (f'<div class="whybox"><div class="k">Why you see this</div><div class="say">{say}</div><div class="lanes">'
            f'<div class="lane job"><div class="ic">&#10003;</div><div><div class="n">{len(rows) - by_ticket}</div><div class="t">Because of your job</div>'
            f'<div class="s">{e(", ".join(job))}</div></div></div>{lane2}'
            f'<div class="lane hid"><div class="ic">{lock}</div><div><div class="t">Everything else: hidden</div><div class="s">Even an AI-written query cannot reach it</div></div></div></div>'
            f'<div class="bottom">The AI only writes the question. The database decides the answer, by who is asking.</div></div>')
