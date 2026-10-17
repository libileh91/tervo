"""INT-129: explicit Compose release, immutable rescue images, conservative rollback.

No Git checkout, seed, downgrade, volume deletion or Docker prune is performed.
Private resolved Compose files live only in the operator's state directory.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import snapshot


def run(command, *, capture=False, **kwargs):
    return subprocess.run(command, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None, **kwargs).stdout


def private_directory(path):
    path = Path(path).resolve()
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise RuntimeError("Release state must be outside a Git checkout.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_mode & 0o077 or path.stat().st_uid != os.geteuid():
        raise RuntimeError("Release state must be private and operator-owned.")
    return path


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as target:
        json.dump(value, target)
    temporary.chmod(0o600)
    temporary.replace(path)


def runtime_model(model):
    # x-* fields are authoring extensions, not runtime Compose resources.
    return {key: value for key, value in model.items() if not key.startswith("x-")}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def smoke(compose, model):
    import http.client
    for service, path in (("backend", "/health/ready"), ("frontend", "/health"), ("frontend", "/login")):
        port = model["services"][service]["ports"][0]
        if port["host_ip"] != "127.0.0.1":
            raise RuntimeError("Only loopback HTTP publication is supported.")
        connection = http.client.HTTPConnection("127.0.0.1", int(port["published"]), timeout=10)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            data = response.read()
            if response.status != 200 or not data:
                raise RuntimeError("HTTP readiness/smoke failed.")
        finally:
            connection.close()
    print("PASS: backend readiness, frontend health and login page", flush=True)


def schema_hash(compose):
    text = run(compose + ["exec", "-T", "postgres", "sh", "-c",
        'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only '
        '--no-owner --no-acl --no-comments --restrict-key=tervoReleaseSchema'],
        capture=True)
    head = run(compose + ["exec", "-T", "postgres", "sh", "-c",
        'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At'],
        capture=True, input="SELECT string_agg(version_num, ',' ORDER BY version_num) FROM public.alembic_version;")
    return hashlib.sha256((text + "\nALEMBIC:" + head).encode()).hexdigest()


@contextmanager
def frozen_console(identifier, checkout):
    state = json.loads(run(["docker", "inspect", "--format",
        '{"running":{{json .State.Running}},"image":{{json .Config.Image}},'
        '"mounts":{{json .Mounts}}}', identifier], capture=True))
    if not state["image"].startswith("louislam/dockge:1.5.0@sha256:"):
        raise RuntimeError("The console must be the pinned official Dockge image.")
    if not any(m["Source"] == m["Destination"]
               and Path(checkout).is_relative_to(m["Source"]) for m in state["mounts"]):
        raise RuntimeError("Dockge must see the full checkout at the identical absolute path.")
    if state["running"]:
        processes = run(["docker", "top", identifier, "-eo", "pid,args"], capture=True)
        if re.search(r"docker compose .*\b(up|build|pull|stop|restart|down|run|create|rm)\b", processes):
            raise RuntimeError("Finish the console's Compose operation before release.")
        run(["docker", "stop", identifier], capture=True)
    control = {"restore": True}
    try:
        yield control
    finally:
        if state["running"] and control["restore"]:
            run(["docker", "start", identifier], capture=True)
        elif state["running"]:
            print("Console remains frozen; reconcile Git/env with the active rescue record before restart.", flush=True)


def configuration(args):
    checkout = Path(args.checkout).resolve(strict=True)
    env_file = Path(args.env_file).absolute()
    if checkout.name != args.project or env_file != checkout / "deploy/.env":
        raise RuntimeError("Use the stack folder name as project and its explicit deploy/.env.")
    if (checkout / ".env").exists() and (checkout / ".env").read_bytes().strip():
        raise RuntimeError("A root .env would be a second environment source.")
    compose = ["docker", "compose", "--env-file", str(env_file), "-p", args.project,
               "-f", str(checkout / "deploy/docker-compose.yml")]
    print("STEP: validate the private environment and explicit CLI model", flush=True)
    run(["sh", str(checkout / "deploy/validate-env.sh"), str(env_file)])
    direct = runtime_model(json.loads(run(compose + ["--profile", "tools", "config", "--format", "json"], capture=True)))
    # This checks these two local CLI entry points, not general Dockge compatibility.
    print("STEP: compare the local include and explicit CLI models in memory", flush=True)
    wrapper = runtime_model(json.loads(run(["docker", "compose", "-f", str(checkout / "compose.yaml"),
        "--profile", "tools", "config", "--format", "json"], cwd=checkout, capture=True)))
    if direct != wrapper:
        raise RuntimeError("Dockge wrapper and explicit CLI configuration differ; adoption blocked.")
    return checkout, compose, direct


def saved_command(args, release_id):
    if not re.fullmatch(r"[0-9a-f]{12}-[0-9a-f]{12}", release_id):
        raise RuntimeError("Invalid release record ID.")
    root = Path(args.state_dir) / release_id
    record = json.loads((root / "record.json").read_text())
    if record["project"] != args.project:
        raise RuntimeError("Release record belongs to a different project.")
    model_path = root / "compose.json"
    if model_path.stat().st_mode & 0o077 or model_path.is_symlink():
        raise RuntimeError("Saved Compose configuration must be private.")
    model = json.loads(model_path.read_text())
    if digest(model) != record["saved_config"]:
        raise RuntimeError("Saved rescue configuration was modified.")
    for image in record["images"].values():
        run(["docker", "image", "inspect", image], capture=True)
    return record, model, ["docker", "compose", "-p", args.project, "-f", str(model_path)]


def rollback(args, live_compose, release_id):
    record, model, command = saved_command(args, release_id)
    if schema_hash(live_compose) != record["schema"]:
        raise RuntimeError("Schema differs: rollback blocked; keep maintenance and plan roll-forward.")
    # PostgreSQL stays on its current image/volume; only the HTTP services change.
    run(command + ["up", "-d", "--no-build", "--no-deps", "--wait", "--wait-timeout", "120",
                   "backend", "frontend"])
    smoke(command, model)
    write_json(Path(args.state_dir) / "current.json", {"release_id": release_id})
    print("PASS: exact rescue image IDs restored; database unchanged", flush=True)


def deploy(args, checkout, compose, model, lock):
    revision = run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture=True).strip()
    wanted = run(["git", "-C", str(checkout), "rev-parse", args.revision + "^{commit}"], capture=True).strip()
    if revision != wanted or run(["git", "-C", str(checkout), "status", "--porcelain"], capture=True).strip():
        raise RuntimeError("Deploy requires the requested commit and a clean checkout.")
    if model["services"]["backend"]["build"]["args"]["VCS_REF"] != revision:
        raise RuntimeError("TERVO_VCS_REF does not match the source commit.")
    current_file = Path(args.state_dir) / "current.json"
    previous_id = json.loads(current_file.read_text())["release_id"] if current_file.exists() else None
    recovering = args.recover_from is not None
    if recovering:
        if not re.fullmatch(r"[0-9a-f]{12}-[0-9a-f]{12}", args.recover_from):
            raise RuntimeError("Invalid failed release ID.")
        failed = json.loads((Path(args.state_dir) / args.recover_from / "failed.json").read_text())
        if (failed["project"] != args.project or not failed["schema"]
                or schema_hash(compose) != failed["schema"]):
            raise RuntimeError("Unknown database state; inspect before any roll-forward.")
        previous_id = failed["previous"]
        for service in ("backend", "frontend"):
            identifiers = run(compose + ["ps", "-a", "-q", service], capture=True).split()
            if (len(identifiers) != 1 or snapshot.docker_state(identifiers[0])["running"]
                    or run(["docker", "inspect", "--format", "{{.Image}}", identifiers[0]],
                           capture=True).strip() != failed["images"][service]):
                raise RuntimeError("Recovery requires the recorded failed candidate stopped.")
    elif previous_id:
        previous, previous_model, previous_command = saved_command(args, previous_id)
        for service in ("backend", "frontend"):
            identifiers = run(compose + ["ps", "-a", "-q", service], capture=True).split()
            if len(identifiers) != 1 or run(["docker", "inspect", "--format", "{{.Image}}",
                identifiers[0]], capture=True).strip() != previous["images"][service]:
                raise RuntimeError("Running image drift detected; reconcile before release.")
        if previous["revision"] == revision and previous["config"] == digest(model):
            if schema_hash(compose) != previous["schema"]:
                raise RuntimeError("Schema drift detected; reconcile before release.")
            run(previous_command + ["up", "-d", "--no-build", "--no-deps", "--wait",
                                    "--wait-timeout", "120", "backend", "frontend"])
            smoke(previous_command, previous_model)
            print("Already released; no rebuild or migration", flush=True)
            return
    else:
        containers = run(compose + ["ps", "-a", "-q"], capture=True).strip()
        volumes = run(["docker", "volume", "ls", "-q", "--filter",
                      "label=com.docker.compose.project=" + args.project], capture=True).strip()
        if containers or volumes:
            raise RuntimeError("First release requires a new project with no existing data volumes.")

    print("STEP: build once while the previous API is still available", flush=True)
    run(compose + ["build", "backend", "frontend"], timeout=180)
    images = {}
    for service in ("backend", "frontend"):
        image = model["services"][service]["image"]
        label = run(["docker", "image", "inspect", "--format",
            '{{index .Config.Labels "org.opencontainers.image.revision"}}', image], capture=True).strip()
        if label != revision:
            raise RuntimeError("Image source label does not match the commit.")
        images[service] = run(["docker", "image", "inspect", "--format", "{{.Id}}", image], capture=True).strip()
    release_id = revision[:12] + "-" + uuid.uuid4().hex[:12]
    root = Path(args.state_dir) / release_id
    root.mkdir(mode=0o700)
    for service, image in images.items():
        run(["docker", "tag", image, f"tervo-{service}:rescue-{release_id}"], capture=True)
    run(compose + ["up", "-d", "--wait", "--wait-timeout", "120", "postgres"])
    try:
        run(compose + ["stop", "backend", "frontend"])
        # `create` never starts services; unlike `up`, it has no --no-deps flag.
        run(compose + ["create", "--no-build", "backend", "frontend"])
        if previous_id:
            with (root / "before-migration.tar").open("wb") as output:
                subprocess.run([sys.executable, args.snapshot_tool, "capture",
                    "--compose", str(checkout / "deploy/docker-compose.yml"),
                    "--env-file", args.env_file, "--project", args.project,
                    "--allow-maintenance", "--lock-file", args.lock_file,
                    "--lock-fd", str(lock.fileno())], stdout=output, check=True,
                    pass_fds=(lock.fileno(),))
            manifest = snapshot.verify(root / "before-migration.tar")
            if manifest["source_project"] != args.project:
                raise RuntimeError("Backup belongs to another project.")
        print("STEP: migrate, grant and check before starting HTTP services", flush=True)
        run(compose + ["run", "--rm", "-T", "--no-deps", "migrate"])
        run(compose + ["exec", "-T", "postgres", "sh", "-c",
            'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/tervo/app-grants.sql'])
        schema = schema_hash(compose)
        rescue = json.loads(json.dumps(model))
        for service in ("backend", "frontend", "migrate"):
            rescue["services"][service].pop("build", None)
            rescue["services"][service]["image"] = images["backend" if service == "migrate" else service]
        write_json(root / "compose.json", rescue)
        command = ["docker", "compose", "-p", args.project, "-f", str(root / "compose.json")]
        run(command + ["up", "-d", "--no-build", "--no-deps", "--wait", "--wait-timeout", "120",
                       "backend", "frontend"])
        smoke(command, rescue)
        write_json(root / "record.json", {"project": args.project, "revision": revision,
            "images": images, "schema": schema, "config": digest(model), "saved_config": digest(rescue)})
        write_json(current_file, {"release_id": release_id})
        print("PASS: release " + release_id, flush=True)
    except Exception:
        # No failed candidate remains publicly usable, even when rollback is blocked.
        run(compose + ["stop", "backend", "frontend"])
        try:
            failed_schema = schema_hash(compose)
        except subprocess.CalledProcessError:
            failed_schema = None
        write_json(root / "failed.json", {"project": args.project, "revision": revision,
            "images": images, "schema": failed_schema, "previous": previous_id})
        print("Failed candidate record: " + release_id, flush=True)
        if previous_id and not recovering:
            rollback(args, compose, previous_id)
        raise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("deploy", "rollback"))
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--lock-file", default="/run/lock/tervo-operations.lock")
    parser.add_argument("--dockge-container", required=True)
    parser.add_argument("--console-idle-confirmed", action="store_true", required=True)
    parser.add_argument("--maintenance-confirmed", action="store_true", required=True,
                        help="Public access and other SQL/Docker writers are held for this operation")
    parser.add_argument("--revision")
    parser.add_argument("--release-id")
    parser.add_argument("--recover-from", help="Explicit failed candidate record for controlled roll-forward")
    parser.add_argument("--snapshot-tool", default=str(Path(__file__).with_name("snapshot.py")))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]+", args.project):
        parser.error("Use a valid explicit project name.")
    if args.operation == "deploy" and not args.revision or args.operation == "rollback" and not args.release_id:
        parser.error("Deploy requires --revision; rollback requires --release-id.")
    try:
        args.state_dir = str(private_directory(args.state_dir))
        lock_fd = os.open(args.lock_file, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            checkout, compose, model = configuration(args)
            print("STEP: check and freeze the private Dockge console", flush=True)
            with frozen_console(args.dockge_container, checkout) as console:
                try:
                    if args.operation == "deploy":
                        deploy(args, checkout, compose, model, lock)
                    else:
                        console["restore"] = False
                        rollback(args, compose, args.release_id)
                except Exception:
                    console["restore"] = False
                    raise
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError, KeyError) as error:
        if isinstance(error, RuntimeError):
            message = str(error)
        elif isinstance(error, subprocess.CalledProcessError):
            message = " ".join(error.cmd[:2]) + f" exited with code {error.returncode}"
        else:
            message = type(error).__name__
        print("Release failed: " + message + ". No database downgrade or restore performed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
