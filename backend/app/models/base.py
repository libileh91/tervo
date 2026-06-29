"""
ResQ — SQLAlchemy declarative base.

Every ORM model in this project inherits from this Base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
