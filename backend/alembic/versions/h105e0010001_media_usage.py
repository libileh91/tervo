"""Canonical media usage (INT-105).

Downgrade preserves quantity semantics, not historical spelling (02.00 -> 2).
Unknown historical units stay NULL; no category or unit is inferred.
"""
import re
from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from alembic import op

revision = "h105e0010001"
down_revision = "g104e0010001"
branch_labels = None
depends_on = None

USAGES = ("BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER")
_LEGACY = {"avant": "BEFORE", "après": "AFTER", "apres": "AFTER"}


def _quantity(value, row_id):
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    # Decimal comma is deliberately not interpreted: it can denote thousands.
    if not re.fullmatch(r"[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        raise RuntimeError(f"INT-105 quantity refused at id={row_id}: {value!r}")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise RuntimeError(f"INT-105 quantity refused at id={row_id}: {value!r}") from None
    if (not number.is_finite() or number <= 0
            or number > Decimal("999999999.999")
            or max(0, -number.as_tuple().exponent) > 3):
        raise RuntimeError(f"INT-105 quantity refused at id={row_id}: {value!r}")
    return format(number, "f")


def _indexes(old, new):
    for column in ("id", "intervention_id"):
        op.drop_index(f"ix_{old}_{column}", table_name=new)
        op.create_index(f"ix_{new}_{column}", new, [column])


def upgrade():
    bind = op.get_bind()
    photos = []
    for row in bind.execute(sa.text("SELECT id, category FROM intervention_photo")):
        usage = _LEGACY.get(row.category, row.category)
        if usage not in USAGES:
            raise RuntimeError(f"INT-105 category refused at id={row.id}: {row.category!r}")
        photos.append((row.id, usage))
    quantities = [
        (row.id, _quantity(row.quantity, row.id))
        for row in bind.execute(sa.text("SELECT id, quantity FROM material"))
    ]
    # Every source row has passed preflight before any write or DDL.
    for row_id, usage in photos:
        bind.execute(sa.text("UPDATE intervention_photo SET category=:value WHERE id=:id"),
                     {"value": usage, "id": row_id})
    for row_id, quantity in quantities:
        bind.execute(sa.text("UPDATE material SET quantity=:value WHERE id=:id"),
                     {"value": quantity, "id": row_id})
    op.rename_table("intervention_photo", "photo")
    with op.batch_alter_table("photo") as batch:
        batch.alter_column("category", new_column_name="usage", existing_type=sa.String(20))
        batch.create_check_constraint("ck_photo_usage", "usage IN (" + ", ".join(repr(x) for x in USAGES) + ")")
    _indexes("intervention_photo", "photo")
    op.rename_table("material", "material_usage")
    with op.batch_alter_table("material_usage") as batch:
        batch.alter_column("name", new_column_name="designation", existing_type=sa.String(255))
        batch.alter_column("quantity", existing_type=sa.String(50), type_=sa.Numeric(12, 3),
                           existing_nullable=True, postgresql_using="quantity::numeric(12,3)")
        batch.add_column(sa.Column("unit", sa.String(50), nullable=True))
        batch.create_check_constraint("ck_material_usage_quantity_positive", "quantity > 0")
    _indexes("material", "material_usage")


def downgrade():
    bind = op.get_bind()
    photos = list(bind.execute(sa.text("SELECT id, usage FROM photo")))
    for row in photos:
        if row.usage not in ("BEFORE", "AFTER"):
            raise RuntimeError(f"INT-105 downgrade refused usage at id={row.id}: {row.usage!r}")
    quantities = []
    for row in bind.execute(sa.text("SELECT id, quantity, unit FROM material_usage")):
        if row.unit is not None:
            raise RuntimeError(f"INT-105 downgrade refused unit at id={row.id}")
        value = _quantity(row.quantity, row.id)
        if value is not None:
            value = value.rstrip("0").rstrip(".") if "." in value else value
            if len(value) > 50:
                raise RuntimeError(f"INT-105 downgrade refused quantity at id={row.id}")
        quantities.append((row.id, value))
    with op.batch_alter_table("photo") as batch:
        batch.drop_constraint("ck_photo_usage", type_="check")
        batch.alter_column("usage", new_column_name="category", existing_type=sa.String(20))
    op.rename_table("photo", "intervention_photo")
    _indexes("photo", "intervention_photo")
    for row in photos:
        bind.execute(sa.text("UPDATE intervention_photo SET category=:value WHERE id=:id"),
                     {"id": row.id, "value": "avant" if row.usage == "BEFORE" else "après"})
    with op.batch_alter_table("material_usage") as batch:
        batch.drop_constraint("ck_material_usage_quantity_positive", type_="check")
        batch.drop_column("unit")
        batch.alter_column("designation", new_column_name="name", existing_type=sa.String(255))
        batch.alter_column("quantity", existing_type=sa.Numeric(12, 3), type_=sa.String(50),
                           existing_nullable=True, postgresql_using="quantity::varchar(50)")
    op.rename_table("material_usage", "material")
    _indexes("material_usage", "material")
    for row_id, value in quantities:
        bind.execute(sa.text("UPDATE material SET quantity=:value WHERE id=:id"),
                     {"id": row_id, "value": value})
