"""The AI agent path: the real exasol-mcp-server (stdio), started as the SIGNED-IN person's own Exasol login.

The agent gets exactly the access that person has at that moment: the same governed views, the same ticket rules, the
same audit trail. It cannot see a locked record any more than the person can.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig  # noqa: E402

UVX = shutil.which("uvx") or "/opt/homebrew/bin/uvx"
MCP_PKG = "exasol-mcp-server@2.2.0"
TIMEOUT = 90
SETTINGS = {"schemas": {"like_pattern": "HEALTH_GOV"}, "tables": {"enable": False}, "views": {"enable": True},
            "functions": {"enable": False}, "scripts": {"enable": False}, "enable_read_query": True,
            "enable_write_query": False, "enable_read_bucketfs": False, "enable_write_bucketfs": False,
            "enable_preprocessor_tools": False, "default_row_limit": 50}
QUESTION = "Summarise Meenakshi Sundaram's full history across branches. Is today's draft prescription safe?"
SQL_ALERT = ("SELECT DRUG, ORDER_BRANCH, ALLERGY_AS_RECORDED, ALLERGY_BRANCH, TICKET FROM HEALTH_GOV.ALLERGY_ALERTS "
             "WHERE UNIFIED_ID = 'WC-000468'")
SQL_RECORDS = "SELECT BRANCH, SOURCE_SYSTEM, ACCESS, TICKET FROM HEALTH_GOV.PATIENT_RECORDS WHERE UNIFIED_ID = 'WC-000468'"
# no ORDER BY: the MCP server wraps every query as SELECT * FROM (...) LIMIT n, and an ORDER BY inside that stops the
# filter reaching the branch systems (23 s instead of 1 s). Sorted in Python instead.
SQL_VISITS = "SELECT ADMIT_DATE, BRANCH, DIAGNOSIS, TICKET FROM HEALTH_GOV.ENCOUNTERS WHERE UNIFIED_ID = 'WC-000468'"
SQL_SCANS = "SELECT STUDY_DATE, BRANCH, MODALITY, STUDY_DESCRIPTION, TICKET FROM HEALTH_GOV.IMAGING WHERE UNIFIED_ID = 'WC-000468'"


class Mcp:
    def __init__(self, user, password):
        env = dict(os.environ, EXA_DSN=f"{hcconfig.EXA_HOST}/nocertcheck:{hcconfig.EXA_PORT}", EXA_USER=user, EXA_PASSWORD=password,
                   EXA_MCP_SETTINGS=json.dumps(SETTINGS))
        self.p = subprocess.Popen([UVX, MCP_PKG], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  env=env, text=True, bufsize=1)
        self.n, self.q = 0, queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "health-access-desk", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _pump(self):
        for line in self.p.stdout:
            self.q.put(line)
        self.q.put(None)

    def _send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def _rpc(self, method, params):
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        deadline = time.time() + TIMEOUT
        while True:
            try:
                line = self.q.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                raise ConnectionError(f"No answer from the MCP server within {TIMEOUT} s")
            if line is None:
                raise ConnectionError("The MCP server stopped")
            msg = json.loads(line)
            if msg.get("id") == self.n:
                return msg

    def call(self, tool, args):
        t = time.time()
        r = self._rpc("tools/call", {"name": tool, "arguments": args})
        res = r.get("result") or {}
        text = "".join(c.get("text", "") for c in res.get("content", []))
        d = res.get("structuredContent") or {}
        rows = [dict(zip(d.get("columns") or [], x)) for x in (d.get("rows") or [])] if isinstance(d, dict) else []
        return {"tool": tool, "args": args, "error": bool(res.get("isError")) or "error" in r, "text": text[:600],
                "rows": rows, "secs": time.time() - t}

    def close(self):
        try:
            self.p.terminate()
        except Exception:  # noqa: BLE001
            pass


def ask(user, password):
    t0 = time.time()
    m = Mcp(user, password)
    try:
        steps = [m.call("list_exasol_tables_and_views", {"schema_name": "HEALTH_GOV"}),
                 m.call("execute_exasol_query", {"query": SQL_RECORDS}),
                 m.call("execute_exasol_query", {"query": SQL_VISITS}),
                 m.call("execute_exasol_query", {"query": SQL_SCANS}),
                 m.call("execute_exasol_query", {"query": SQL_ALERT})]
    finally:
        m.close()
    return {"user": user, "question": QUESTION, "steps": steps, "records": steps[1]["rows"], "visits": sorted(steps[2]["rows"], key=lambda r: str(r.get("ADMIT_DATE"))),
            "scans": steps[3]["rows"], "alerts": steps[4]["rows"],
            "secs": time.time() - t0, "at": time.strftime("%H:%M:%S")}
