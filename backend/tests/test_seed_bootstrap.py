"""Seed CLI on disposable demo-only SQLite; not a populated V2/prod safety test."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]


def environment(tmp_path, database):
    env = {key: value for key, value in os.environ.items() if not key.startswith("TERVO_")}
    env.update(PYTHONPATH=str(BACKEND), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL=f"sqlite:///{database}", UPLOAD_DIR=str(tmp_path / "uploads"))
    return env


def test_import_seed_does_not_execute_sql(tmp_path):
    database = tmp_path / "import-only.db"
    result = subprocess.run([sys.executable, "-B", "-c", """
from sqlalchemy import event
from sqlalchemy.engine import Engine
def forbidden(*args, **kwargs):
    raise AssertionError("Importing seed attempted database access")
event.listen(Engine, "engine_connect", forbidden)
event.listen(Engine, "before_cursor_execute", forbidden)
import app.seed
assert callable(app.seed.seed)
"""], cwd=tmp_path, env=environment(tmp_path, database),
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not database.exists()


def test_real_seed_cli_twice_on_its_own_demo_only(tmp_path):
    database = tmp_path / "demo-only.db"
    assert not database.exists()
    env = environment(tmp_path, database)
    for _ in range(2):
        result = subprocess.run([sys.executable, "-B", "-m", "app.seed"],
                                cwd=tmp_path, env=env, capture_output=True,
                                text=True, timeout=120)
        # Do not surface demo credentials printed by the CLI in test diagnostics.
        assert result.returncode == 0, result.stderr
        with sqlite3.connect(database) as connection:
            assert {
                table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                for table in ("user", "client", "site", "intervention")
            } == {"user": 2, "client": 8, "site": 8, "intervention": 7}
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            users = connection.execute('SELECT role, hashed_password FROM "user"').fetchall()
            assert {role.lower() for role, _ in users} == {"admin", "technician"}
            from passlib.hash import bcrypt
            assert all(bcrypt.identify(value) for _, value in users)
            assert all(len(value) == 60 for _, value in users)
