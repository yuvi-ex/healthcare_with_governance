"""Patient records, access on request: the access-desk console on dash-server.

People sign in with their own Exasol login. The console holds no credentials and opens no database session: every
action is a named operation on the access-desk service (../service, loopback only), which runs it as the signed-in
person. What each person may see or do is decided by Exasol: one role per job, governed views, and tickets that open
another branch's records of one patient for a set time.
"""
import base64
import re
import time
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

import desk
import picture as P
import qa
import rls
import views as V
from page_css import PAGE_CSS
from theme import CSS as THEME_CSS

HERE = Path(__file__).resolve().parent
HERO = "WC-000468"


def _css(s):
    return s.replace("<style>", "").replace("</style>", "")


DASH_CSS = """
html, body { margin:0; }
body { font-family:"Figtree",sans-serif; color:var(--ink);
  background: radial-gradient(circle at top left, rgba(226,244,255,0.95), transparent 30%),
              radial-gradient(circle at top right, rgba(227,245,241,0.85), transparent 26%),
              linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 55%, #ffffff 100%); background-attachment:fixed; min-height:100vh; }
.page { padding:1.4rem 2.2rem 3rem; max-width:1700px; margin:0 auto; }
.md > p:empty { display:none; } .md p { margin:0; }
.tabbar { border-bottom:1px solid var(--line) !important; margin-bottom:.6rem; }
.tabbar .tab { background:transparent !important; border:0 !important; border-bottom:3px solid transparent !important; font-weight:600; font-size:.95rem;
  color:var(--muted) !important; padding:.55rem 0 !important; margin-right:1.6rem; width:auto !important; flex:0 0 auto !important; }
.tabbar .tab--selected { color:var(--bad) !important; border-bottom-color:var(--bad) !important; }
.btn { font-family:"Figtree",sans-serif; font-weight:600; font-size:.92rem; border-radius:12px; border:1px solid rgba(31,160,139,.35);
  background:linear-gradient(135deg,#081226 0%,#10203F 100%); color:#fff; padding:.6rem 1rem; cursor:pointer; text-align:left; }
.btn:hover { filter:brightness(1.18); } .btn.ghost { background:#fff; color:var(--ink2); border:1px solid var(--edge); }
.btn.on { background:linear-gradient(135deg,#12796A 0%,#1FA08B 100%); border-color:#1FA08B; }
.btn.sm { font-size:.8rem; padding:.4rem .75rem; border-radius:10px; }
.inp { font-family:"Figtree",sans-serif; font-size:.92rem; border-radius:12px; border:1px solid var(--edge); padding:.55rem .8rem; background:#fff; }
.seg .dash-options-list-option, .seg label { font-size:.88rem; margin-right:1rem; }
details.eng { border-radius:14px; border:1px solid var(--edge); background:#fff; margin:.6rem 0; padding:.2rem .9rem; }
details.eng > summary { cursor:pointer; font-weight:700; font-size:.9rem; color:var(--ink2); padding:.55rem 0; }
pre.sql { font-family:"JetBrains Mono",monospace; font-size:.74rem; line-height:1.5; background:#0B1730; color:#DCE6F5; border-radius:12px;
  padding:.7rem .9rem; white-space:pre-wrap; word-break:break-word; margin:.2rem 0 .6rem; }
@media (max-width:1100px) { .page { padding:1rem; } }
"""
STYLE = _css(THEME_CSS) + _css(PAGE_CSS) + V.CSS + V.CHART_CSS + qa.CSS + qa.FREE_CSS + rls.CSS + rls.SIMPLE_CSS + P.CSS + DASH_CSS
INDEX = ("<!DOCTYPE html><html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}<style>" + STYLE
         + "</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>")
_VOID = re.compile(r"<(br|hr|img|wbr)(\s[^<>]*?)?(?<!/)>")
TAB = {"style": {}, "selected_style": {}, "className": "tab", "selected_className": "tab--selected"}


def H(fragment):
    """Raw HTML as one Markdown block (no blank lines or indentation, void tags closed, or dcc.Markdown renders nothing)."""
    text = "\n".join(l.strip() for l in str(fragment).splitlines() if l.strip())
    text = f"<div>{text}</div>"  # a fragment that starts inline (<code>, text) loses nested markup otherwise
    return dcc.Markdown(_VOID.sub(r"<\1\2/>", text), dangerously_allow_html=True, className="md")


def _logo():
    b64 = base64.b64encode((HERE / "assets" / "exasol_logo_dark.svg").read_bytes()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" alt="Exasol" width="104" height="26" style="height:26px;width:auto;max-width:104px;display:block;"/>'


def hero(ok):
    pill = lambda good, t: f'<span class="hs-pill{"" if good else " down"}">{t}</span>'  # noqa: E731
    return (f'<div class="hero-slim"><div class="hs-t">Patient records, <em>access on request</em>'
            f'<span>Everyone signs in with their own Exasol login. Exasol checks the password, enforces the role, opens another branch\'s '
            f'records only on an approved ticket, closes them when it runs out, and keeps every query on record.</span></div>'
            f'<div class="hs-m">{pill(ok, "Exasol")}{pill(ok, "Access desk")}</div></div>')


def persona_buttons(cls="pc"):
    return html.Div(className="cards4", children=[
        html.Button(id={"type": "as", "u": u}, n_clicks=0, className=cls, style={"--c": c}, children=[
            html.Span(r, className="r"), html.Span(n, className="n"), html.Span(j, className="j"), html.Span(u, className="u")])
        for u, (n, j, r, c) in V.PEOPLE.items()])


def signin_panel():
    return html.Div([
        H('<div class="ov-band" style="margin-top:.2rem"><div class="ov-k">Sign in</div>'
          '<div class="ov-h">Pick a person. Exasol checks the password.</div>'
          '<div class="ov-s">Each card signs in with that person\'s own Exasol login (the password stays on the server). '
          'Or type a login below: a wrong password is refused by Exasol, not by this page.</div></div>'),
        persona_buttons(),
        html.Div(className="lform", children=[
            dcc.Input(id="lu", placeholder="Exasol login, e.g. DR_PRIYA", className="inp", type="text", debounce=False),
            dcc.Input(id="lp", placeholder="Password", className="inp", type="password"),
            html.Button("Sign in", id="lgo", n_clicks=0, className="btn on")]),
    ])


def userbar(tok):
    if not tok:
        return H('<div class="ubar"><span class="who">Not signed in</span><span class="role none">no role</span></div>')
    roles = [html.Span(r, className="role") for r in tok.get("roles", [])] or [html.Span("no role", className="role none")]
    return html.Div(className="ubar", children=[
        html.Span(className="who", children=["Signed in as ", html.B(tok["name"]), f" · {tok['job']} · Exasol login ", html.Code(tok["user"]), *roles]),
        html.Span(className="sp"),
        html.Span("Switch to:", style={"fontSize": ".8rem", "color": "var(--faint)"}),
        *[html.Button(n.split()[-1] if not n.startswith("Dr") else "Dr. Priya", id={"type": "as", "u": u}, n_clicks=0, className="btn ghost sm")
          for u, (n, *_r) in V.PEOPLE.items() if u != tok["user"]],
        html.Button("Sign out", id="lout", n_clicks=0, className="btn sm")])


def role_of(tok):
    roles = set((tok or {}).get("roles", []))
    for r in ("HC_CLINICIAN", "HC_DATA_OWNER", "HC_ANALYST", "HC_AUDITOR"):
        if r in roles:
            return r
    return None


def probe_btn(kind, label):
    return html.Button(label, id={"type": "probe", "k": kind}, n_clicks=0, className="btn ghost sm")


def workspace(tok):
    """The static frame for the signed-in role. The live part (#live) refreshes on its own; forms stay put."""
    if not tok:
        return signin_panel()
    role = role_of(tok)
    probes = html.Div([html.Div("Try to go round the rules", className="cap2", style={"fontSize": ".78rem", "color": "var(--faint)", "fontWeight": 700, "margin": ".8rem 0 .3rem"}),
                       html.Div(className="btns", children={
                           "HC_CLINICIAN": [probe_btn("raw", "Read the allergy table directly"), probe_btn("approve", "Approve my own request")],
                           "HC_DATA_OWNER": [probe_btn("patients", "Open the patient records")],
                           "HC_ANALYST": [probe_btn("request", "Request a named patient's records"), probe_btn("raw", "Read the allergy table directly")],
                           "HC_AUDITOR": [probe_btn("patients", "Open the patient records")]}.get(role, [])),
                       dcc.Loading(html.Div(id="pr-out"), type="dot")])
    # a fresh Store with each frame: its arrival fires the live callback once for THIS frame (no race with the old one)
    live = html.Div([dcc.Store(id="live-key", data=f'{tok["token"][:8]}-{time.time()}'),
                     dcc.Loading(html.Div(id="live"), type="dot", delay_show=1500)])
    if role == "HC_CLINICIAN":
        form = html.Div(className="blk", children=[
            H('<div class="k">Request her full Branch A record</div><div class="s" style="font-size:.84rem;color:var(--muted);margin-bottom:.4rem">'
              'Visits, notes, medications, allergies and scans held at Branch A, for this one patient, for the time you choose.</div>'),
            html.Div(className="rq", children=[
                dcc.Textarea(id="rq-reason", className="inp", value="Admitted today with pneumonia. Need her Branch A history (2017 stroke, 2019 admission, earlier chest X-ray) before treating."),
                dcc.RadioItems(id="rq-min", className="seg", inline=True, value=15,
                               options=[{"label": " 15 minutes", "value": 15}, {"label": " One shift (8 h)", "value": 480}, {"label": " 24 hours", "value": 1440}]),
                html.Button("Raise the request", id="rq-go", n_clicks=0, className="btn on")]),
            dcc.Loading(html.Div(id="rq-out"), type="dot")])
        return html.Div(className="grid2", children=[html.Div([live]), html.Div([form, probes])])
    if role == "HC_DATA_OWNER":
        return html.Div([H('<div class="ov-band" style="margin-top:.2rem"><div class="ov-k">Data owner, Branch A</div>'
                           '<div class="ov-h">Requests for Branch A records</div><div class="ov-s">You decide who may open your branch\'s records, '
                           'for which patient and for how long. You never see the records themselves.</div></div>'),
                         dcc.Loading(html.Div(id="dec-out"), type="dot"), live, probes])
    if role in ("HC_ANALYST", "HC_AUDITOR"):
        return html.Div([live, probes])
    return H('<div class="refused">This login has none of the demo roles.</div>')


def eng(res_list):
    blocks = [html.Pre(r["sql"], className="sql") for r in res_list if r and r.get("sql")]
    return html.Details(className="eng", children=[html.Summary("The statements, as run under this login")] + blocks) if blocks else None


def agent_tab():
    return html.Div([
        H('<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">AI agent</div>'
          '<div class="ov-h">The agent signs in as the person it works for</div>'
          '<div class="ov-s">The real Exasol MCP server, started with the signed-in person\'s own login, the way Claude Desktop would start it. '
          'Ask before and after the ticket is approved: the agent sees exactly what the person may see, and its queries land in the same audit trail.</div></div>'),
        html.Button("Ask the agent: summarise her full history, and is today's prescription safe?", id="ag-go", n_clicks=0, className="btn on"),
        dcc.Loading(html.Div(id="ag-out"), type="dot"),
    ])


PRE = {"fontFamily": "JetBrains Mono, monospace", "fontSize": ".72rem", "lineHeight": "1.45", "background": "#0B1730", "color": "#DCE6F5",
       "borderRadius": "10px", "padding": ".5rem .7rem", "whiteSpace": "pre", "overflowX": "auto", "margin": ".25rem 0"}


def rls_panel(key, tok, d):
    """Row-level security for the signed-in person: their access list, what Exasol did to this answer, the rule that did it."""
    _view, lines = rls.RULE[key]
    rule = html.Div(className="c rule", children=[
        H(rls.rule_head(key)), html.Pre(lines, style=PRE),
        html.Details([html.Summary("The access list these lines join to", style={"cursor": "pointer", "fontSize": ".82rem", "fontWeight": 700}),
                      html.Pre(rls.ACCESS_LIST, style=PRE)]), H(rls.TAGS)])
    return html.Div(className="rlsband", children=[
        H(rls.panel_head(tok)),
        html.Div(className="rls3", children=[H(rls.access_list(tok, d)), H(rls.what_it_did(key, d)), rule]),
        html.Div(H(rls.BETTER), style={"marginTop": ".7rem"})])


def qa_tab():
    """Full width: ask anything first, then the six questions as large cards, then the answer."""
    return html.Div([
        H('<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">Ask questions</div>'
          '<div class="ov-h">Ask anything. The answer depends on who asks.</div>'
          '<div class="ov-s">Every question runs as the signed-in person. Ask as the doctor, then as the analyst, then as the doctor again once '
          'her ticket is approved. Under every answer, in plain words: why you see what you see.</div></div>'),
        html.Div(className="ask2", children=[
            H('<div class="k">Ask your own question</div>'),
            html.Div(className="askrow", children=[
                dcc.Textarea(id="own-q", className="inp", placeholder="Type any question about patients, visits, allergies, medicines or scans..."),
                html.Button("Ask", id="own-go", n_clicks=0, className="btn on")]),
            html.Div(className="ex2", children=[H('<span class="lbl">Try:</span>')]
                     + [html.Button(x, id={"type": "ex", "i": i}, n_clicks=0) for i, x in enumerate(qa.EXAMPLES)]),
            H('<div class="hint">Claude writes the query in 5 to 15 seconds, from the views your login may read. Exasol runs it as you.</div>')]),
        H('<div class="k6">Or pick one of the six</div>'),
        html.Div(className="qcards", children=[html.Button([html.Span(str(i), className="qn"), html.Span(t, className="qt")],
                                                           id={"type": "q", "k": k}, n_clicks=0, className="btn")
                                               for i, (k, t) in enumerate(qa.QS, 1)]),
        dcc.Loading(html.Div(id="q-out", children=H('<div class="blk"><div class="s" style="color:var(--muted)">Ask a question above, or pick one of the six. '
                                                    'Sign in first (tab 2) or use the switch buttons at the top.</div></div>')), type="dot")])


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/",
               requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               assets_folder=str(HERE / "assets"), title="Patient records, access on request",
               suppress_callback_exceptions=True, index_string=INDEX)

    app.layout = html.Div(className="page", children=[
        H(f'<div class="pagehead">{_logo()}<span class="ph-t">Hospital group &middot; patient records, access on request &middot; live demo</span></div>'),
        html.Div(id="hero", children=H(hero(True))),
        dcc.Store(id="tok", storage_type="session"), dcc.Store(id="bump", data=0),
        dcc.Interval(id="tick", interval=15_000, n_intervals=0), dcc.Interval(id="slow", interval=60_000, n_intervals=0),
        html.Div(id="ubar"), html.Div(id="lmsg"),
        dcc.Tabs(id="tabs", value="how", className="tabbar", parent_className="tabs-wrap", children=[
            dcc.Tab(label="1 · How it works", value="how", children=H(P.how_page()), **TAB),
            dcc.Tab(label="2 · Sign in and work", value="ws", children=html.Div(id="ws"), **TAB),
            dcc.Tab(label="3 · Ask questions", value="qa", children=qa_tab(), **TAB),
            dcc.Tab(label="4 · AI agent", value="agent", children=agent_tab(), **TAB),
            dcc.Tab(label="5 · Security", value="sec", children=H(P.security()), **TAB),
        ]),
    ])

    @app.callback(Output("hero", "children"), Input("slow", "n_intervals"))
    def _hero(_):
        try:
            return H(hero(bool(desk.call("health", timeout=10).get("exa"))))
        except desk.Down:
            return H(hero(False))

    # ---- sign in / out: one callback per trigger, so each one's inputs are on the page whenever it can fire
    def _signed(r):
        if not r.get("ok"):
            return None, "ws", H(f'<div class="refused"><b>Refused by Exasol:</b> {V.e(r.get("refused"))}</div>')
        return {k: r[k] for k in ("token", "user", "name", "job", "roles")}, "ws", None

    @app.callback(Output("tok", "data"), Output("tabs", "value"), Output("lmsg", "children"),
                  Input({"type": "as", "u": ALL}, "n_clicks"), State("tok", "data"), prevent_initial_call=True)
    def _as(_n, tok):
        t = ctx.triggered_id
        if not isinstance(t, dict) or not (ctx.triggered and ctx.triggered[0].get("value")):
            return no_update, no_update, no_update
        try:
            if tok:
                desk.call("logout", tok["token"])
            new, _tab, msg = _signed(desk.call("demo_login", t["u"]))
            return new, no_update, msg  # switching person keeps the tab: ask the same question as someone else
        except desk.Down as e:
            return no_update, no_update, H(f'<div class="refused">{V.e(e)}</div>')

    @app.callback(Output("tok", "data", allow_duplicate=True), Output("tabs", "value", allow_duplicate=True),
                  Output("lmsg", "children", allow_duplicate=True), Input("lgo", "n_clicks"), State("lu", "value"), State("lp", "value"),
                  prevent_initial_call=True)
    def _typed(n, lu, lp):
        if not n:
            return no_update, no_update, no_update
        try:
            return _signed(desk.call("login", lu or "", lp or ""))
        except desk.Down as e:
            return no_update, no_update, H(f'<div class="refused">{V.e(e)}</div>')

    @app.callback(Output("tok", "data", allow_duplicate=True), Input("lout", "n_clicks"), State("tok", "data"), prevent_initial_call=True)
    def _out(n, tok):
        if not n:
            return no_update
        try:
            if tok:
                desk.call("logout", tok["token"])
        except desk.Down:
            pass
        return None

    @app.callback(Output("ubar", "children"), Output("ws", "children"), Input("tok", "data"))
    def _frame(tok):
        return userbar(tok), workspace(tok)

    # ---- the live part of each workspace
    @app.callback(Output("live", "children"), Input("live-key", "data"), Input("bump", "data"), Input("tick", "n_intervals"),
                  State("tok", "data"), State("tabs", "value"))
    def _live(_k, _b, _t, tok, tab):
        if not tok:
            return no_update
        role, u = role_of(tok), tok["user"]
        # only the auditor's screen refreshes on its own (the audit log lags by a minute); the others refresh on an
        # action, so their screens do not fill the audit trail with repeated reads
        if ctx.triggered_id == "tick" and (tab != "ws" or role != "HC_AUDITOR"):
            return no_update
        try:
            if role == "HC_CLINICIAN":
                d = desk.call("chart", tok["token"], HERO, timeout=180)
                return [H(V.access_banner(u, d["access"]) + V.safety(u, d["alerts"], d["records"]) + V.chart(u, d) + V.my_requests(u, d["mine"])),
                        eng([d[k] for k in ("access", "records", "identity", "encounters", "notes", "meds", "allergies", "alerts", "imaging", "mine")])]
            if role == "HC_DATA_OWNER":
                d = desk.call("owner", tok["token"])
                return owner_view(u, d["queue"])
            if role == "HC_ANALYST":
                d = desk.call("analyst", tok["token"])
                return [H(V.access_banner(u, d["access"]) + V.masked_alerts(u, d["alerts"])), eng([d["access"], d["alerts"]])]
            if role == "HC_AUDITOR":
                d = desk.call("auditor", tok["token"])
                return [H(V.tickets(u, d["tickets"]) + V.audit(u, d["audit"])), eng([d["tickets"], d["audit"]])]
        except desk.SignedOut:
            return H('<div class="refused">Signed out: sign in again.</div>')
        except desk.Down as e:
            return H(f'<div class="refused">{V.e(e)}</div>')
        return no_update

    def owner_view(u, q):
        if q.get("refused"):
            return H(V.refused(q))
        rows = []
        for r in q["rows"]:
            acts = []
            if r["STATUS"] == "PENDING":
                acts = [html.Button("Approve 15 min", id={"type": "dec", "req": int(r["REQ_NO"]), "d": "APPROVE", "m": 15}, n_clicks=0, className="btn on sm"),
                        html.Button("Approve 8 h", id={"type": "dec", "req": int(r["REQ_NO"]), "d": "APPROVE", "m": 480}, n_clicks=0, className="btn sm"),
                        html.Button("Reject", id={"type": "dec", "req": int(r["REQ_NO"]), "d": "REJECT", "m": 0}, n_clicks=0, className="btn red sm")]
            elif r["STATUS"] == "ACTIVE":
                acts = [html.Button("Revoke now", id={"type": "dec", "req": int(r["REQ_NO"]), "d": "REVOKE", "m": 0}, n_clicks=0, className="btn red sm")]
            rows.append(html.Tr([
                html.Td(H(f'<code>{V.e(r["TICKET"])}</code><div class="meta" style="margin:0">raised {V.hm(r["CREATED_AT"])}</div>')),
                html.Td(H(f'<b>{V.e(r["REQUESTER_NAME"])}</b><div class="meta" style="margin:0">{V.e(r["REQUESTER_JOB"])}</div>')),
                html.Td(H(f'<code>{V.e(r["UNIFIED_ID"])}</code><div class="meta" style="margin:0">{V.e(V.BR.get(r["BRANCH"]))} records</div>')),
                html.Td(V.e(r["REASON"])), html.Td(H(V.status(r))), html.Td(html.Div(acts, className="btns"))]))
        table = html.Div(className="tblw", children=html.Table(className="tbl", children=[
            html.Tr([html.Th(x) for x in ("Ticket", "Requested by", "Patient", "Reason", "Status", "Decide")])] + rows)) if rows else H(
            '<div class="s" style="color:var(--muted)">No requests yet.</div>')
        return html.Div(className="blk", children=[H('<div class="k">Your queue</div>'), table, H(V.meta(u, "HEALTH_ITSM.APPROVAL_QUEUE", q)),
                                                   eng([q])])

    # ---- actions
    @app.callback(Output("rq-out", "children"), Output("bump", "data", allow_duplicate=True), Input("rq-go", "n_clicks"),
                  State("rq-reason", "value"), State("rq-min", "value"), State("tok", "data"), State("bump", "data"), prevent_initial_call=True)
    def _request(n, reason, minutes, tok, b):
        if not n or not tok:
            return no_update, no_update
        try:
            r = desk.call("request_access", tok["token"], HERO, "CHN", reason, minutes)
        except (desk.Down, desk.SignedOut) as e:
            return H(f'<div class="refused">{V.e(e)}</div>'), no_update
        w = r["insert"]
        if w.get("refused"):
            return H(V.refused(w)), (b or 0) + 1
        t = (r["mine"]["rows"] or [{}])[0]
        return H(f'<div class="ok"><b>Ticket <code>{V.e(t.get("TICKET"))}</code> raised.</b> It waits for the data owner of Branch A. '
                 f'Sign in as Anita Rao to decide it.</div>'), (b or 0) + 1

    @app.callback(Output("dec-out", "children"), Output("bump", "data", allow_duplicate=True),
                  Input({"type": "dec", "req": ALL, "d": ALL, "m": ALL}, "n_clicks"), State("tok", "data"), State("bump", "data"),
                  prevent_initial_call=True)
    def _decide(_n, tok, b):
        t = ctx.triggered_id
        if not t or not (ctx.triggered and ctx.triggered[0].get("value")) or not tok:
            return no_update, no_update
        note = {"APPROVE": "Treating physician, this patient only", "REJECT": "Not enough reason given", "REVOKE": "Care episode closed"}[t["d"]]
        try:
            r = desk.call("decide", tok["token"], t["req"], t["d"], t["m"] or None, note)
        except (desk.Down, desk.SignedOut) as e:
            return H(f'<div class="refused">{V.e(e)}</div>'), no_update
        w = r["insert"]
        if w.get("refused"):
            return H(V.refused(w)), (b or 0) + 1
        what = {"APPROVE": f"approved for {t['m'] // 60} h" if t["m"] >= 60 else f"approved for {t['m']} minutes", "REJECT": "rejected",
                "REVOKE": "revoked: access ends now"}[t["d"]]
        return H(f'<div class="ok"><b>REQ{t["req"]:07d} {what}.</b> Recorded as a decision by <code>{V.e(tok["user"])}</code>; '
                 f'the ticket itself cannot be edited.</div>'), (b or 0) + 1

    @app.callback(Output("pr-out", "children"), Input({"type": "probe", "k": ALL}, "n_clicks"), State("tok", "data"), prevent_initial_call=True)
    def _probe(_n, tok):
        t = ctx.triggered_id
        if not t or not (ctx.triggered and ctx.triggered[0].get("value")) or not tok:
            return no_update
        try:
            r = desk.call("probe", tok["token"], t["k"])
        except (desk.Down, desk.SignedOut) as e:
            return H(f'<div class="refused">{V.e(e)}</div>')
        if r.get("refused"):
            return H(V.refused(r, r["label"]))
        return H(f'<div class="warn"><b>{V.e(r["label"])}: allowed.</b> {len(r["rows"])} rows. <code>{V.e(r["sql"])}</code></div>')

    @app.callback(Output("q-out", "children"), Output({"type": "q", "k": ALL}, "className"),
                  Input({"type": "q", "k": ALL}, "n_clicks"), State("tok", "data"), prevent_initial_call=True)
    def _ask(_n, tok):
        t = ctx.triggered_id
        keys = [k for k, _ in qa.QS]
        if not isinstance(t, dict) or not (ctx.triggered and ctx.triggered[0].get("value")):
            return no_update, no_update
        cls = ["btn on" if k == t["k"] else "btn" for k in keys]
        if not tok:
            return H('<div class="warn"><b>Sign in first</b> (tab 2, or the switch buttons): every answer is computed as the signed-in person.</div>'), cls
        try:
            d = desk.call("ask", tok["token"], t["k"], HERO, timeout=180)
        except (desk.Down, desk.SignedOut) as ex:
            return H(f'<div class="refused">{V.e(ex)}</div>'), cls
        # business view: why you see this, in plain words. The rule and the SQL are in the engineers' fold-out.
        engineers = html.Details(className="eng", children=[html.Summary("For engineers: the rule that did it, and the statements as run")]
                                 + [rls_panel(t["k"], tok, d)] + [html.Pre(v["sql"], className="sql") for v in d.values() if isinstance(v, dict) and v.get("sql")])
        return [H(qa.render(t["k"], tok, d)), H(rls.simple(t["k"], tok, d)), engineers], cls

    @app.callback(Output("q-out", "children", allow_duplicate=True), Input("tok", "data"), prevent_initial_call=True)
    def _ask_reset(tok):
        who = f"as {V.e(tok['name'])}" if tok else "after signing in"
        return H(f'<div class="blk"><div class="s" style="color:var(--muted)">Pick a question: it will be answered {who}.</div></div>')

    @app.callback(Output("own-q", "value"), Input({"type": "ex", "i": ALL}, "n_clicks"), prevent_initial_call=True)
    def _example(_n):
        t = ctx.triggered_id
        if not isinstance(t, dict) or not (ctx.triggered and ctx.triggered[0].get("value")):
            return no_update
        return qa.EXAMPLES[t["i"]]

    @app.callback(Output("q-out", "children", allow_duplicate=True), Output({"type": "q", "k": ALL}, "className", allow_duplicate=True),
                  Input("own-go", "n_clicks"), State("own-q", "value"), State("tok", "data"), prevent_initial_call=True)
    def _own(n, question, tok):
        cls = ["btn"] * len(qa.QS)
        if not n:
            return no_update, no_update
        if not tok:
            return H('<div class="warn"><b>Sign in first</b> (tab 2, or the switch buttons): the question runs as the signed-in person.</div>'), cls
        if not (question or "").strip():
            return H('<div class="warn"><b>Type a question</b>, or click one of the examples.</div>'), cls
        try:
            d = desk.call("ask_free", tok["token"], question, timeout=150)
        except (desk.Down, desk.SignedOut) as ex:
            return H(f'<div class="refused">{V.e(ex)}</div>'), cls
        sql = d.get("sql")
        engineers = html.Details(className="eng", children=[html.Summary("For engineers: the query Claude wrote, as run under this login")]
                                 + ([H(f'<div class="meta">{V.e(d.get("about", ""))}</div>'), html.Pre(sql, className="sql")] if sql else []))
        return [H(qa.free_render(tok, d)), H(rls.simple_free(tok, d)), engineers], cls

    @app.callback(Output("ag-out", "children"), Input("ag-go", "n_clicks"), State("tok", "data"), prevent_initial_call=True)
    def _agent(n, tok):
        if not n:
            return no_update
        if not tok:
            return H('<div class="warn"><b>Sign in first</b> (tab 2): the agent works for the person who is signed in.</div>')
        try:
            r = desk.call("agent_ask", tok["token"], timeout=150)
        except (desk.Down, desk.SignedOut) as e:
            return H(f'<div class="refused">{V.e(e)}</div>')
        steps = ""
        for s in r["steps"]:
            arg = (s["args"] or {}).get("query") or (s["args"] or {}).get("schema_name") or ""
            err = f'<div class="meta">{V.e(s["text"][:220])}</div>' if s["error"] else ""
            steps += f'<li><div><code>{V.e(s["tool"])}</code> {V.e(arg)}{err}</div><span class="s">{s["secs"]:.1f} s</span></li>'

        recs = r["records"]
        locked = [V.BR.get(x["BRANCH"]) for x in recs if x.get("ACCESS") == "locked"]
        vis = r.get("visits") or []
        hist = "".join(f'<li>{V.dmy(x["ADMIT_DATE"])} &middot; {V.e(V.BR.get(x["BRANCH"]))}: {V.e(x["DIAGNOSIS"])}</li>' for x in vis)
        scans = "".join(f'<li>{V.dmy(x["STUDY_DATE"])} &middot; {V.e(V.BR.get(x["BRANCH"]))}: {V.e(x["STUDY_DESCRIPTION"])}</li>' for x in (r.get("scans") or []))
        summary = (f'<div class="blk" style="margin-top:.5rem"><div class="k">Her history, as the agent may see it</div>'
                   f'<b>{len(vis)} visits</b><ul style="margin:.2rem 0 .5rem 1.1rem;padding:0;font-size:.86rem">{hist}</ul>'
                   f'<b>{len(r.get("scans") or [])} scans</b><ul style="margin:.2rem 0 0 1.1rem;padding:0;font-size:.86rem">{scans}</ul></div>')
        if r["alerts"]:
            a = r["alerts"][0]
            ans = (f'<div class="alert"><div class="h">Agent: stop, {V.e(a["DRUG"])} conflicts with a recorded allergy</div>'
                   f'<div class="d">{V.e(V.BR.get(a["ALLERGY_BRANCH"]))} recorded <b>{V.e(a["ALLERGY_AS_RECORDED"])}</b>. '
                   f'I could read it because ticket <code>{V.e(a["TICKET"])}</code> is active for {V.e(tok["name"])}.</div></div>')
        elif locked:
            ans = (f'<div class="warn"><b>Agent: no conflict in the records I can open, but I cannot check her {V.e(", ".join(locked))} record.</b> '
                   f'It is locked for {V.e(tok["name"])}. Ask the data owner of {V.e(", ".join(locked))} for a ticket.</div>')
        elif any(s["error"] for s in r["steps"]):
            ans = f'<div class="refused"><b>Agent: I may not read patient data as {V.e(tok["name"])}.</b> Exasol refused the queries.</div>'
        else:
            ans = '<div class="ok"><b>Agent: no conflict</b> in any of her records.</div>'
        return H(f'<div class="grid2" style="margin-top:.8rem"><div class="blk"><div class="k">What the agent did, signed in as <code>{V.e(r["user"])}</code></div>'
                 f'<ol class="steps">{steps}</ol><div class="meta">{r["secs"]:.1f} s in all, including starting the MCP server &middot; at {V.e(r["at"])}</div></div>'
                 f'<div class="blk"><div class="k">Its answer</div>{ans}{summary}</div></div>')

    return app
