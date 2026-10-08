"""Select SQLAlchemy drivers without interpolating credentials into config files."""

from sqlalchemy.engine import URL, make_url


def database_url(raw_url: str, *, asynchronous: bool) -> URL:
    url = make_url(raw_url)
    backend = url.get_backend_name()
    if backend == "sqlite":
        return url.set(drivername="sqlite+aiosqlite" if asynchronous else "sqlite")
    if backend == "postgresql":
        return url.set(drivername="postgresql+asyncpg" if asynchronous else "postgresql+psycopg2")
    return url
