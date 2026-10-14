#!/bin/sh
# Run only on mini-s1. Capture failure never publishes a restic snapshot.
set -eu
umask 077
if [ "$#" -ne 1 ] || [ ! -f "$1" ] || [ -L "$1" ]; then
    echo "Provide one private regular configuration file." >&2
    exit 2
fi
case "$(stat -c '%a' "$1")" in 400|600) ;; *) exit 2 ;; esac
test "$(stat -c '%u' "$1")" = "$(id -u)" || exit 2
# Trusted operator-owned file, not downloaded or stored in Git.
. "$1"
: "${RESTIC_REPOSITORY:?}" "${RESTIC_PASSWORD_FILE:?}" "${SSH_TARGET:?}" "${SSH_CONFIG:?}" "${REMOTE_COMMAND:?}"
case "$RESTIC_REPOSITORY" in /*) ;; *) echo "Use an absolute local repository on mini-s1." >&2; exit 2 ;; esac
if [ ! -f "$RESTIC_PASSWORD_FILE" ] || [ -L "$RESTIC_PASSWORD_FILE" ]; then exit 2; fi
case "$(stat -c '%a' "$RESTIC_PASSWORD_FILE")" in 400|600) ;; *) exit 2 ;; esac
test "$(stat -c '%u' "$RESTIC_PASSWORD_FILE")" = "$(id -u)" || exit 2
unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
directory=$(mktemp -d /var/tmp/tervo-pull.XXXXXXXX)
trap 'rm -rf -- "$directory"' EXIT
trap 'exit 1' HUP INT TERM
ssh -F "$SSH_CONFIG" -o BatchMode=yes -o StrictHostKeyChecking=yes \
    "$SSH_TARGET" "$REMOTE_COMMAND" > "$directory/tervo.tar"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$script_dir/snapshot.py" verify --bundle "$directory/tervo.tar"
# restic commits an encrypted, authenticated snapshot atomically.
restic backup --stdin --stdin-filename tervo.tar --host tervo-vps --tag tervo \
    < "$directory/tervo.tar"
restic check
if [ "${APPLY_RETENTION:-0}" = 1 ]; then
    restic forget --host tervo-vps --tag tervo --group-by host,tags \
        --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
fi
