"""Client for the access-desk service (../service/itsm_api.py; its address is in site_config, from config.env). The console holds no credentials and
opens no database session: it names an operation and passes the sign-in token; the service runs it as that person."""
import json
import urllib.error
import urllib.request

import site_config  # top level: dash-server resolves sibling modules only while app.py is imported

URL = site_config.SERVICE_URL + "/rpc"


class Down(Exception):
    pass


class SignedOut(Exception):
    pass


def call(fn, *args, timeout=120):
    body = json.dumps({"fn": fn, "args": args}, default=str).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        out = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        raise Down(f"The access-desk service is not answering ({type(e).__name__}). Start it: service/run.sh") from e
    if out.get("signed_out"):
        raise SignedOut(out.get("error") or "Signed out")
    if not out.get("ok"):
        raise Down(out.get("error") or "service error")
    return out["result"]
