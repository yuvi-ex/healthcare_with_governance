"""Settings for the access-on-request demo: config.env here, overridden by environment variables. The S3 settings come
from the hospital-chain build this demo sits on (HC_BASE_DIR/config.env), so both read the same bucket with the same key.

    import hcconfig as C;  C.EXA_DSN, C.SERVICE_PORT, C.exasol() ...
"""
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read(path):
    vals = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def _path(v, base):
    p = Path(v).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


_ENV = {k: v for k, v in os.environ.items() if k.startswith("HC_")}
_V = {**_read(ROOT / "config.env"), **_ENV}
BASE_DIR = _path(_V["HC_BASE_DIR"], ROOT)
_B = {**_read(BASE_DIR / "config.env"), **_ENV}           # the hospital-chain build's settings

EXA_HOST, EXA_PORT = _V["HC_EXA_HOST"], int(_V["HC_EXA_PORT"])
EXA_DSN = f"{EXA_HOST}:{EXA_PORT}"
EXAPUMP_PROFILE = _V["HC_EXAPUMP_PROFILE"]
SERVICE_PORT = int(_V["HC_GOV_SERVICE_PORT"])
SERVICE_URL = f"http://127.0.0.1:{SERVICE_PORT}"
APP, DASH_PORT, DASH_PROFILE = _V["HC_GOV_APP"], int(_V["HC_DASH_PORT"]), _V["HC_DASH_PROFILE"]
ANTHROPIC_KEY_FILE = _path(_V["HC_ANTHROPIC_KEY_FILE"], ROOT)
CLAUDE_MODEL = _V["HC_CLAUDE_MODEL"]
S3_BUCKET = _B.get("HC_S3_BUCKET", "")
S3_REGION = _B.get("HC_S3_REGION", "ap-south-1")
S3_KEY_FILE = _path(_B.get("HC_S3_KEY_FILE", "secrets/s3_reader_key.json"), BASE_DIR)
USERS_FILE = ROOT / "secrets" / "hc_users.env"


def exasol(**kw):
    """An admin session from the exapump profile (Exasol Personal uses a self-signed certificate)."""
    import pyexasol
    c = tomllib.load(open(Path.home() / ".exapump" / "config.toml", "rb"))[EXAPUMP_PROFILE]
    return pyexasol.connect(dsn=f"{c['host']}:{c['port']}", user=c["user"], password=c["password"],
                            encryption=True, websocket_sslopt={"cert_reqs": 0}, **kw)
