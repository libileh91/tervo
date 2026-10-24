#!/bin/sh
# INT-130 - privileged entry point for the GitHub Actions release job.
#
# This file is the source of the installed /usr/local/sbin/tervo-ci-release.
# The installed copy is root-owned and must be refreshed by the operator when
# this file changes; it is never updated by a release or by the CI account.
#
# sudoers allows this exact command without arguments. The expected commit is
# read from stdin, so no sudoers argument wildcard is needed:
#
#   printf '%s\n' "$GITHUB_SHA" | ssh <ci>@<vps>
#
# The SSH key of the CI account is restricted to this command in
# authorized_keys. The wrapper only releases a commit that is HEAD after a
# fast-forward of origin/main, with a clean checkout; build, migration,
# backup, smoke and rollback stay in release.py. No second orchestration is
# introduced here. The checkout may be on an attached main branch or detached
# at the released SHA (the documented immutable release state).
set -eu

checkout=/opt/stacks/tervo
state_dir=/var/lib/tervo/state
lock=/run/lock/tervo-operations.lock

# This wrapper is specific to the VPS host and must run as root.
test "$(hostname)" = 22565
test "$(id -u)" = 0

revision=$(head -n 1)
case "$revision" in
  ""|*[!0-9a-f]*) echo "Invalid revision." >&2; exit 2 ;;
esac
[ "${#revision}" -eq 40 ] || { echo "Invalid revision length." >&2; exit 2; }

# Clean checkout only; main may be attached or detached at a released SHA.
test -z "$(git -C "$checkout" status --porcelain)"

# Same lock as release.py: never pull the checkout under a running release.
umask 077
exec 9>>"$lock"
flock -n 9 || { echo "Another release operation holds the lock." >&2; exit 1; }
export GIT_TERMINAL_PROMPT=0
git -C "$checkout" pull --ff-only origin main
if [ "$(git -C "$checkout" rev-parse HEAD)" != "$revision" ]; then
  echo "Server HEAD does not match the requested commit." >&2
  exit 1
fi
exec 9>&-

# The private env pins both the image tag and the build VCS_REF to the released
# commit. Only these two lines change; mode and owner are preserved.
env_file=$checkout/deploy/.env
test -f "$env_file"
test ! -L "$env_file"
mode=$(stat -c '%a' "$env_file")
owner=$(stat -c '%u:%g' "$env_file")
case "$mode" in
  400|600) ;;
  *) echo "deploy/.env must be mode 400 or 600." >&2; exit 1 ;;
esac
sed -i \
  -e "s|^TERVO_IMAGE_TAG=.*|TERVO_IMAGE_TAG=$revision|" \
  -e "s|^TERVO_VCS_REF=.*|TERVO_VCS_REF=$revision|" \
  "$env_file"
chmod "$mode" "$env_file"
chown "$owner" "$env_file"
grep -qx "TERVO_IMAGE_TAG=$revision" "$env_file"
grep -qx "TERVO_VCS_REF=$revision" "$env_file"

# Fixed arguments only: the CI account cannot choose paths, project or flags.
exec python3 "$checkout/deploy/scripts/release.py" deploy \
  --checkout "$checkout" \
  --env-file "$env_file" \
  --project tervo \
  --state-dir "$state_dir" \
  --lock-file "$lock" \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed \
  --revision "$revision"
