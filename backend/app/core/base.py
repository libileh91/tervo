"""Shared SQLAlchemy declarative base, without engine or domain imports."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
