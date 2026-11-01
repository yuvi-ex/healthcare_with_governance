# Shared settings for the shell scripts. Source it, do not run it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# config.local.env (your overrides, git-ignored) wins over config.env; an environment variable of the same name wins over both
for f in "$ROOT/config.local.env" "$ROOT/config.env"; do
  [[ -f "$f" ]] || continue
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" == \#* ]] && continue
    [[ -n "${!k:-}" ]] || export "$k=$v"
  done < "$f"
done
BASE="$HC_BASE_DIR"; [[ "$BASE" == /* ]] || BASE="$(cd "$ROOT" && cd "$BASE" 2>/dev/null && pwd || echo "$ROOT/$HC_BASE_DIR")"
PY="$ROOT/.venv/bin/python"
SVC="http://127.0.0.1:$HC_GOV_SERVICE_PORT"
APP_URL="http://127.0.0.1:$HC_DASH_PORT/apps/$HC_GOV_APP"
ok()  { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }
say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[0;31merror: %s\033[0m\n' "$*" >&2; exit 1; }
