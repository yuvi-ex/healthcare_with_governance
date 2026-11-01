#!/usr/bin/env python3
"""Demo reset: clear every request and decision so the story starts from 'no ticket'. Admin login, never the app.
  .venv/bin/python setup/reset.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module
con = import_module("01_access").admin()
con.execute("DELETE FROM HEALTH_ITSM.DECISIONS")
con.execute("DELETE FROM HEALTH_ITSM.REQUESTS")
con.execute("DELETE FROM HEALTH_ITSM.DEMO_EPOCH")
con.execute("INSERT INTO HEALTH_ITSM.DEMO_EPOCH VALUES (SYSTIMESTAMP)")
con.commit()
print("tickets cleared, audit trail starts now: every login is back to its standing access")
