"""The access-desk service: loopback only, 127.0.0.1:<HC_GOV_SERVICE_PORT> (8518). The console on dash-server calls it; it holds no account of
its own. Every operation runs as the signed-in person's Exasol login (see ops.py). Start: service/run.sh
POST /rpc {"fn": "...", "args": [...]} -> {"ok": true, "result": ...}      GET /health
"""
import json
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent  # noqa: E402
import freeask  # noqa: E402
import ops  # noqa: E402

PORT = ops.hcconfig.SERVICE_PORT


def agent_ask(token):
    with ops._LOCK:
        s = ops._SESSIONS.get(token)
    if not s:
        raise ops.Refused("Signed out. Sign in again.")
    return agent.ask(s["user"], s["password"])


OPS = {"health": ops.health, "login": ops.login, "demo_login": ops.demo_login, "logout": ops.logout,
       "clinician": ops.clinician, "chart": ops.chart, "ask": ops.ask, "ask_free": freeask.ask_free, "analyst": ops.analyst, "owner": ops.owner, "auditor": ops.auditor,
       "request_access": ops.request_access, "decide": ops.decide, "probe": ops.probe, "agent_ask": agent_ask}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        self._send(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

    def do_POST(self):  # noqa: N802
        t = time.time()
        if self.path != "/rpc":
            return self._send(404, {"ok": False})
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 1_000_000)))
            res = OPS[req["fn"]](*req.get("args", []))
            self._send(200, {"ok": True, "result": res})
            print(f"{time.strftime('%H:%M:%S')} {req['fn']:16} {time.time() - t:6.2f}s", flush=True)  # never the args
        except KeyError:
            self._send(404, {"ok": False, "error": "unknown operation"})
        except ops.Refused as e:
            self._send(200, {"ok": False, "error": str(e), "signed_out": True})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._send(500, {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
