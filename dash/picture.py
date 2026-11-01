"""Static pages: how access on request works (one picture), who may do what (the roles), and the security card."""

CSS = """
.hw-h { font-size:1.9rem; font-weight:900; letter-spacing:-.03em; color:var(--ink2); margin:.3rem 0 .1rem; line-height:1.15; }
.hw-h em { font-style:normal; color:#12796A; }
.hw-pic { margin-top:.6rem; border-radius:24px; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); padding:.6rem .8rem; overflow:hidden; }
.hw-pic svg { display:block; width:100%; min-width:0; height:auto; }  /* always the whole picture: it scales, it never scrolls the ticket out of view */
.hw-pic text { font-family:inherit; }
.sec.sec3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
@media (max-width:1100px) { .sec.sec3 { grid-template-columns:1fr; } }
"""

I_USER = '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>'
I_BOT = '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13v1M15 13v1M9 17h6"/><circle cx="12" cy="3" r="1"/>'
I_DB = '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'
I_DOCS = '<path d="M8 3h8l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>'
I_LOCK = '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>'
I_OPEN = '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/>'
I_TICKET = '<path d="M3 8a2 2 0 0 0 0 4v4h18v-4a2 2 0 0 1 0-4V4H3z"/><path d="M13 4v12" stroke-dasharray="2 2"/>'
I_OK = '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>'
I_CLOCK = '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
I_LOG = '<path d="M6 3h12v18H6z"/><path d="M9 8h6M9 12h6M9 16h4"/>'
I_SHIELD = '<path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/><path d="M9 12l2 2 4-4"/>'
I_KEY = '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M14 9l2 2"/>'
I_SERVER = '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>'
I_COPY = '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V5a1 1 0 0 1 1-1h11"/><path d="M3 3l18 18"/>'
I_MASK = '<path d="M3 12s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z"/><path d="M3 3l18 18"/>'
I_WARN = '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>'


def _i(path, x, y, s=2.0, color="#0B1B34", sw=1.7):
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</g>')


def _num(n, x, y):
    return (f'<circle cx="{x}" cy="{y}" r="15" fill="#0B1B34"/>'
            f'<text x="{x}" y="{y + 5}" text-anchor="middle" font-size="15" font-weight="900" fill="#fff">{n}</text>')


def _t(x, y, txt, size=13, weight=600, color="#0B1B34", anchor="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}">{txt}</text>'


def svg_icon(path, color="#12796A"):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')


def picture():
    out = ['<svg viewBox="0 0 1240 470" role="img" aria-label="How access on request works">',
           '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">'
           '<path d="M0 0 L10 5 L0 10 z" fill="#9FB0C4"/></marker></defs>']
    # 1 a person (or their agent) signs in with their own login
    for y, c, ic, t in [(176, "#0E2A47", I_USER, "Doctor"), (240, "#5B5FE0", I_BOT, "her AI agent")]:
        out.append(f'<rect x="40" y="{y}" width="130" height="50" rx="14" fill="#fff" stroke="{c}" stroke-width="2.5"/>'
                   + _i(ic, 50, y + 12, 1.1, c, 2) + _t(82, y + 31, t, 14, 800, c, "start"))
    out.append(_num(1, 45, 170) + _t(105, 330, "Signs in", 17, 800) + _t(105, 350, "her own Exasol login", 13, 500, "#5B6B80"))
    # 2 Exasol: password, role, access list, governed views
    out.append('<line x1="180" y1="230" x2="318" y2="230" stroke="#9FB0C4" stroke-width="3" marker-end="url(#ah)"/>')
    out.append('<rect x="325" y="120" width="330" height="232" rx="28" fill="#0B3B4A"/><rect x="325" y="120" width="330" height="232" rx="28" fill="#12796A" opacity=".55"/>')
    out.append(_t(490, 156, "Exasol", 26, 900, "#fff"))
    for k, (t, d) in enumerate([("Password", "checked by Exasol"), ("Role", "one per job"), ("Access list", "branch + tickets"),
                                ("Governed views", "rows, identity")]):
        y = 170 + k * 44
        out.append(f'<rect x="345" y="{y}" width="290" height="36" rx="12" fill="rgba(255,255,255,.14)"/>'
                   f'<circle cx="364" cy="{y + 18}" r="10" fill="#fff"/><text x="364" y="{y + 22}" text-anchor="middle" font-size="11" font-weight="900" fill="#0B3B4A">{chr(97 + k)}</text>'
                   + _t(384, y + 23, t, 14, 800, "#fff", "start") + _t(625, y + 23, d, 11.5, 500, "#fff", "end"))
    out.append(_num(2, 340, 122))
    # her two records: her own branch open, the other branch locked
    for x, c, ic, lk, t, s in [(380, "#0076AD", I_DOCS, I_OPEN, "Branch B record", "her own branch"),
                               (600, "#C56A00", I_DB, I_LOCK, "Branch A record", "another branch")]:
        out.append(f'<rect x="{x - 95}" y="18" width="190" height="62" rx="16" fill="{c}"/>' + _i(ic, x - 84, 30, 1.0, "#fff", 2.2)
                   + _t(x - 54, 44, t, 13, 800, "#fff", "start") + _t(x - 54, 62, s, 10.5, 500, "#fff", "start"))
        out.append(_i(lk, x + 60, 30, 0.95, "#fff", 2.2))
        out.append(f'<line x1="{x}" y1="82" x2="{490 + (x - 490) * .4}" y2="118" stroke="{c}" stroke-width="3" stroke-dasharray="6 6"/>')
    # 3 the answer: locked without a ticket
    out.append('<path d="M660 236 C700 236 700 176 740 176" fill="none" stroke="#D98A00" stroke-width="3" marker-end="url(#ah)"/>')
    out.append('<rect x="748" y="140" width="210" height="72" rx="16" fill="#FFFBF2" stroke="#D98A00" stroke-width="2"/>'
               + _i(I_LOCK, 760, 158, 1.3, "#C56A00", 2) + _t(800, 170, "Locked", 16, 800, "#9A4A00", "start")
               + _t(800, 190, "no ticket: her Branch A visits,", 11.5, 500, "#6B3E00", "start") + _t(800, 205, "notes and scans stay closed", 11.5, 500, "#6B3E00", "start"))
    out.append(_num(3, 748, 140))
    # 4 the service desk: ticket, data owner approves for a limited time
    out.append('<path d="M958 176 C1000 176 1010 176 1040 176" fill="none" stroke="#9FB0C4" stroke-width="3" marker-end="url(#ah)"/>')
    out.append('<rect x="1048" y="120" width="170" height="120" rx="16" fill="#fff" stroke="#0B1B34" stroke-width="2"/>'
               + _i(I_TICKET, 1062, 132, 1.2, "#0B1B34", 2) + _t(1096, 150, "Ticket", 15, 800, "#0B1B34", "start")
               + _t(1062, 178, "REQ0012345", 12, 700, "#0076AD", "start") + _t(1062, 198, "data owner of", 11.5, 500, "#5B6B80", "start")
               + _t(1062, 213, "Branch A approves,", 11.5, 500, "#5B6B80", "start") + _t(1062, 228, "for 15 minutes", 11.5, 700, "#12796A", "start"))
    out.append(_num(4, 1048, 120))
    # 5 open, until it runs out
    out.append('<path d="M1133 242 C1133 290 1060 300 960 300" fill="none" stroke="#1FA08B" stroke-width="3" marker-end="url(#ah)"/>')
    out.append('<rect x="748" y="262" width="210" height="72" rx="16" fill="#F2FBF8" stroke="#1FA08B" stroke-width="2"/>'
               + _i(I_OPEN, 760, 280, 1.3, "#12796A", 2) + _t(800, 292, "Open, with the ticket", 15, 800, "#12796A", "start")
               + _t(800, 312, "full record, scans included;", 11.5, 500, "#0E5E52", "start") + _t(800, 327, "closes itself when time is up", 11.5, 500, "#0E5E52", "start"))
    out.append('<path d="M660 262 C700 262 700 298 740 298" fill="none" stroke="#1FA08B" stroke-width="3" stroke-dasharray="5 5"/>')
    out.append(_num(5, 748, 262))
    # 6 the log
    out.append('<line x1="40" y1="400" x2="1200" y2="400" stroke="#E6EBF2" stroke-width="2"/>')
    out.append(_num(6, 370, 432) + _i(I_LOG, 398, 418, 1.3, "#0B1B34"))
    out.append(_t(438, 437, "Every statement is logged by Exasol", 15, 800, "#0B1B34", "start")
               + _t(720, 437, "who ran it, the ticket in force, and every refusal", 13, 500, "#5B6B80", "start"))
    out.append('</svg>')
    return "".join(out)


ROLES = [  # login, role, can see, can do, refused
    ("Dr. Priya Nair · DR_PRIYA", "HC_CLINICIAN", "Branch B records, full identity; another branch's full record of one patient (visits, notes, medications, scans) while a ticket is active",
     "raise an access request", "raw tables, approving any ticket"),
    ("Anita Rao · OWNER_ANITA", "HC_DATA_OWNER", "the request queue for Branch A: who asks, for whom, why",
     "approve for a set time, reject, revoke", "any patient data"),
    ("Ravi Kumar · ANALYST_RAVI", "HC_ANALYST", "every branch, identities masked by the view", "analyse", "raising requests, any name or birth date"),
    ("Sam Thomas · AUDITOR_SAM", "HC_AUDITOR", "every ticket and every statement, with the ticket in force", "export the trail", "any patient data"),
]


def roles_table():
    rows = "".join(f'<tr><td>{a}</td><td><span class="role">{r}</span></td><td>{s}</td><td class="y">{d}</td><td class="n">{n}</td></tr>'
                   for a, r, s, d, n in ROLES)
    return ('<div class="blk"><div class="k">Who may do what: one Exasol role per job, enforced by Exasol</div><div class="tblw">'
            '<table class="tbl matrix"><tr><th>Login</th><th>Role</th><th>Sees</th><th>Can</th><th>Refused</th></tr>'
            f'{rows}</table></div></div>')


SECURITY = [
    (I_SERVER, "One central Exasol", "Staff reach it from their laptops through this console, a BI tool or an AI agent. No patient data is stored on a laptop."),
    (I_KEY, "Each person has their own login", "Exasol checks the password. The console holds no account of its own and no list of who may see what."),
    (I_SHIELD, "One role per job", "Clinician, analyst, data owner, auditor. Each role can read its views and nothing else; the raw tables are refused."),
    (I_TICKET, "Another branch is a ticket", "Opened by the data owner of that branch, never by the requester, for one patient's whole record and a set time."),
    (I_DOCS, "Scans follow the same rule", "A link to a DICOM file on S3 is made only for a study the governed view returned, and expires with the ticket."),
    (I_CLOCK, "Access ends by itself", "The expiry is checked inside the view on every query. Nobody has to remember to remove it."),
    (I_MASK, "Identity masked by the view", "Analysts get pseudonyms; names, birth dates and mobiles never leave the database for them."),
    (I_COPY, "Nothing copied", "The branch systems are read where they are, read-only. The ticket opens a view, not a copy."),
    (I_LOG, "Every statement on record", "Written by Exasol, including refusals, with the ticket in force. Ready to send to a SIEM."),
    (I_BOT, "Agents get the same rules", "An AI agent signs in as the person it works for and sees exactly what that person may see."),
]
GAPS = [
    (I_WARN, "Whoever runs the database", "Can still change the rules. In production a separate team holds that job, and the record of every check is kept outside the database."),
    (I_WARN, "Tickets live in Exasol here", "In production your service desk (for example ServiceNow) raises and closes them, and tells Exasol."),
    (I_WARN, "Passwords in this demo", "In production staff sign in with their normal company login (single sign-on)."),
]


def security():
    c = "".join(f'<div class="c">{svg_icon(i)}<div><b>{t}</b><span>{d}</span></div></div>' for i, t, d in SECURITY)
    g = "".join(f'<div class="c gap">{svg_icon(i, "#C56A00")}<div><b>{t}</b><span>{d}</span></div></div>' for i, t, d in GAPS)
    return (f'<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">Security</div>'
            f'<div class="hw-h">One governed Exasol. <em>Every person, every agent, every query.</em></div></div>'
            f'<div class="hw-pic">{security_picture()}</div>')


def how_page():
    return (f'<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">How it works</div>'
            f'<div class="hw-h">Another branch\'s records, <em>on an approved ticket.</em></div></div>'
            f'<div class="hw-pic">{picture()}</div>{roles_table()}')


I_IMG = '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/>'
I_STOP = '<path d="M8 2h8l6 6v8l-6 6H8l-6-6V8z"/><path d="M8 12h8"/>'


def security_picture():
    """For a business audience: every request walks one road through four checkpoints inside one central Exasol."""
    out = ['<svg viewBox="0 0 1240 545" role="img" aria-label="Four checks on every request">',
           '<defs><marker id="sa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">'
           '<path d="M0 0 L10 5 L0 10 z" fill="#1FA08B"/></marker>'
           '<marker id="sr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="13" markerHeight="13" markerUnits="userSpaceOnUse" orient="auto">'
           '<path d="M0 0 L10 5 L0 10 z" fill="#C8102E"/></marker></defs>']
    # who asks: one group of people and assistants
    out.append(_t(110, 120, "WHO ASKS", 11, 900, "#5B6B80"))
    out.append('<path d="M184 200 L214 200" stroke="#1FA08B" stroke-width="5" marker-end="url(#sa)"/>')
    for k, (ic, c) in enumerate([(I_USER, "#0E2A47"), (I_USER, "#5B5FE0"), (I_USER, "#C56A00"), (I_USER, "#12796A"), (I_BOT, "#7A4FD6")]):
        cx, cy = (70 + (k % 2) * 80, 160 + (k // 2) * 62) if k < 4 else (110, 284)
        out.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="#fff" stroke="{c}" stroke-width="2.5"/>' + _i(ic, cx - 13, cy - 13, 1.1, c, 2))
    out.append(_t(110, 336, "doctors, analysts, data owners,", 12, 600, "#0B1B34") + _t(110, 352, "auditors and AI assistants", 12, 600, "#0B1B34"))
    out.append(_t(110, 378, "no patient data on any laptop", 11.5, 700, "#12796A"))
    # one central Exasol, one road, four checkpoints
    out.append('<rect x="215" y="22" width="790" height="350" rx="30" fill="#F2FBF8" stroke="#1FA08B" stroke-width="2"/>')
    out.append(_t(610, 58, "One central Exasol: four checks on every request", 19, 900, "#0B3B4A"))
    out.append('<rect x="222" y="168" width="772" height="64" rx="32" fill="#0B3B4A"/>'
               '<line x1="250" y1="200" x2="966" y2="200" stroke="#5EE0C2" stroke-width="2" stroke-dasharray="10 9"/>')
    out.append('<path d="M996 200 L1026 200" stroke="#1FA08B" stroke-width="5" marker-end="url(#sa)"/>')
    checks = [(I_KEY, "Who are you?", ["Your own login.", "Exasol checks it."]),
              (I_SHIELD, "What is your job?", ["Doctor, analyst, owner", "or auditor: one role each."]),
              (I_TICKET, "Do you have a ticket?", ["Another branch only with", "approval, for a set time."]),
              (I_MASK, "What may you see?", ["Only your rows; names", "hidden if your job says so."])]
    for k, (ic, q, a2) in enumerate(checks):
        x = 300 + k * 175
        out.append(_t(x, 120, q, 15.5, 900, "#0B1B34"))
        out.append(f'<circle cx="{x}" cy="200" r="46" fill="#fff" stroke="#1FA08B" stroke-width="4"/>' + _i(ic, x - 18, 182, 1.5, "#0B3B4A", 2))
        out.append(f'<circle cx="{x - 34}" cy="164" r="13" fill="#0B1B34"/>' + _t(x - 34, 169, str(k + 1), 12, 900, "#fff"))
        out.append(_t(x, 278, a2[0], 12.5, 600, "#3B4A5C") + _t(x, 295, a2[1], 12.5, 600, "#3B4A5C"))
    # every check is recorded
    out.append('<rect x="245" y="318" width="730" height="38" rx="19" fill="#fff" stroke="#C9D3E0"/>'
               + _i(I_LOG, 262, 325, 1.0, "#0B1B34") + _t(292, 342, "Every check is recorded, refusals too: who asked, what they saw, and the ticket that allowed it", 12.5, 700, "#0B1B34", "start"))
    # the answer
    out.append('<rect x="1030" y="118" width="192" height="210" rx="20" fill="#fff" stroke="#1FA08B" stroke-width="2.5"/>')
    out.append(_t(1126, 148, "Your answer", 16, 900, "#0B3B4A"))
    for k, (ic, c, t1, t2) in enumerate([(I_OK, "#12796A", "Only the rows", "you may see"), (I_MASK, "#5B5FE0", "Names hidden", "where needed"),
                                          (I_CLOCK, "#C56A00", "Ends by itself", "with the ticket")]):
        y = 172 + k * 50
        out.append(_i(ic, 1044, y, 1.05, c, 2) + _t(1076, y + 11, t1, 12.5, 800, "#0B1B34", "start") + _t(1076, y + 26, t2, 11.5, 500, "#5B6B80", "start"))
    # going round the rules: stopped
    # going round the rules is stopped at check 2: no job gives access to the raw data
    out.append('<path d="M475 374 L475 392" stroke="#C8102E" stroke-width="3.5" marker-end="url(#sr)"/>')
    out.append('<polygon points="461,396 489,396 509,416 509,444 489,464 461,464 441,444 441,416" fill="#C8102E"/>'
               + _t(475, 435, "STOP", 13, 900, "#fff"))
    out.append(_t(475, 486, "Trying to go round the rules?", 14, 900, "#C8102E")
               + _t(475, 505, "Refused. Nobody, not even the analyst,", 12.5, 600, "#5B6B80")
               + _t(475, 521, "gets the raw data.", 12.5, 600, "#5B6B80"))
    # the systems stay where they are
    for k, (ic, c, t1, t2) in enumerate([(I_DB, "#C56A00", "Branch A system", "legacy"), (I_DOCS, "#0076AD", "Branch B system", "modern"),
                                          (I_IMG, "#7A4FD6", "Scans", "on S3")]):
        x = 740 + k * 126
        out.append(f'<rect x="{x - 59}" y="398" width="118" height="62" rx="14" fill="{c}"/>' + _i(ic, x - 11, 406, 0.95, "#fff", 2.1)
                   + _t(x, 442, t1, 11.5, 800, "#fff") + _t(x, 455, t2, 10, 500, "#fff"))
        out.append(f'<line x1="{x}" y1="396" x2="{x}" y2="374" stroke="{c}" stroke-width="2.5" stroke-dasharray="4 4"/>')
    out.append(_t(866, 488, "the systems stay where they are:", 12.5, 700, "#12796A") + _t(866, 505, "read in place, never copied", 12.5, 700, "#12796A"))
    out.append('</svg>')
    return "".join(out)
