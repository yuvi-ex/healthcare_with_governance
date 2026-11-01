"""Headless walk through the access-desk story. .venv/bin/python tools/story.py <outdir>  (saves fail.png on a failed step)"""
import sys, time
from playwright.sync_api import sync_playwright
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig  # noqa: E402
URL, out = f"http://127.0.0.1:{hcconfig.DASH_PORT}/apps/{hcconfig.APP}/", sys.argv[1]
errs = []
def snap(pg, name):
    h = pg.evaluate("() => Math.max(document.body.scrollHeight, document.querySelector('.page').scrollHeight)")
    pg.set_viewport_size({"width": 1500, "height": min(h + 40, 6000)}); time.sleep(.8)
    pg.screenshot(path=f"{out}/{name}.png"); pg.set_viewport_size({"width": 1500, "height": 1000}); print("shot", name, flush=True)
def switch(pg, user, label):
    pg.locator(f'.ubar button:has-text("{label}")').first.click()
    pg.wait_for_function("u => document.querySelector('.ubar code') && document.querySelector('.ubar code').innerText === u", arg=user, timeout=60000)
    time.sleep(1)
def steps(pg):
    pg.goto(URL); pg.wait_for_selector(".hw-pic", timeout=120000); time.sleep(1); snap(pg, "1_how")
    pg.get_by_text("2 · Sign in and work", exact=True).click(); pg.wait_for_selector(".cards4"); snap(pg, "2_signin")
    pg.fill("#lu", "DR_PRIYA"); pg.fill("#lp", "not-her-password"); pg.click("#lgo")
    pg.wait_for_selector("#lmsg .refused", timeout=60000); print("wrong password:", pg.inner_text("#lmsg"))
    pg.locator(".pc").first.click()
    pg.wait_for_selector("text=Is the prescription drafted now safe for her?", timeout=90000); time.sleep(2)
    pg.locator('button:has-text("Read the allergy table directly")').click(); pg.wait_for_selector("#pr-out .refused", timeout=60000)
    snap(pg, "3_doctor_locked")
    pg.click("#rq-go"); pg.wait_for_selector("#rq-out .ok", timeout=60000); print("request:", pg.inner_text("#rq-out"))
    switch(pg, "OWNER_ANITA", "Rao"); pg.wait_for_selector('button:has-text("Approve 15 min")', timeout=60000); snap(pg, "4_owner_queue")
    pg.locator('button:has-text("Approve 15 min")').first.click(); pg.wait_for_selector("#dec-out .ok", timeout=60000)
    print("decision:", pg.inner_text("#dec-out"))
    pg.locator('button:has-text("Open the patient records")').click(); pg.wait_for_selector("#pr-out .refused", timeout=60000); snap(pg, "5_owner_after")
    switch(pg, "DR_PRIYA", "Dr. Priya"); pg.wait_for_selector(".alert", timeout=90000); time.sleep(1); snap(pg, "6_doctor_open")
    pg.get_by_text("4 · AI agent", exact=True).click(); pg.click("#ag-go"); pg.wait_for_selector("text=Its answer", timeout=150000); snap(pg, "7_agent")
    pg.get_by_text("2 · Sign in and work", exact=True).click()
    switch(pg, "ANALYST_RAVI", "Kumar"); pg.wait_for_selector("text=identities masked", timeout=90000)
    pg.locator('button:has-text("Request a named patient")').click(); pg.wait_for_selector("#pr-out .refused", timeout=60000); time.sleep(1); snap(pg, "8_analyst")
    switch(pg, "AUDITOR_SAM", "Thomas"); pg.wait_for_selector("text=Every ticket", timeout=60000)
    pg.wait_for_function("() => /Ticket in force[\\s\\S]*REQ00/i.test(document.body.innerText)", timeout=200000); time.sleep(1); snap(pg, "9_auditor")
    pg.get_by_text("5 · Security", exact=True).click(); time.sleep(1); snap(pg, "10_security")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    try:
        steps(pg)
    except Exception as ex:
        pg.screenshot(path=f"{out}/fail.png", full_page=True); print("FAILED:", str(ex)[:300]); sys.exit(1)
    finally:
        print("console errors:", errs[:5])
    b.close()
