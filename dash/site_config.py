"""Where the console finds the access-desk service. In a checkout this reads config.env through hcconfig.py; dash-server
runs its own copy of the app, outside this repository, so dash/deploy.py uploads a frozen version with the value filled in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcconfig as _C  # noqa: E402

SERVICE_URL = _C.SERVICE_URL
