"""Tab 'Ask questions': the six questions of the health demo, each answered as the SIGNED-IN person. The same question
gives each role a different answer, and each answer says what this login cannot see."""
from views import BR, br, dmy, e, refused, tk

QS = [("who", "Who is Meenakshi Sundaram?"), ("allergy", "Is the prescription drafted now safe for her?"),
      ("scans", "What did her earlier scans show?"), ("similar", "What worked for patients like her?"),
      ("readmit", "How many patients came back to a different branch?"), ("risk", "Who else is at risk right now?")]
SRC = {"who": "HEALTH_GOV.PATIENT_IDENTITY + PATIENT_RECORDS + ENCOUNTERS + IMAGING", "allergy": "HEALTH_GOV.ALLERGY_ALERTS + ALLERGIES",
       "scans": "HEALTH_GOV.IMAGING (the PACS header index on S3)", "similar": "HEALTH_GOV.SIMILAR_TO_HER (note vectors, a join + GROUP BY)",
       "readmit": "HEALTH_GOV.READMISSIONS (the certified 30-day definition)", "risk": "HEALTH_GOV.ALLERGY_ALERTS, every patient"}

CSS = """
.qgrid { display:grid; grid-template-columns:minmax(0,22rem) minmax(0,1fr); gap:1.2rem; align-items:start; }
.qlist { display:grid; gap:.45rem; } .qlist .btn { min-height:2.8rem; }
.asas { border-radius:12px; background:#F1F4F9; padding:.45rem .7rem; font-size:.84rem; color:var(--ink2); margin-bottom:.5rem; }
.asas b { font-weight:800; } .asas code { font-size:.76rem; }
.big3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem; margin:.5rem 0 .7rem; }
.b3 { border-radius:14px; background:#F6F9FC; padding:.6rem .8rem; } .b3.hl { background:#E3F5F1; } .b3.bad { background:#FFF5F6; }
.b3 .v { font-size:1.6rem; font-weight:900; color:var(--ink2); line-height:1.1; } .b3.bad .v { color:#C8102E; } .b3.hl .v { color:#12796A; }
.b3 .k { font-size:.8rem; color:var(--muted); margin-top:.15rem; }
.cant { border-radius:12px; border:1px dashed #E3B068; background:#FFFBF2; padding:.5rem .75rem; font-size:.86rem; color:#6B3E00; margin-top:.6rem; }
.cant b { font-weight:900; }
.idr { display:grid; grid-template-columns:6rem minmax(0,1fr); gap:.6rem; padding:.4rem 0; border-bottom:1px solid #EEF2F7; font-size:.88rem; }
.idr:last-child { border-bottom:0; } .idr code { font-size:.8rem; }
.bars { display:grid; gap:.45rem; margin:.4rem 0; }
.bar { display:grid; grid-template-columns:6rem minmax(0,1fr) 7rem; gap:.6rem; align-items:center; font-size:.86rem; }
.bar .t { height:24px; border-radius:7px; background:#F1F4F9; display:flex; overflow:hidden; }
.bar .t .a { background:#1FA08B; } .bar .t .x { background:repeating-linear-gradient(45deg,#C8102E 0 6px,#E0505F 6px 12px); }
.bar .n { text-align:right; font-weight:800; font-variant-numeric:tabular-nums; }
@media (max-width:1100px) { .qgrid { grid-template-columns:1fr; } .big3 { grid-template-columns:1fr; } }
"""


def _tiles(*t):
    return '<div class="big3">' + "".join(f'<div class="b3 {c}"><div class="v">{v}</div><div class="k">{k}</div></div>' for v, k, c in t) + "</div>"


def _locked(d):
    rec = d.get("records") or {}
    return sorted({r["BRANCH"] for r in rec.get("rows", []) if r["ACCESS"] == "locked"})


def _cant(text):
    return f'<div class="cant"><b>What this login cannot see.</b> {text}</div>'


def _refused_any(d):
    return next((v for k, v in d.items() if isinstance(v, dict) and v.get("refused") and k != "access"), None)


def render(key, tok, d):
    q = dict(QS)[key]
    head = (f'<div class="blk"><div class="t">{e(q)}</div><div class="s" style="font-size:.82rem;color:var(--muted);margin:.15rem 0 .5rem">'
            f'{e(SRC[key])}</div><div class="asas">Answered as <b>{e(tok["name"])}</b> &middot; <code>{e(tok["user"])}</code> &middot; '
            f'{e(", ".join(tok.get("roles", [])))}: every number below is what this login may see right now.</div>')
    bad = _refused_any(d)
    if bad and key not in ("who", "scans"):
        return head + refused(bad) + _cant("This role may not read patient data at all; Exasol refused the statement.") + "</div>"
    body = globals()["_" + key](d)
    return head + body + f'<div class="meta">{d.get("secs", 0):.1f} s in all, every statement run as <code>{e(tok["user"])}</code></div></div>'


def _who(d):
    if d["identity"].get("refused"):
        return refused(d["identity"]) + _cant("This role may not open patient identities.")
    ids, enc = d["identity"]["rows"], d["encounters"].get("rows", [])
    img = d["imaging"]
    rows = "".join(f'<div class="idr">{br(r["BRANCH"])}<div><code>{e(r["RECORD_ID"] or "(identity masked)")}</code> {tk(r["TICKET"])}<br/>'
                   f'{e(r["NAME_AS_RECORDED"] or "")} &middot; born {e(r["BIRTH_DATE_AS_RECORDED"] or r["BIRTH_YEAR"])} &middot; mobile {e(r["MOBILE"] or "hidden")}</div></div>'
                   for r in ids)
    lk = _locked(d)
    nimg = "&mdash;" if img.get("refused") else len(img["rows"])
    out = _tiles((f'{len(ids)} of {len(ids) + len(lk)}', "of her records you may open", "hl"), (len(enc), "visits you may see", ""),
                 (nimg, "scans you may see", "")) + rows
    if lk:
        out += _cant(f'Her {e(", ".join(BR[b] for b in lk))} record: the patient index knows it exists, but its name, IDs, visits and scans stay closed until a ticket opens them.')
    if img.get("refused"):
        out += _cant("Scans: this role may not open imaging at all.")
    return out


def _allergy(d):
    a, al = d["alerts"]["rows"], d["allergies"]["rows"]
    lk = _locked(d)
    if a:
        x = a[0]
        out = _tiles(("Stop", f'{e(x["DRUG"])} is a {e(str(x["DRUG_CLASS"]).lower())}', "bad"), (len(al), "allergies you may see", ""),
                     (e(BR.get(x["ALLERGY_BRANCH"])), "where the allergy was recorded", ""))
        out += (f'<div class="alert"><div class="h">{e(x["ALLERGY_AS_RECORDED"])} ({e(x["SEVERITY"])})</div><div class="d">Recorded at '
                f'{e(BR.get(x["ALLERGY_BRANCH"]))}; today\'s order was drafted at {e(BR.get(x["ORDER_BRANCH"]))}, whose system holds no allergy for her. '
                f'{"Opened by ticket " + tk(x["TICKET"]) if x["TICKET"] else ""}</div></div>')
        return out
    out = _tiles(("No alert", "in the records you may open", "hl" if not lk else ""), (len(al), "allergies you may see", ""),
                 (len(lk), "of her records locked", "bad" if lk else ""))
    if lk:
        out += _cant(f'Any allergy recorded at {e(", ".join(BR[b] for b in lk))}. "No alert" here means "none in what you may open", not "safe". '
                     'Ask the data owner for a ticket.')
    return out


def _scans(d):
    img = d["imaging"]
    if img.get("refused"):
        return refused(img) + _cant("This role may not open imaging. No study is returned, so no link to a file can be made.")
    cards = "".join(f'<div class="scan"><img src="{e(r["THUMB_URL"])}" alt="{e(r["STUDY_DESCRIPTION"])}"/><div class="c">'
                    f'<b>{dmy(r["STUDY_DATE"])} &middot; {e(r["STUDY_DESCRIPTION"])}</b>{br(r["BRANCH"])} {e(r["MODALITY"])} {tk(r["TICKET"])}'
                    f'<div style="margin-top:.3rem"><a href="{e(r["DICOM_URL"])}" target="_blank" rel="noopener">Original DICOM &rarr;</a> '
                    f'<span class="meta" style="display:inline">{("by ticket " + e(r["TICKET"]) + " · closes in " + str(max(1, r["LINK_SECS"] // 60)) + " min") if r["TICKET"] else "your branch · always available"}</span></div></div></div>' for r in img["rows"])
    lk = _locked(d)
    out = _tiles((len(img["rows"]), "studies you may open", "hl"), (sum(int(r["FILE_BYTES"] or 0) for r in img["rows"]) // 100_000 / 10, "MB of DICOM on S3", ""),
                 (0, "pixels through the database", "")) + f'<div class="scans">{cards}</div>'
    if lk:
        out += _cant(f'Her scans held at {e(", ".join(BR[b] for b in lk))}. The governed view does not return them, so the service never learns the file '
                     'names and cannot make a link.')
    return out


def _similar(d):
    rows = d["similar"]["rows"]
    masked = any(str(r["PATIENT_NAME"]).startswith("Patient ") for r in rows)
    body = "".join(f'<tr><td><b>{e(r["PATIENT_NAME"])}</b>, {int(float(r["AGE"]))}</td><td>{br(r["BRANCH"])}</td><td>{e(r["DIAGNOSIS"])}</td>'
                   f'<td>{e(r["ANTIBIOTIC"] or "none recorded")}</td><td>{"came back" if r["READMITTED_30D"] in (True, "true") else "did not come back"}</td>'
                   f'<td style="text-align:right">{float(r["SIMILARITY"]):.2f}</td></tr>' for r in rows)
    back = sum(1 for r in rows if r["READMITTED_30D"] in (True, "true"))
    out = _tiles((len(rows), "patients like her you may see", "hl"), (back, "came back within 30 days", "bad" if back else ""),
                 ("masked" if masked else "named", "identities, for this role", ""))
    out += ('<div class="tblw"><table class="tbl"><tr><th>Patient</th><th>Branch</th><th>Diagnosis</th><th>Antibiotic</th><th>30 days</th>'
            f'<th style="text-align:right">Similarity</th></tr>{body}</table></div>')
    out += _cant("Patients whose notes and records sit at a branch this login may not open. Diabetic, 60+, penicillin-allergic, close in meaning "
                 "to her admission note; the analyst sees every branch with pseudonyms, the doctor her own branch with names.")
    return out


def _readmit(d):
    rows = d["readm"]["rows"]
    tot, cross = sum(int(r["READMISSIONS"]) for r in rows), sum(int(r["CROSS_BRANCH"]) for r in rows)
    mx = max([int(r["READMISSIONS"]) for r in rows] or [1])
    bars = "".join(f'<div class="bar">{br(r["BRANCH"])}<div class="t"><div class="a" style="width:{100 * (int(r["READMISSIONS"]) - int(r["CROSS_BRANCH"])) / mx:.1f}%"></div>'
                   f'<div class="x" style="width:{100 * int(r["CROSS_BRANCH"]) / mx:.1f}%"></div></div><span class="n">{int(r["READMISSIONS"])} &middot; {int(r["CROSS_BRANCH"])} cross</span></div>'
                   for r in rows)
    out = _tiles((tot, "readmissions within 30 days you may count", "hl"), (cross, "came back to a different branch", "bad" if cross else ""),
                 (f'{100 * cross / max(tot, 1):.0f}%', "of them cross a branch", ""))
    out += f'<div class="bars">{bars}</div>'
    if not cross:
        out += _cant("Readmissions where the earlier stay was at another branch: counting one needs the records of both stays. "
                     "The analyst, who may see every branch (masked), counts 148 of 462.")
    return out


def _risk(d):
    rows = d["alerts"]["rows"]
    body = "".join(f'<div class="alert" style="margin:.35rem 0"><div class="h">{e(r["PATIENT_NAME"])}: {e(r["DRUG"])} ({e(r["ORDER_STATUS"])}) at '
                   f'{e(BR.get(r["ORDER_BRANCH"]))}</div><div class="d">{e(r["ALLERGY_AS_RECORDED"])} ({e(r["SEVERITY"])}), recorded at '
                   f'{e(BR.get(r["ALLERGY_BRANCH"]))}. {tk(r["TICKET"])}</div></div>' for r in rows)
    out = _tiles((len(rows), "current orders clashing with an allergy", "bad" if rows else "hl"),
                 (sum(1 for r in rows if r["ORDER_BRANCH"] != r["ALLERGY_BRANCH"]), "where the allergy is at another branch", ""),
                 ("masked" if any(str(r["PATIENT_NAME"]).startswith("Patient ") for r in rows) else "named", "identities, for this role", ""))
    return out + body + _cant("A clash is shown only when this login may open BOTH the order and the allergy record. "
                              "The analyst sees all 3 across the group, masked; the doctor sees the ones in her reach.")


# ---------------------------------------------------------------- ask your own question
EXAMPLES = ["Which of my patients are in a bed right now?", "List all patients with their names and phone numbers",
            "What allergies does Meenakshi have?", "How many readmissions per branch came back to a different branch?"]
FREE_CSS = """
.ask2 { border-radius:20px; border:2px solid #1FA08B; background:#fff; padding:.9rem 1.1rem 1rem; margin:.4rem 0 1rem; box-shadow:var(--shadow); }
.ask2 .k, .k6 { font-size:.7rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#12796A; }
.askrow { display:grid; grid-template-columns:minmax(0,1fr) 8rem; gap:.7rem; margin-top:.45rem; align-items:stretch; }
.askrow textarea { font-size:1.15rem !important; min-height:3.4rem; padding:.7rem .9rem !important; resize:vertical; width:100%; box-sizing:border-box; }
.askrow .btn { font-size:1.1rem; text-align:center; font-weight:800; }
.ex2 { display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; margin-top:.6rem; } .ex2 .lbl { font-size:.85rem; color:var(--muted); font-weight:700; }
.ex2 button { font-family:inherit; font-size:.9rem; border-radius:999px; border:1px solid #CDEBE4; background:#F2FBF8; color:#0E5E52; padding:.4rem .85rem; cursor:pointer; }
.ex2 button:hover { background:#E3F5F1; }
.ask2 .hint { font-size:.8rem; color:var(--faint); margin-top:.5rem; }
.k6 { margin:.2rem 0 .45rem; }
.qcards { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem; margin-bottom:1rem; }
.qcards .btn { display:flex; align-items:center; gap:.75rem; min-height:4.2rem; font-size:1.02rem; padding:.7rem .95rem; border-radius:16px; }
.qcards .qn { flex:0 0 2rem; height:2rem; border-radius:50%; background:rgba(255,255,255,.16); display:flex; align-items:center; justify-content:center; font-weight:900; }
.qcards .qt { font-weight:700; line-height:1.3; }
@media (max-width:1100px) { .qcards { grid-template-columns:1fr 1fr; } .askrow { grid-template-columns:1fr; } }
@media (max-width:700px) { .qcards { grid-template-columns:1fr; } }
.own { margin-top:1rem; border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.7rem .8rem; }
.own .k { font-size:.64rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#12796A; }
.own textarea { width:100%; box-sizing:border-box; min-height:3.4rem; margin:.35rem 0; resize:vertical; }
.own .ex { display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.4rem; }
.own .ex button { font-size:.74rem; border-radius:999px; border:1px solid var(--edge); background:#F6F9FC; color:var(--ink2); padding:.25rem .6rem; cursor:pointer; text-align:left; }
.own .hint { font-size:.74rem; color:var(--faint); margin-top:.3rem; }
.say2 { font-size:1.1rem; line-height:1.5; color:var(--ink2); margin:.4rem 0 .6rem; border-radius:14px; background:#F6F9FC; padding:.7rem .9rem; }
.tbl td.hid { color:#5B5FE0; font-style:italic; }
"""
LABEL = {"UNIFIED_ID": "Patient ID", "PATIENT_NAME": "Patient", "NAME_AS_RECORDED": "Name", "MOBILE": "Phone", "BRANCH": "Branch",
         "BIRTH_DATE_AS_RECORDED": "Born", "RECORD_ID": "Record", "TICKET": "Ticket"}
HIDDEN_COLS = {"PATIENT_NAME", "NAME_AS_RECORDED", "MOBILE", "BIRTH_DATE_AS_RECORDED", "RECORD_ID"}


def _cell(col, v):
    if col in HIDDEN_COLS and (v is None or str(v).startswith("Patient ")):
        return f'<td class="hid">{e(v) if v else "hidden"}</td>'
    if col.endswith("BRANCH") and v in BR:
        return f"<td>{e(BR[v])}</td>"
    return f"<td>{e(v)}</td>"


def free_render(tok, d):
    head = (f'<div class="blk"><div class="t">{e(d.get("question"))}</div><div class="asas" style="margin-top:.4rem">Answered as <b>{e(tok["name"])}</b> '
            f'&middot; <code>{e(tok["user"])}</code> &middot; {e(", ".join(tok.get("roles", [])))}. Claude wrote the query from the views this login may read; '
            f'Exasol ran it as this login.</div>')
    if d.get("cannot"):
        return head + f'<div class="cant"><b>No query was run.</b> {e(d["cannot"])}</div></div>'
    r = d.get("result") or {}
    if r.get("refused"):
        return head + refused(r) + _cant("Exasol refused the query for this login. The AI could not get round it either.") + "</div>"
    rows = r.get("rows", [])
    body = f'<div class="say2">{e(d.get("answer") or "")}</div>'
    if rows:
        cols = list(rows[0].keys())
        th = "".join(f"<th>{e(LABEL.get(c, c.replace('_', ' ').title()))}</th>" for c in cols)
        tr = "".join("<tr>" + "".join(_cell(c, x[c]) for c in cols) + "</tr>" for x in rows[:12])
        more = f'<div class="meta">{len(rows)} rows; the first 12 shown.</div>' if len(rows) > 12 else ""
        body += f'<div class="tblw"><table class="tbl"><tr>{th}</tr>{tr}</table></div>{more}'
    return head + body + f'<div class="meta">{d.get("secs", 0):.1f} s in all: Claude wrote the query, Exasol ran it as <code>{e(tok["user"])}</code>, Claude summarised.</div></div>'
