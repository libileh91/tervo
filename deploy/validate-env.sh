#!/bin/sh
# Validate private file permissions and Compose interpolation without logging values.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: sh deploy/validate-env.sh /absolute/path/to/private.env" >&2
    exit 2
fi
env_file=$1
if [ ! -f "$env_file" ] || [ -L "$env_file" ]; then
    echo "A regular private environment file is required (no symlink)." >&2
    exit 2
fi
case "$(stat -c '%a' -- "$env_file")" in
    400|600) ;;
    *) echo "Environment permissions must be 400 or 600." >&2; exit 2 ;;
esac
# Shell exports override --env-file in Compose. Refuse ambiguity rather than
# silently validate a different source; Docker client settings remain intact.
for name in TERVO_IMAGE_TAG TERVO_VCS_REF TERVO_DB_NAME TERVO_DB_USER \
    TERVO_DB_PASSWORD SECRET_KEY FRONTEND_ORIGIN VITE_API_BASE_URL \
    BACKEND_PORT FRONTEND_PORT; do
    if printenv "$name" >/dev/null 2>&1; then
        echo "Unset exported $name before using the explicit environment file." >&2
        exit 2
    fi
done
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose --env-file "$env_file" -f "$script_dir/docker-compose.yml" config --quiet
python3 - "$env_file" "$script_dir/docker-compose.yml" <<'PY'
import json
import re
import subprocess
import sys

raw = subprocess.check_output([
    "docker", "compose", "--env-file", sys.argv[1], "-f", sys.argv[2],
    "config", "--format", "json",
])
# This remains in memory; never print a resolved environment or secret.
config = json.loads(raw)
revision = config["services"]["backend"]["build"]["args"]["VCS_REF"]
if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision):
    raise SystemExit("TERVO_VCS_REF must be a full hexadecimal source SHA.")
PY
echo "Environment permissions and Compose configuration valid."
