"""INT-125: clean-source build and disposable local Compose availability check.

Uses fictitious credentials and only its uniquely named containers/volumes.
Never points at an existing DB, performs a production release or prunes Docker.
"""

import argparse
import base64
import contextlib
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import uuid


def run(args, *, capture=False, env=None, input_data=None):
    return subprocess.run(
        args, check=True, text=True, env=env, input=input_data,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    ).stdout


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def get(port, path, *, origin=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path, headers={"Origin": origin} if origin else {})
        response = connection.getresponse()
        return response.status, response.read(), {
            name.lower(): value for name, value in response.getheaders()
        }
    finally:
        connection.close()


def wait_for(check, description, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if check():
                print(f"PASS: {description}", flush=True)
                return
        except (OSError, http.client.HTTPException):
            pass
        time.sleep(1)
    raise RuntimeError(f"Timeout: {description}")


def check_backup(root, compose, env_file, child_env, project, restic):
    """INT-128: real PG/restic restore, offline configuration fixtures, no real SSH."""
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location("snapshot", root / "deploy/scripts/snapshot.py")
    snapshot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snapshot)
    photo = (root / "backend/tests/test_photo.jpg").read_bytes()
    compose("exec", "-T", "backend", "python", "-c", """
import asyncio,base64,hashlib,sys
from datetime import date,datetime
from pathlib import Path
from weasyprint import HTML
from app.model_registry import load_models
from app.core.database import async_session
from app.modules.customers.models import Client,Site
from app.modules.interventions.models.intervention import Intervention
from app.modules.interventions.models.photo import Photo
from app.modules.reports.models import Report,ReportVersion
load_models()
photo=base64.b64decode(sys.stdin.read())
pdf=HTML(string='<p>INT128 restore fixture</p>').write_pdf()
async def create():
    async with async_session() as db, db.begin():
        client=Client(full_name='INT128_CLIENT',phone='fictitious',address='fictitious')
        db.add(client); await db.flush()
        site=Site(client_id=client.id,name='INT128_SITE',address='fictitious')
        db.add(site); await db.flush()
        intervention=Intervention(site_id=site.id,title='INT128',scheduled_date=date.today())
        db.add(intervention); await db.flush()
        db.add(Photo(intervention_id=intervention.id,usage='BEFORE',file_path='photos/int128.jpg'))
        report=Report(intervention_id=intervention.id)
        db.add(report); await db.flush()
        db.add(ReportVersion(report_id=report.id,version=1,pdf=pdf,
            sha256=hashlib.sha256(pdf).hexdigest(),size=len(pdf),
            generated_at=datetime(2026,1,1,12),transmitted_at=datetime(2026,1,2,12)))
        Path('/app/uploads/photos/int128.jpg').write_bytes(photo)
asyncio.run(create())
""", input_data=base64.b64encode(photo).decode())
    sql = """SELECT c.id,s.id,i.id,p.id,r.id,v.id,encode(v.pdf,'hex'),v.sha256,v.size,
v.generated_at,v.transmitted_at
FROM client c JOIN site s ON s.client_id=c.id JOIN intervention i ON i.site_id=s.id
JOIN photo p ON p.intervention_id=i.id JOIN report r ON r.intervention_id=i.id
JOIN report_version v ON v.report_id=r.id WHERE c.full_name='INT128_CLIENT';"""

    def query(command):
        return run(command + ["exec", "-T", "postgres", "sh", "-c",
            'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -qAt'],
            env=child_env, input_data=sql, capture=True).strip()

    source_command = ["docker", "compose", "-p", project, "--env-file", str(env_file),
                      "-f", str(root / "deploy/docker-compose.yml")]
    expected = query(source_command)
    fields = expected.split("|")
    assert hashlib.sha256(bytes.fromhex(fields[6])).hexdigest() == fields[7]
    assert len(bytes.fromhex(fields[6])) == int(fields[8])
    config_dirs = [root / name for name in ("caddy-config", "caddy-state", "dockge-data")]
    for directory in config_dirs:
        directory.mkdir()
    (config_dirs[0] / "Caddyfile").write_text("fixture HTTP only")
    (config_dirs[1] / "state").write_bytes(b"fictitious-private-state")
    with sqlite3.connect(config_dirs[2] / "dockge.db") as db:
        db.execute("CREATE TABLE fixture (value TEXT)")
        db.execute("INSERT INTO fixture VALUES ('fictitious-auth-state')")
    private_sources = {path: snapshot.sha256(path) for directory in config_dirs for path in directory.iterdir()}
    unit = root / "caddy.service"
    unit.write_text("fictitious unit")
    dockge_compose = root / "dockge-fixture.yaml"
    dockge_compose.write_text("fictitious compose")
    bundle = root / "bundle.tar"
    with bundle.open("wb") as output:
        snapshot.capture(SimpleNamespace(
            env_file=env_file, compose=root / "deploy/docker-compose.yml", project=project,
            caddy_config=config_dirs[0], caddy_state=config_dirs[1], dockge_data=config_dirs[2],
            caddy_unit_file=unit, dockge_compose=dockge_compose,
            lock_file=root / "backup.lock", output=output), contextlib.nullcontext())
    assert query(source_command) == expected
    assert all(snapshot.sha256(path) == digest for path, digest in private_sources.items())

    password_file = root / "restic-password"
    password_file.write_text(uuid.uuid4().hex)
    password_file.chmod(0o600)
    restic_env = {**child_env, "RESTIC_REPOSITORY": str(root / "restic-repo"),
                  "RESTIC_PASSWORD_FILE": str(password_file)}
    restic_env.pop("RESTIC_PASSWORD", None)
    restic_env.pop("RESTIC_PASSWORD_COMMAND", None)
    run([restic, "init"], env=restic_env, capture=True)
    tools = root / "test-tools"
    tools.mkdir()
    (tools / "restic").symlink_to(restic)
    (tools / "ssh").write_text('#!/bin/sh\nexec cat "$FAKE_BUNDLE"\n')
    (tools / "ssh").chmod(0o700)
    config = root / "mini-fixture.conf"
    config.write_text(
        f"RESTIC_REPOSITORY='{restic_env['RESTIC_REPOSITORY']}'\n"
        f"RESTIC_PASSWORD_FILE='{password_file}'\nSSH_TARGET=fictitious\n"
        "SSH_CONFIG=/fictitious\nREMOTE_COMMAND=fictitious\nAPPLY_RETENTION=1\n")
    config.chmod(0o600)
    run(["sh", str(root / "deploy/scripts/pull-backup.sh"), str(config)],
        env={**child_env, "PATH": str(tools) + ":" + child_env["PATH"], "FAKE_BUNDLE": str(bundle)},
        capture=True)
    run([restic, "check", "--read-data"], env=restic_env, capture=True)
    decrypted = root / "decrypted.tar"
    with decrypted.open("wb") as output:
        subprocess.run([restic, "dump", "latest", "/tervo.tar"], env=restic_env,
                       stdout=output, stderr=subprocess.PIPE, check=True)
    assert snapshot.sha256(decrypted) == snapshot.sha256(bundle)
    wrong_password = root / "wrong-password"
    wrong_password.write_text("wrong-fictitious-password")
    denied = subprocess.run([restic, "snapshots"],
        env={**restic_env, "RESTIC_PASSWORD_FILE": str(wrong_password)}, capture_output=True)
    assert denied.returncode != 0
    unpacked = root / "unpacked"
    snapshot.unpack(decrypted, unpacked)
    assert (unpacked / "private.env").read_bytes() == env_file.read_bytes()
    for archive_name, original in zip(
            ("caddy-config.tar", "caddy-state.tar", "dockge-data.tar"), config_dirs):
        restored = root / (archive_name + "-restore")
        restored.mkdir()
        with tarfile.open(unpacked / archive_name) as archive:
            archive.extractall(restored, filter="data")
        for path in original.iterdir():
            assert (restored / original.name / path.name).read_bytes() == path.read_bytes()

    restore_project = "tervo-int128-restore-" + uuid.uuid4().hex[:12]
    restore_command = ["docker", "compose", "-p", restore_project,
                       "--env-file", str(env_file), "-f", str(root / "deploy/docker-compose.yml")]
    try:
        run(restore_command + ["up", "-d", "--wait", "--wait-timeout", "120", "postgres"], env=child_env)
        with (unpacked / "database.dump").open("rb") as source:
            subprocess.run(restore_command + ["exec", "-T", "postgres", "sh", "-c",
                'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
                stdin=source, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        run(restore_command + ["exec", "-T", "postgres", "sh", "-c",
            'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /opt/tervo/app-grants.sql'],
            env=child_env, capture=True)
        assert query(restore_command) == expected
        with (unpacked / "uploads.tar").open("rb") as source:
            subprocess.run(restore_command + ["run", "--rm", "-T", "--no-deps", "backend", "python", "-c",
                "import sys,tarfile; tarfile.open(fileobj=sys.stdin.buffer,mode='r|').extractall('/app',filter='data')"],
                stdin=source, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        restored_photo = run(restore_command + ["run", "--rm", "-T", "--no-deps", "backend", "python", "-c",
            "import base64; from pathlib import Path; "
            "print(base64.b64encode(Path('/app/uploads/photos/int128.jpg').read_bytes()).decode())"],
            env=child_env, capture=True).strip()
        assert base64.b64decode(restored_photo) == photo
        assert query(source_command) == expected
        print("PASS: encrypted restic bundle, wrong-key refusal, relationships/photo/PDF BYTEA and private config restore; source unchanged", flush=True)
    finally:
        run(restore_command + ["down", "--volumes", "--remove-orphans"], env=child_env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Explicit Git commit/tree to export")
    parser.add_argument("--backup", action="store_true", help="Also run isolated INT-128 restore checks")
    parser.add_argument("--restic", help="Verified local restic executable for --backup")
    args = parser.parse_args()
    if args.backup and (not args.restic or not Path(args.restic).is_file()):
        parser.error("--backup requires --restic /absolute/path/to/restic")
    repo = Path(__file__).resolve().parent.parent
    endpoint = os.environ.get("DOCKER_HOST") or run(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        capture=True,
    ).strip()
    if not endpoint.startswith("unix://"):
        raise SystemExit("This check requires a local Unix Docker engine, not a remote builder.")
    revision = run(["git", "-C", str(repo), "rev-parse", args.revision], capture=True).strip()
    archive = subprocess.check_output(["git", "-C", str(repo), "archive", revision])
    project = f"tervo-int125-{uuid.uuid4().hex[:12]}"
    image_tag = f"int125-{uuid.uuid4().hex[:12]}"
    backend_port, frontend_port = free_port(), free_port()
    password = "test-only-p@ss#$/%:word"
    values = {
        "TERVO_IMAGE_TAG": image_tag,
        "TERVO_VCS_REF": revision,
        "TERVO_DB_NAME": "tervo_db",
        "TERVO_DB_ADMIN_USER": "tervo_admin",
        "TERVO_DB_ADMIN_PASSWORD": "test-only-admin-" + "x" * 32,
        "TERVO_DB_USER": "tervo_app",
        "TERVO_DB_PASSWORD": password,
        "SECRET_KEY": "test-only-key-" + "x" * 64,
        "FRONTEND_ORIGIN": "https://tervoapp.com",
        "VITE_API_BASE_URL": "https://api.tervoapp.com/api/v1",
        "BACKEND_PORT": str(backend_port),
        "FRONTEND_PORT": str(frontend_port),
    }
    child_env = os.environ.copy()
    for name in values:
        child_env.pop(name, None)  # Never let a real shell secret override test values.
    child_env["BUILDX_BUILDER"] = "default"
    temporary_root = os.environ.get("DELTA_SCRATCH_DIR")
    with tempfile.TemporaryDirectory(prefix="int125-", dir=temporary_root) as directory:
        root = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(root, filter="data")
        assert not (root / "frontend/dist").exists()
        assert not (root / "frontend/node_modules").exists()
        assert not (root / "backend/tervo.db").exists()
        env_file = root / "private.env"
        env_file.write_text("".join(f"{key}='{value}'\n" for key, value in values.items()))
        env_file.chmod(0o600)
        compose_file = root / "deploy/docker-compose.yml"

        def compose(*command, capture=False, input_data=None):
            return run([
                "docker", "compose", "--project-name", project,
                "--env-file", str(env_file), "-f", str(compose_file), *command,
            ], capture=capture, env=child_env, input_data=input_data)

        def info(service):
            identifier = compose("ps", "-a", "-q", service, capture=True).strip()
            if not identifier:
                return {}
            # No complete inspect: restrict output to state, bindings and logging.
            output = run(["docker", "inspect", "--format",
                '{"state":{{json .State}},"ports":{{json .HostConfig.PortBindings}},'
                '"logs":{{json .HostConfig.LogConfig}}}', identifier], capture=True)
            return json.loads(output)

        def healthy(service):
            return info(service).get("state", {}).get("Health", {}).get("Status") == "healthy"

        try:
            run(["sh", str(root / "deploy/validate-env.sh"), str(env_file)], env=child_env)
            polluted_env = {**child_env, "SECRET_KEY": "ambient-test-only-not-to-use"}
            rejected = subprocess.run(
                ["sh", str(root / "deploy/validate-env.sh"), str(env_file)],
                env=polluted_env, capture_output=True,
            )
            assert rejected.returncode != 0
            valid_env = env_file.read_text()
            for key in ("SECRET_KEY", "TERVO_DB_PASSWORD", "TERVO_DB_ADMIN_PASSWORD", "TERVO_VCS_REF"):
                env_file.write_text(valid_env.replace(f"{key}='{values[key]}'", f"{key}=''"))
                rejected = subprocess.run(
                    ["sh", str(root / "deploy/validate-env.sh"), str(env_file)],
                    env=child_env, capture_output=True,
                )
                assert rejected.returncode != 0
            for key, invalid in (
                ("TERVO_DB_USER", values["TERVO_DB_ADMIN_USER"]),
                ("TERVO_DB_USER", "Invalid Role"),
                ("TERVO_DB_USER", "pg_reserved"),
                ("TERVO_DB_PASSWORD", "short"),
                ("TERVO_DB_ADMIN_PASSWORD", password),
            ):
                env_file.write_text(valid_env.replace(f"{key}='{values[key]}'", f"{key}='{invalid}'"))
                rejected = subprocess.run(
                    ["sh", str(root / "deploy/validate-env.sh"), str(env_file)],
                    env=child_env, capture_output=True,
                )
                assert rejected.returncode != 0
            env_file.write_text(valid_env)
            env_file.chmod(0o644)
            rejected = subprocess.run(
                ["sh", str(root / "deploy/validate-env.sh"), str(env_file)],
                env=child_env, capture_output=True,
            )
            assert rejected.returncode != 0
            env_file.chmod(0o600)
            config = json.loads(compose("config", "--format", "json", capture=True))
            # Compose's config serializer doubles literal dollars for re-use.
            # Exact runtime values are checked separately inside the container.
            assert config["services"]["backend"]["environment"]["TERVO_DB_PASSWORD"].replace("$$", "$") == password
            assert not config["services"]["postgres"].get("ports")
            assert config["services"]["postgres"]["environment"]["POSTGRES_USER"] == values["TERVO_DB_ADMIN_USER"]
            assert "TERVO_DB_ADMIN_PASSWORD" not in config["services"]["backend"]["environment"]
            assert not any(v.get("external") for v in config["networks"].values())
            for service in ("backend", "frontend"):
                assert all(port["host_ip"] == "127.0.0.1" for port in config["services"][service]["ports"])
            print(f"PASS: clean source {revision}; private env parsing and network contract", flush=True)
            compose("build")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
            wait_for(lambda: all(healthy(s) for s in ("postgres", "backend", "frontend")),
                     "all services healthy")
            compose("exec", "-T", "backend", "python", "-c",
                    "import os,sys; assert os.environ['TERVO_DB_PASSWORD'] == sys.stdin.read(); "
                    "print('PASS: exact reserved-character credential at runtime')",
                    input_data=password)
            assert get(backend_port, "/health/ready")[0] == 200
            status, _, headers = get(backend_port, "/health/ready", origin=values["FRONTEND_ORIGIN"])
            assert status == 200 and headers.get("access-control-allow-origin") == values["FRONTEND_ORIGIN"]
            assert "access-control-allow-origin" not in get(backend_port, "/health/ready",
                                                         origin="https://unapproved.invalid")[2]
            assert get(frontend_port, "/login")[0] == 200
            assert get(frontend_port, "/health")[0] == 200
            compose("exec", "-T", "frontend", "mv", "/usr/share/nginx/html/index.html",
                    "/tmp/int125-index.html")
            assert get(frontend_port, "/health")[0] == 503
            compose("exec", "-T", "frontend", "mv", "/tmp/int125-index.html",
                    "/usr/share/nginx/html/index.html")
            assert get(frontend_port, "/health")[0] == 200
            for service in ("postgres", "backend", "frontend"):
                assert info(service)["logs"]["Config"] == {"max-file": "3", "max-size": "10m"}
            assert not info("postgres")["ports"]
            print("PASS: DB readiness, SPA, frontend health, CORS and bounded logs", flush=True)
            compose("exec", "-T", "backend", "python", "-c",
                    "from weasyprint import HTML; "
                    "assert HTML(string='<p>INT125</p>').write_pdf().startswith(b'%PDF'); "
                    "print('PASS: native PDF dependencies render an in-memory document')")
            # Full migrations only on this newly created, privately named DB.
            version_and_role = compose("exec", "-T", "postgres", "sh", "-c",
                    'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -qAt',
                    input_data="SHOW server_version; SELECT current_user, rolsuper FROM pg_roles WHERE rolname=current_user;",
                    capture=True).splitlines()
            assert version_and_role[0].startswith("17.11")
            assert version_and_role[1] == values["TERVO_DB_ADMIN_USER"] + "|t"
            compose("run", "--rm", "-T", "--no-deps", "migrate")
            compose("exec", "-T", "postgres", "sh", "-c",
                    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                    '-f /opt/tervo/app-grants.sql')

            def app_sql(sql):
                return compose("exec", "-T", "postgres", "sh", "-c",
                    'export PGPASSWORD="$TERVO_DB_PASSWORD"; '
                    'exec psql -h 127.0.0.1 -U "$TERVO_DB_USER" -d "$POSTGRES_DB" '
                    '-v ON_ERROR_STOP=1 -qAt', input_data=sql, capture=True).strip()

            assert app_sql(
                "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole, "
                "rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user;"
            ) == values["TERVO_DB_USER"] + "|f|f|f|f|f"
            app_sql(
                'INSERT INTO public."user" (username,email,hashed_password,role,is_active) '
                "VALUES ('int127_check','int127@example.test','fictitious-not-a-login','TECHNICIAN',true);"
                'UPDATE public."user" SET full_name=\'INT127 persistence\' WHERE username=\'int127_check\';'
                'INSERT INTO public."user" (username,email,hashed_password,role,is_active) '
                "VALUES ('int127_delete','delete@example.test','fictitious-not-a-login','TECHNICIAN',true);"
                'DELETE FROM public."user" WHERE username=\'int127_delete\';'
            )
            assert app_sql('SELECT full_name FROM public."user" WHERE username=\'int127_check\';') == "INT127 persistence"
            for sql in (
                "CREATE TABLE public.int127_forbidden (id integer);",
                'TRUNCATE TABLE public."user";',
                "CREATE ROLE int127_forbidden;",
                "SET ROLE " + values["TERVO_DB_ADMIN_USER"] + ";",
                "UPDATE public.alembic_version SET version_num='forbidden';",
            ):
                try:
                    app_sql(sql)
                except subprocess.CalledProcessError as error:
                    assert "permission denied" in error.stderr.lower()
                else:
                    raise AssertionError("Application role unexpectedly allowed a privileged command.")
            print("PASS: admin migrations, application CRUD/sequences, forbidden DDL/roles/TRUNCATE/version edits", flush=True)
            compose("exec", "-T", "backend", "python", "-c",
                    "from pathlib import Path; Path('/app/uploads/photos').mkdir(exist_ok=True); "
                    "Path('/app/uploads/photos/int125-check.txt').write_text('INT125_UPLOAD_CHECK')")
            assert get(backend_port, "/uploads/photos/int125-check.txt")[:2] == (
                200, b"INT125_UPLOAD_CHECK")
            compose("stop", "postgres")
            assert get(backend_port, "/health/ready")[:2] == (503, b'{"status":"not_ready"}')
            wait_for(lambda: info("backend")["state"]["Health"]["Status"] == "unhealthy",
                     "DB outage makes Docker backend unhealthy", seconds=70)
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120", "postgres")
            wait_for(lambda: get(backend_port, "/health/ready")[0] == 200 and healthy("backend"),
                     "DB recovery restores readiness")
            compose("up", "-d", "--no-build", "--no-deps", "--force-recreate",
                    "--wait", "--wait-timeout", "120", "postgres")
            assert app_sql('SELECT full_name FROM public."user" WHERE username=\'int127_check\';') == "INT127 persistence"
            print("PASS: application role and data preserved on existing-volume PostgreSQL recreation", flush=True)
            compose("up", "-d", "--no-build", "--no-deps", "--force-recreate", "backend")
            wait_for(lambda: healthy("backend"), "backend healthy after recreation")
            assert get(backend_port, "/uploads/photos/int125-check.txt")[1] == b"INT125_UPLOAD_CHECK"
            print("PASS: uploads persisted after backend recreation; migrations and outage/recovery", flush=True)
            if args.backup:
                check_backup(root, compose, env_file, child_env, project, str(Path(args.restic).resolve()))
            for service in ("backend", "frontend"):
                label = run(["docker", "image", "inspect", config["services"][service]["image"],
                             "--format", '{{index .Config.Labels "org.opencontainers.image.revision"}}'],
                            capture=True).strip()
                assert label == revision
            print("PASS: image revision labels match exported source object", flush=True)
        finally:
            # Destructive cleanup is restricted to this UUID project, never production.
            with contextlib.suppress(subprocess.CalledProcessError):
                compose("down", "--volumes", "--remove-orphans")
            for service in ("backend", "frontend"):
                image = f"tervo-{service}:{image_tag}"
                exists = subprocess.run(
                    ["docker", "image", "inspect", image],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                ).returncode == 0
                if exists:
                    with contextlib.suppress(subprocess.CalledProcessError):
                        run(["docker", "image", "rm", image], capture=True)


if __name__ == "__main__":
    main()
