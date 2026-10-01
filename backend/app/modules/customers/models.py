"""
Tervo — Client and Site models.

Customers and their physical locations where equipment is installed and
interventions take place.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.base import Base


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    address = Column(String(500), nullable=False)
    postal_code = Column(String(20), nullable=True)
    city = Column(String(255), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.full_name}')>"


class Site(Base):
    __tablename__ = "site"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    postal_code = Column(String(20), nullable=True)
    city = Column(String(255), nullable=True, index=True)
    country = Column(String(100), nullable=True)
    access_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    equipment = relationship("Equipment", back_populates="site", passive_deletes="all")
    installations = relationship("Installation", back_populates="site", passive_deletes="all")

    # ── Relationships ───────────────────────────────────────
    client = relationship("Client", backref="sites")

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name='{self.name}')>"
