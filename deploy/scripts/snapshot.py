"""INT-128: coherent bundle capture and checksum verification, no in-place restore.

The CLI capture requires an explicitly authorized maintenance window.
Bundle stdout is private binary data, never a log to paste into chat.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile


FILES = ("database.dump", "uploads.tar", "private.env", "caddy.service",
         "dockge-compose.yaml", "caddy-config.tar", "caddy-state.tar", "dockge-data.tar",
         "source-project.txt")


def call(command, **kwargs):
    return subprocess.run(command, check=True, stderr=subprocess.PIPE, **kwargs)


def docker_state(identifier):
    return json.loads(call(["docker", "inspect", "--format",
        '{"running":{{json .State.Running}},"mounts":{{json .Mounts}}}', identifier],
        stdout=subprocess.PIPE, text=True).stdout)


@contextmanager
def stopped_containers(identifiers):
    restart = []
    try:
        for identifier in identifiers:
            if docker_state(identifier)["running"]:
                restart.append(identifier)
                call(["docker", "stop", identifier], stdout=subprocess.DEVNULL)
        yield
    finally:
        failures = []
        for identifier in reversed(restart):
            try:
                call(["docker", "start", identifier], stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                failures.append(identifier)
        if failures:
            raise RuntimeError("Service recovery failed; inspect the maintenance state.")


@contextmanager
def host_services(dockge_compose):
    state = call(["systemctl", "show", "caddy.service", "-p", "ActiveState", "--value"],
                 stdout=subprocess.PIPE, text=True).stdout.strip()
    if state not in ("active", "inactive"):
        raise RuntimeError("Caddy must be active or inactive before capture.")
    dockge = call(["docker", "compose", "-p", "dockge", "-f", str(dockge_compose),
                   "ps", "-a", "-q", "dockge"], stdout=subprocess.PIPE, text=True).stdout.split()
    if len(dockge) != 1:
        raise RuntimeError("Exactly one Dockge container is required.")
    with stopped_containers(dockge):
        try:
            if state == "active":
                call(["systemctl", "stop", "caddy.service"], stdout=subprocess.DEVNULL)
            yield
        finally:
            if state == "active":
                call(["systemctl", "start", "caddy.service"], stdout=subprocess.DEVNULL)


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def capture(args, pause_host):
    """pause_host is explicit: production stops services; tests use offline fixtures."""
    lock_fd = os.open(args.lock_file, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _capture_locked(args, pause_host)


def _capture_locked(args, pause_host):
    raw_env_file = Path(args.env_file)
    compose_file = Path(args.compose).resolve(strict=True)
    validator = compose_file.parent / "validate-env.sh"
    call(["sh", str(validator), str(raw_env_file), str(compose_file)], stdout=subprocess.DEVNULL)
    env_file = raw_env_file.resolve(strict=True)
    endpoint = os.environ.get("DOCKER_HOST") or call(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        stdout=subprocess.PIPE, text=True).stdout.strip()
    if not endpoint.startswith("unix://"):
        raise RuntimeError("Capture requires the local Unix Docker daemon.")
    compose = ["docker", "compose", "--env-file", str(env_file),
               "-f", str(compose_file), "-p", args.project]
    backend = call(compose + ["ps", "-a", "-q", "backend"],
                   stdout=subprocess.PIPE, text=True).stdout.split()
    if len(backend) != 1:
        raise RuntimeError("Exactly one backend container is required.")
    mounts = docker_state(backend[0])["mounts"]
    upload_volume = [mount["Name"] for mount in mounts
                     if mount["Type"] == "volume" and mount["Destination"] == "/app/uploads"]
    if len(upload_volume) != 1:
        raise RuntimeError("Expected one named uploads volume at /app/uploads.")
    configs = {"caddy-config.tar": Path(args.caddy_config),
               "caddy-state.tar": Path(args.caddy_state),
               "dockge-data.tar": Path(args.dockge_data)}
    for path in configs.values():
        if not path.is_dir() or path.is_symlink():
            raise RuntimeError("Configuration sources must be explicit regular directories.")
    with tempfile.TemporaryDirectory(prefix="tervo-snapshot-", dir="/var/tmp") as directory:
        root = Path(directory)
        # No output until capture AND service recovery both succeed.
        with stopped_containers(backend), pause_host:
            with (root / "database.dump").open("wb") as output:
                call(compose + ["exec", "-T", "postgres", "sh", "-c",
                    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                    '--format=custom --no-owner --no-acl'], stdout=output)
            with (root / "uploads.tar").open("wb") as output:
                call(compose + ["run", "--rm", "-T", "--no-deps",
                    "-v", upload_volume[0] + ":/app/uploads:ro",
                    "backend", "tar", "-C", "/app", "-cf", "-", "uploads"], stdout=output)
            shutil.copy2(env_file, root / "private.env")
            shutil.copy2(args.caddy_unit_file, root / "caddy.service")
            shutil.copy2(args.dockge_compose, root / "dockge-compose.yaml")
            for name, source in configs.items():
                with tarfile.open(root / name, "w") as archive:
                    archive.add(source, arcname=source.name)
        (root / "source-project.txt").write_text(args.project + "\n")
        (root / "SHA256SUMS").write_text(
            "".join(f"{sha256(root / name)}  {name}\n" for name in FILES))
        # Staged bytes are immutable after the maintenance window.
        with tarfile.open(fileobj=args.output, mode="w|") as archive:
            for name in (*FILES, "SHA256SUMS"):
                archive.add(root / name, arcname=name)


def verify(bundle):
    with tarfile.open(bundle, "r:") as archive:
        members = archive.getmembers()
        if (len(members) != len(FILES) + 1
                or {m.name for m in members} != {*FILES, "SHA256SUMS"}
                or not all(m.isfile() for m in members)):
            raise RuntimeError("Unexpected bundle members.")
        hashes = {}
        for line in archive.extractfile("SHA256SUMS").read().decode("ascii").splitlines():
            digest, separator, name = line.partition("  ")
            if (not separator or name not in FILES or name in hashes or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                raise RuntimeError("Invalid checksum manifest.")
            hashes[name] = digest
        if set(hashes) != set(FILES):
            raise RuntimeError("Incomplete checksum manifest.")
        for name in FILES:
            with archive.extractfile(name) as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != hashes[name]:
                raise RuntimeError("Bundle checksum mismatch.")
        return {"source_project": archive.extractfile("source-project.txt").read().decode().strip(),
                "sha256": hashes}


def unpack(bundle, directory):
    verify(bundle)
    destination = Path(directory).resolve()
    if any((parent / ".git").exists() for parent in (destination, *destination.parents)):
        raise RuntimeError("Never unpack private configuration inside a Git checkout.")
    destination.mkdir(mode=0o700)  # Never overwrite an existing restore directory.
    with tarfile.open(bundle, "r:") as archive:
        archive.extractall(destination, filter="data")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("capture")
    create.add_argument("--compose", required=True)
    create.add_argument("--env-file", required=True)
    create.add_argument("--project", required=True)
    create.add_argument("--allow-maintenance", action="store_true", required=True)
    create.add_argument("--lock-file", default="/run/lock/tervo-operations.lock")
    create.add_argument("--caddy-config", default="/etc/caddy")
    create.add_argument("--caddy-state", default="/var/lib/caddy")
    create.add_argument("--caddy-unit-file", default="/etc/systemd/system/caddy.service")
    create.add_argument("--dockge-data", default="/opt/dockge/data")
    create.add_argument("--dockge-compose", default="/opt/dockge/compose.yaml")
    for name in ("verify", "unpack"):
        command = commands.add_parser(name)
        command.add_argument("--bundle", required=True)
        if name == "unpack":
            command.add_argument("--directory", required=True)
    args = parser.parse_args()

    def interrupt(signum, frame):
        raise InterruptedError("Capture interrupted.")

    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupt)
    try:
        if args.command == "capture":
            if os.geteuid() != 0:
                raise RuntimeError("Capture requires privileged access to private configuration.")
            if sys.stdout.isatty():
                raise RuntimeError("Never send private bundle data to a terminal.")
            output_stat = os.fstat(sys.stdout.fileno())
            if stat.S_ISREG(output_stat.st_mode):
                output_path = Path(os.readlink("/proc/self/fd/1")).resolve()
                if (output_stat.st_mode & 0o077
                        or any((p / ".git").exists() for p in output_path.parents)):
                    raise RuntimeError("Bundle output must be private and outside Git.")
            args.output = sys.stdout.buffer
            capture(args, host_services(Path(args.dockge_compose)))
        elif args.command == "verify":
            verify(args.bundle)
            print("Bundle checksums valid.")
        else:
            unpack(args.bundle, args.directory)
    except (OSError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError,
            ValueError, KeyError) as error:
        # No SQL, environment, credentials or subprocess stderr in shared output.
        print(f"Snapshot failed ({type(error).__name__}); inspect service states.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
