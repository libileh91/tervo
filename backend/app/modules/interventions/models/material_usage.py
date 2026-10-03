"""
Tervo — MaterialUsage model.

Represents a material/part used during an intervention.
"""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.base import Base


class MaterialUsage(Base):
    __tablename__ = "material_usage"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_material_usage_quantity_positive"),)

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(
        Integer,
        ForeignKey("intervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    designation = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=True)
    unit = Column(String(50), nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # ── Relationships ───────────────────────────────────────
    intervention = relationship("Intervention", back_populates="materials")

    def __repr__(self) -> str:
        return f"<MaterialUsage(id={self.id}, designation='{self.designation}')>"
