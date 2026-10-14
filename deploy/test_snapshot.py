"""INT-128 safety checks; only fictitious data under pytest's temporary directory."""
from contextlib import nullcontext
import fcntl
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("snapshot", ROOT / "scripts/snapshot.py")
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def bundle(path, *, corrupt=False, extra=None):
    contents = {name: b"fictitious-" + name.encode() for name in snapshot.FILES}
    contents["source-project.txt"] = b"test\n"
    contents["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in contents.items()).encode()
    if corrupt:
        contents["database.dump"] += b"corruption"
    if extra:
        contents[extra] = b"unexpected"
    with tarfile.open(path, "w") as archive:
        for name, data in contents.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(data))


def test_verify_and_unpack_never_overwrite(tmp_path):
    source = tmp_path / "bundle.tar"
    bundle(source)
    assert snapshot.verify(source)["source_project"] == "test"
    destination = tmp_path / "restore"
    snapshot.unpack(source, destination)
    assert (destination / "database.dump").read_bytes() == b"fictitious-database.dump"
    with pytest.raises(FileExistsError):
        snapshot.unpack(source, destination)


@pytest.mark.parametrize("extra", ("../outside", "/absolute", "unlisted"))
def test_reject_unexpected_members(tmp_path, extra):
    source = tmp_path / "bundle.tar"
    bundle(source, extra=extra)
    with pytest.raises(RuntimeError, match="Unexpected"):
        snapshot.verify(source)


def test_reject_checksum_corruption_and_git_destination(tmp_path):
    source = tmp_path / "bundle.tar"
    bundle(source, corrupt=True)
    with pytest.raises(RuntimeError, match="checksum"):
        snapshot.verify(source)
    bundle(source)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").touch()
    with pytest.raises(RuntimeError, match="Git checkout"):
        snapshot.unpack(source, checkout / "private")


def test_recovery_preserves_original_container_state(monkeypatch):
    commands = []
    monkeypatch.setattr(snapshot, "docker_state", lambda name: {"running": name == "active"})
    monkeypatch.setattr(snapshot, "call", lambda command, **kw: commands.append(command))
    with pytest.raises(RuntimeError, match="capture failure"):
        with snapshot.stopped_containers(["inactive", "active"]):
            raise RuntimeError("capture failure")
    assert commands == [["docker", "stop", "active"], ["docker", "start", "active"]]


def test_lock_refuses_concurrent_operation_before_capture(tmp_path, monkeypatch):
    lock = tmp_path / "lock"
    with lock.open("w") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        monkeypatch.setattr(snapshot, "_capture_locked",
                            lambda *args: pytest.fail("Capture must not start"))
        with pytest.raises(BlockingIOError):
            snapshot.capture(SimpleNamespace(lock_file=str(lock)), nullcontext())


@pytest.mark.parametrize("caddy_active", (True, False))
def test_host_services_recover_after_capture_failure(monkeypatch, caddy_active):
    commands = []

    def fake_call(command, **kwargs):
        commands.append(command)
        output = ""
        if command[:2] == ["systemctl", "show"]:
            output = "active" if caddy_active else "inactive"
        elif command[:2] == ["docker", "compose"]:
            output = "dockge-id\n"
        return SimpleNamespace(stdout=output)

    monkeypatch.setattr(snapshot, "call", fake_call)
    monkeypatch.setattr(snapshot, "docker_state", lambda _: {"running": True})
    with pytest.raises(RuntimeError, match="capture failure"):
        with snapshot.host_services(Path("/fictitious/compose.yaml")):
            raise RuntimeError("capture failure")
    assert ["docker", "stop", "dockge-id"] in commands
    assert ["docker", "start", "dockge-id"] in commands
    assert (["systemctl", "stop", "caddy.service"] in commands) == caddy_active
    assert (["systemctl", "start", "caddy.service"] in commands) == caddy_active


def test_failed_ssh_never_invokes_restic(tmp_path):
    tools = tmp_path / "bin"
    tools.mkdir()
    marker = tmp_path / "restic-called"
    for name, command in (("ssh", "printf partial; exit 1"),
                          ("restic", f"touch '{marker}'")):
        tool = tools / name
        tool.write_text("#!/bin/sh\n" + command + "\n")
        tool.chmod(0o700)
    password = tmp_path / "password"
    password.write_text("fictitious-test-only")
    password.chmod(0o600)
    config = tmp_path / "config"
    config.write_text(
        f"RESTIC_REPOSITORY='{tmp_path / 'repo'}'\nRESTIC_PASSWORD_FILE='{password}'\n"
        "SSH_TARGET=fictitious\nSSH_CONFIG=/fictitious\nREMOTE_COMMAND=fictitious\n")
    config.chmod(0o600)
    result = subprocess.run(["sh", str(ROOT / "scripts/pull-backup.sh"), str(config)],
                            env={**os.environ, "PATH": str(tools) + ":" + os.environ["PATH"]},
                            capture_output=True)
    assert result.returncode != 0 and not marker.exists()
