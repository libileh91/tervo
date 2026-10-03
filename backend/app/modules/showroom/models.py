"""Commercial visit events, independent of sales and physical equipment."""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.base import Base


class FollowUpStatus(str, enum.Enum):
    TO_FOLLOW_UP = "TO_FOLLOW_UP"
    CONSIDERING = "CONSIDERING"
    QUOTE_REQUESTED = "QUOTE_REQUESTED"
    QUOTE_SENT = "QUOTE_SENT"
    SOLD = "SOLD"
    LOST = "LOST"
    NO_FURTHER_ACTION = "NO_FURTHER_ACTION"


class ShowroomVisit(Base):
    __tablename__ = "showroom_visit"
    __table_args__ = (
        CheckConstraint(
            "client_id IS NOT NULL OR "
            "(visitor_name IS NOT NULL AND length(trim(visitor_name)) > 0)",
            name="ck_showroom_visit_identity",
        ),
        CheckConstraint(
            "follow_up_status IN (" + ", ".join(repr(s.value) for s in FollowUpStatus) + ")",
            name="ck_showroom_visit_follow_up_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="RESTRICT"), nullable=True, index=True)
    visitor_name = Column(String(255), nullable=True)
    visited_at = Column(DateTime, nullable=False, index=True)
    salesperson_id = Column(Integer, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    follow_up_status = Column(
        String(30), nullable=False, default=FollowUpStatus.TO_FOLLOW_UP.value,
        server_default=FollowUpStatus.TO_FOLLOW_UP.value, index=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client")
    salesperson = relationship("User")
    presented_products = relationship(
        "ShowroomVisitProduct", back_populates="visit", cascade="all, delete-orphan",
        order_by="ShowroomVisitProduct.product_id",
    )

    @property
    def product_ids(self) -> list[int]:
        return [link.product_id for link in self.presented_products]


class ShowroomVisitProduct(Base):
    __tablename__ = "showroom_visit_product"

    visit_id = Column(Integer, ForeignKey("showroom_visit.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True)
    visit = relationship("ShowroomVisit", back_populates="presented_products")
    product = relationship("Product")
