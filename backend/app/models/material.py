"""
Tervo — Material model.

Represents a material/part used during an intervention.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Material(Base):
    __tablename__ = "material"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(
        Integer,
        ForeignKey("intervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    quantity = Column(String(50), nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # ── Relationships ───────────────────────────────────────
    intervention = relationship("Intervention", back_populates="materials")

    def __repr__(self) -> str:
        return f"<Material(id={self.id}, name='{self.name}')>"
