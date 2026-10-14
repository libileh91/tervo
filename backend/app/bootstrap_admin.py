"""One-time administrator bootstrap. Never creates tables or runs the demo seed.

Run on a migrated database with explicit DB environment variables and a TTY:
    python -m app.bootstrap_admin --confirm-db-name tervo_db
"""

import argparse
import asyncio
import getpass
import os
import re
import sys

from sqlalchemy import or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Role, User


class BootstrapError(Exception):
    """An expected refusal; messages contain no credentials or connection URL."""


def check_database(expected_name: str) -> None:
    """Require an explicit connection source, not Settings' local SQLite default."""
    components = ("TERVO_DB_NAME", "TERVO_DB_USER", "TERVO_DB_PASSWORD")
    if not (
        os.environ.get("DATABASE_URL")
        or all(os.environ.get(component) for component in components)
    ):
        raise BootstrapError("Configure the database explicitly before bootstrap.")

    from app.config import settings

    try:
        actual_name = make_url(settings.DATABASE_URL).database
    except (ValueError, TypeError):
        raise BootstrapError("Invalid database configuration.") from None
    if not expected_name or not actual_name or actual_name != expected_name:
        raise BootstrapError("Database name does not match --confirm-db-name.")
    if actual_name == ":memory:":
        raise BootstrapError("An in-memory database cannot be bootstrapped.")


def validate_identity(username: str, email: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,100}", username):
        raise BootstrapError("Username must be 3-100 ASCII letters, digits, _, . or -.")
    if (
        len(email) > 255
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        raise BootstrapError("Invalid email address.")


async def check_existing(session: AsyncSession, username: str, email: str) -> bool:
    """Return True only for the exact, active admin; never repair accounts."""
    result = await session.execute(
        select(User).where(
            or_(User.username == username, User.email == email, User.role == Role.ADMIN)
        )
    )
    users = result.scalars().all()
    if not users:
        return False
    if (
        len(users) == 1
        and users[0].username == username
        and users[0].email == email
        and users[0].role == Role.ADMIN
        and users[0].is_active
    ):
        return True
    raise BootstrapError("An administrator or conflicting identity already exists; unchanged.")


async def create_admin(
    session: AsyncSession, username: str, email: str, password: str
) -> bool:
    """Create a single admin in the caller's transaction; True if created."""
    from app.core.security import get_password_hash

    validate_identity(username, email)
    if await check_existing(session, username, email):
        return False
    if not 12 <= len(password.encode("utf-8")) <= 72:
        raise BootstrapError("Password must contain 12-72 UTF-8 bytes.")
    session.add(
        User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=Role.ADMIN,
            is_active=True,
        )
    )
    await session.flush()
    return True


async def run(expected_db: str) -> str:
    check_database(expected_db)
    if not sys.stdin.isatty():
        raise BootstrapError("An interactive terminal is required; do not pipe secrets.")

    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    validate_identity(username, email)

    # Import the engine only after the explicit target has been checked.
    from app.core.database import async_session

    async with async_session() as session:
        if await check_existing(session, username, email):
            return "Administrator already exists; no changes made."
        await session.rollback()  # Close the read transaction before prompting.
        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise BootstrapError("Passwords do not match.")
        try:
            async with session.begin():
                created = await create_admin(session, username, email, password)
        except IntegrityError:
            raise BootstrapError("Identity conflict; no changes committed.") from None
        return "Administrator created." if created else "Administrator already exists; no changes made."


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the first Tervo administrator")
    parser.add_argument("--confirm-db-name", required=True, help="Expected database name")
    args = parser.parse_args()
    try:
        print(asyncio.run(run(args.confirm_db_name)))
        return 0
    except (BootstrapError, SQLAlchemyError, EOFError) as exc:
        if isinstance(exc, BootstrapError):
            print(f"Bootstrap refused: {exc}", file=sys.stderr)
        else:
            print("Bootstrap failed; database unchanged.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
