# Healthcare with governance: patient records, access on request

A doctor needs a patient's records from another branch. Today that means a phone call, a shared password, or a copy
that never goes away. This demo shows the governed way, with every rule enforced **in Exasol**:

- People sign in with their **own Exasol login**, and Exasol checks the password.
- **One role per job** decides what each person can read and do.
- Another branch's records open only with a **ticket** that branch's data owner approved. A ticket covers one patient
  for a set time, and the view checks its expiry on every query.
- Exasol's **audit log** records every statement, refusals included, together with the ticket that was in force.
- An **AI agent** (the real `exasol-mcp-server`) signs in as the person and gets exactly their access, no more.

It sits on top of the **[hospital_chain](https://github.com/yuvi-ex/hospital_chain)** demo: three branch systems
(legacy HIS on Postgres, modern EHR on MongoDB, DICOM images on S3) federated by Exasol, with a patient index across them.
This repository adds the access layer and its own console. It reads hospital_chain's views and changes nothing there.

## The people

| Login | Person | Role | Sees | Can |
|---|---|---|---|---|
| `DR_PRIYA` | Dr. Priya Nair, treating physician, Branch B | `HC_CLINICIAN` | Branch B in full; another branch's full record of one patient while a ticket is open | raise a request |
| `OWNER_ANITA` | Anita Rao, records officer, Branch A | `HC_DATA_OWNER` | the request queue for Branch A, but no patient data | approve for a set time, reject, revoke |
| `ANALYST_RAVI` | Ravi Kumar, quality analyst | `HC_ANALYST` | every branch, with names masked | analyse; cannot request named data |
| `AUDITOR_SAM` | Sam Thomas, compliance auditor | `HC_AUDITOR` | every ticket and every statement, with the ticket in force, but no patient data | read the audit trail |

The patient is Meenakshi Sundaram, 68. She was treated at Branch A years ago and had anaphylaxis to penicillin there.
Today she is admitted at Branch B, where no allergy is on file, and a penicillin has just been drafted.

## The story (about 7 minutes)

The console has five tabs: **1 How it works · 2 Sign in and work · 3 Ask questions · 4 AI agent · 5 Security**.

1. **How it works**: one picture of the flow.
2. **Sign in as Dr. Priya.** A wrong password is refused by Exasol itself. Her chart shows only today at Branch B: one
   admission (pneumonia), one chest X-ray and one note, with no allergies. **Her Branch A record is locked**, and the
   safety check warns that it cannot see allergies held there. "Read the allergy table directly" is refused by Exasol.
3. She **requests** Meenakshi's Branch A record, with a reason. That creates a ticket, `REQ…`.
4. **Switch to Anita** and approve it for 15 minutes. If Anita tries to open the patient records herself, she is refused.
5. **Switch back to Dr. Priya.** The **whole Branch A history opens**: six more visits, the earlier chest X-ray and
   brain MRI from S3 (behind signed links that expire with the ticket), four discharge summaries, earlier medications
   and the **penicillin anaphylaxis**, so the allergy alert fires. Everything the ticket opened is labelled with its
   number.
6. **AI agent**: the agent summarises her full history *as Dr. Priya*, through the MCP server, in about 5 seconds.
7. **Switch to Ravi**: names are masked, and asking for a named patient is refused.
8. **Switch to Sam**: every ticket, and the audit trail with the ticket in force on every statement.
9. *Optional:* Anita revokes the ticket, and the Branch A part of the chart closes at once.
10. **Security**: one picture showing who asks, the four checks in one central Exasol, the systems read in place, and
    the audit log under all of it.

**Ask questions (tab 3).** Six fixed questions, each answered as whoever is signed in, so the answer depends on who
asks. For example:

- Readmissions: Dr. Priya counts 115, none of them across a branch. Ravi counts 462, of which 148 cross a branch, all
  masked.
- Her scans: Dr. Priya sees 1 before the ticket and 3 after it.
- Anita and Sam are refused on all six.

Under every answer, **"Why you see this"** explains in plain words what came from the person's job, what came from a
ticket, and what was hidden. The exact rule and the SQL are in the "For engineers" fold-out.

**Ask your own question** (also tab 3). Type anything and three things happen:

1. Claude writes one read-only query, using only the views the signed-in person may read.
2. Exasol runs that query **as that person**, so safety never depends on the model.
3. Claude gives the answer in plain words.

Good questions to try:

- As Ravi: "List all patients with their names and phone numbers". He gets IDs only, because names and phones are hidden.
- As Anita: "Show me Meenakshi's discharge notes". No query runs, because her job reads no patient data.
- As anyone: "Delete all tickets". It is declined, because questions can only read.

## How it works

```
Browser ──► console on dash-server ──► access-desk service (loopback) ──► Exasol, as the signed-in person
                (no credentials)          opens a session per action          roles · governed views · tickets
                                          with that person's own login        audit log
                                                                                    │
                                     hospital_chain: HOSP_* views ◄─────────────────┘
                                     Postgres (legacy HIS) · MongoDB (EHR) · S3 (DICOM), all read live, in place
```

| Piece | What it does |
|---|---|
| `sql/10_itsm.sql` | `HEALTH_ITSM`: the people, standing access, data owners, requests and decisions (append-only), the ticket state, the queue and the audit trail. `HEALTH_GOV`: the governed views. They filter each record by `CURRENT_USER`'s standing access plus any active ticket, mask names for the analyst and expose the safety check. Also the four roles and their grants. |
| `sql/20_chart.sql` | The whole chart, governed record by record: identity, visits, clinical notes (read live from Postgres and MongoDB), medications and imaging (S3 keys only for records you may open). |
| `sql/30_questions.sql` | The views behind the six questions: readmissions, similar patients (note vectors) and visible branches. |
| `service/` | The **access desk** (`127.0.0.1:8518`). It runs every action as the signed-in person's own Exasol login (dash-server does not allow credentials in hosted apps), signs S3 links capped at the ticket's time left, starts the MCP server as the person for the AI agent, and calls Claude for typed questions. It never holds more than 6 sessions, because Exasol Personal allows 20 in total. |
| `dash/` | The console: Dash on dash-server, deployed by `dash/deploy.py`. It holds no credentials and opens no database session. |
| `setup/01_access.py` | Applies `sql/*.sql` in order and creates the four logins. Their passwords go to `secrets/hc_users.env` (mode 600) and are never printed. |
| `setup/reset.py` | Clears every request and decision and restarts the audit trail, for a clean start. |

**Design rules worth knowing:**

- **Tickets are append-only:** requests and decisions are inserted, never updated.
- **A forged row grants nothing:** a decision counts only if it came from a data owner of that branch who is not the
  requester.
- **One clock for expiry:** expiry uses `SYSTIMESTAMP`, the clock the audit log uses.
- **Refusals come from Exasol:** every refusal on screen is Exasol's own error message, not the app's.

## Build it

### What you need

1. **The hospital_chain demo, built.** Clone [hospital_chain](https://github.com/yuvi-ex/hospital_chain) next to
   this repository and follow its README (`setup/build_all.sh`). That gives you Exasol Personal with the
   `HOSP_*` objects, the branch systems, the images on S3 and the read-only S3 key.
2. **uv**, for this repository's Python environment, and `uvx`, which comes with uv and runs the MCP server.
3. *Optional:* an **Anthropic API key**, used for "Ask your own question". Without it everything else works.
4. *Optional:* Google Chrome, for the headless checks in `tools/`.

### Steps

```sh
# next to your hospital_chain checkout (or set HC_BASE_DIR in config.env)
git clone https://github.com/yuvi-ex/healthcare_with_governance.git && cd healthcare_with_governance

# optional, for typed questions
mkdir -p secrets && cp anthropic.env.example secrets/anthropic.env && chmod 600 secrets/anthropic.env
#   then put your key after ANTHROPIC_API_KEY= in secrets/anthropic.env

setup/build_all.sh
```

| Step | Does |
|---|---|
| 0 | `.venv` from `requirements.txt` (`setup/venv.sh`) |
| 1 | checks that the hospital_chain objects, its S3 bucket and its read-only key are there |
| 2 | the access layer and the four logins (`setup/01_access.py`) |
| 3 | checks for the Claude key (optional) |
| 4 | starts the access-desk service (`service/run.sh`) |
| 5 | deploys the console to dash-server (`dash/deploy.py`) |
| 6 | preflight with a clean start: GO / NO-GO |

Open `http://127.0.0.1:5100/apps/health-access`. Every step is re-runnable, and `setup/build_all.sh <n>` resumes
from step n.

### Before every demo

```sh
../hospital_chain/setup/preflight.sh     # first: Exasol, the branch systems, the VM clock
setup/preflight.sh --reset               # then: the service, the four logins, Claude, the console, and a clean start
```

`--reset` clears every ticket and restarts the audit trail. Run it just before the demo, not during it.

### Settings

`config.env` holds the settings: where hospital_chain is, the Exasol address, the service port, the app name and the
Claude model. An environment variable of the same name overrides any of them. The S3 bucket and key are read from
hospital_chain's own `config.env`, so both demos always use the same ones. Credentials never go in `config.env`: they
live in `secrets/`, which is git-ignored.

## Check it

- `setup/preflight.sh`: each of the four logins signs in and has the role Exasol says it has.
- `.venv/bin/python tools/story.py <dir>`: walks the whole story in headless Chrome and saves a screenshot per step:
  wrong password, locked chart, refused direct read, request, approval, owner refused, chart opened, agent, analyst
  refused, audit trail.
- `.venv/bin/python tools/qa_test.py <dir>`: the six questions as the doctor, the analyst, the doctor with a ticket and
  the data owner, plus one typed question.

## If asked: what changes in production

- **Who runs the database** can still change the rules. In production a separate team holds that job, and the record of
  every check is also kept outside the database.
- **Tickets live in Exasol here.** In production the service desk (ServiceNow, Jira Service Management and so on)
  raises and closes them and tells Exasol. The views stay the same.
- **Passwords here.** In production staff sign in with their company login (single sign-on), and Exasol still sees the
  person, not a shared account.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sign-ins hang, or the logs say `08004` / connection limit | Exasol Personal allows 20 connections in total. Restart the service: `pkill -f "$PWD/service/itsm_api.py"; service/run.sh`. If that does not help, restart dash-server: `exakit stop dash-server && exakit start dash-server`. |
| "The access-desk service is not answering" | `service/run.sh`; the log is `.work/itsm_api.log` |
| Scans do not show, or S3 answers 403 | The VM clock is off: run `../hospital_chain/setup/preflight.sh` |
| A ticket seems to expire at the wrong time | Times use `SYSTIMESTAMP` (UTC, like the audit log). Do not change them to `CURRENT_TIMESTAMP`, which follows the session time zone. |
| Typed questions say Claude is not set up | Put `ANTHROPIC_API_KEY=` in `secrets/anthropic.env`; it needs internet access |
| The audit trail is empty | Auditing must be on in Exasol (it is on in Exasol Personal). The trail starts at the last `--reset`. |

## Layout

```
config.env, hcconfig.py     settings (shell and Python); the S3 settings come from hospital_chain
sql/                        10 access layer + governed views · 20 the whole chart · 30 the six questions
setup/                      build_all.sh, venv.sh, 01_access.py (layer + logins), reset.py, preflight.sh
service/                    the access desk: itsm_api.py (HTTP), ops.py (operations as the person), agent.py (MCP), freeask.py (Claude)
dash/                       the console on dash-server; deploy.py publishes it
tools/                      story.py and qa_test.py, headless checks with screenshots
anthropic.env.example       template for secrets/anthropic.env
```

## Licence

MIT (see `LICENSE`). The patients are synthetic; the images come from hospital_chain (The Cancer Imaging Archive, CC BY 4.0).
