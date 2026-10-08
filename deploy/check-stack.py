"""INT-125: clean-source build and disposable local Compose availability check.

Uses fictitious credentials and only its uniquely named containers/volumes.
Never points at an existing DB, performs a production release or prunes Docker.
"""

import argparse
import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import tempfile
import time
import uuid


def run(args, *, capture=False, env=None, input_data=None):
    return subprocess.run(
        args, check=True, text=True, env=env, input=input_data,
        stdout=subprocess.PIPE if capture else None,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Explicit Git commit/tree to export")
    args = parser.parse_args()
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
        "TERVO_DB_NAME": "test_db",
        "TERVO_DB_USER": "test_user",
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
            for key in ("SECRET_KEY", "TERVO_DB_PASSWORD", "TERVO_VCS_REF"):
                env_file.write_text(valid_env.replace(f"{key}='{values[key]}'", f"{key}=''"))
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
            compose("exec", "-T", "backend", "alembic", "upgrade", "head")
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
            compose("up", "-d", "--no-build", "--no-deps", "--force-recreate", "backend")
            wait_for(lambda: healthy("backend"), "backend healthy after recreation")
            assert get(backend_port, "/uploads/photos/int125-check.txt")[1] == b"INT125_UPLOAD_CHECK"
            print("PASS: uploads persisted after backend recreation; migrations and outage/recovery", flush=True)
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
