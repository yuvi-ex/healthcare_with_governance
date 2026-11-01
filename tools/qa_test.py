"""Headless check of tab 3 (Ask questions): the six questions as the doctor, the analyst, the doctor with a ticket and the
data owner. .venv/bin/python tools/qa_test.py <outdir>"""
import json, sys, time, urllib.request
from playwright.sync_api import sync_playwright
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig  # noqa: E402
URL, out = f"http://127.0.0.1:{hcconfig.DASH_PORT}/apps/{hcconfig.APP}/", sys.argv[1]
def rpc(fn, *a):
    return json.loads(urllib.request.urlopen(urllib.request.Request(hcconfig.SERVICE_URL + "/rpc", data=json.dumps({"fn": fn, "args": a}).encode()), timeout=120).read())["result"]
def ask(pg, i, name):
    pg.locator(".qcards button").nth(i).click()
    pg.wait_for_function("i => { const b = document.querySelectorAll('.qcards button')[i]; return b && b.className.includes('on'); }", arg=i, timeout=30000)
    pg.wait_for_function("() => { const o = document.getElementById('q-out'); return o && !o.closest('[data-dash-is-loading]') && /Answered as|Sign in|Refused/.test(o.innerText); }", timeout=120000)
    time.sleep(2.5)
    el = pg.locator("#q-out"); el.screenshot(path=f"{out}/q_{name}.png"); print("shot", name, "|", el.inner_text()[:150].replace("\n", " "), flush=True)
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); pg = b.new_page(viewport={"width": 1500, "height": 1100})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL); pg.wait_for_selector(".hw-pic", timeout=120000)
    pg.get_by_text("5 · Security", exact=True).click(); time.sleep(1.5)
    h = pg.evaluate("() => document.querySelector('.page').scrollHeight"); pg.set_viewport_size({"width": 1500, "height": h + 40}); time.sleep(1)
    pg.screenshot(path=f"{out}/sec.png"); pg.set_viewport_size({"width": 1500, "height": 1100}); print("shot security")
    pg.get_by_text("2 · Sign in and work", exact=True).click(); pg.wait_for_selector(".cards4"); pg.locator(".pc").first.click()
    pg.wait_for_function("() => document.querySelector('.ubar code') && document.querySelector('.ubar code').innerText === 'DR_PRIYA'", timeout=60000)
    pg.get_by_text("3 · Ask questions", exact=True).click(); time.sleep(1)
    for i, k in enumerate(["who", "allergy", "scans", "similar", "readmit", "risk"]):
        ask(pg, i, f"dr_{k}")
    pg.locator('.ubar button:has-text("Kumar")').click()
    pg.wait_for_function("() => document.querySelector('.ubar code').innerText === 'ANALYST_RAVI'", timeout=60000); time.sleep(1)
    for i, k in [(3, "similar"), (4, "readmit"), (5, "risk"), (0, "who")]:
        ask(pg, i, f"an_{k}")
    # approve a ticket for her Branch A record through the service, as the two people would
    dr, ow = rpc("demo_login", "DR_PRIYA")["token"], rpc("demo_login", "OWNER_ANITA")["token"]
    rpc("request_access", dr, "WC-000468", "CHN", "Admitted today with pneumonia; need her Branch A history", 15)
    q = rpc("owner", ow)["queue"]["rows"]; rpc("decide", ow, q[0]["REQ_NO"], "APPROVE", 15, "today only"); print("ticket", q[0]["TICKET"], "approved")
    pg.locator('.ubar button:has-text("Dr. Priya")').click()
    pg.wait_for_function("() => document.querySelector('.ubar code').innerText === 'DR_PRIYA'", timeout=60000); time.sleep(1)
    for i, k in [(0, "who"), (1, "allergy"), (2, "scans"), (4, "readmit")]:
        ask(pg, i, f"tk_{k}")
    pg.locator('.ubar button:has-text("Rao")').click()
    pg.wait_for_function("() => document.querySelector('.ubar code').innerText === 'OWNER_ANITA'", timeout=60000); time.sleep(1)
    ask(pg, 0, "ow_who")
    # a typed question (needs ANTHROPIC_API_KEY; without it the page says Claude is not set up), as the doctor
    pg.locator('.ubar button:has-text("Dr. Priya")').click()
    pg.wait_for_function("() => document.querySelector('.ubar code').innerText.endsWith('DR_PRIYA')", timeout=60000); time.sleep(1)
    pg.fill("#own-q", "How many patients are in a bed right now?"); pg.click("#own-go")
    pg.wait_for_function("() => { const o = document.getElementById('q-out'); return o && !o.closest('[data-dash-is-loading]') && /bed|not set up|not reachable|No query/i.test(o.innerText) && !/pick one of the six/.test(o.innerText); }", timeout=120000)
    time.sleep(2); pg.locator("#q-out").screenshot(path=f"{out}/q_free.png"); print("shot free |", pg.inner_text("#q-out")[:200].replace("\n", " "))
    b.close()
print("console errors:", errs[:5])
