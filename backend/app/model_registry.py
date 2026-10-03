"""Explicit ORM loading for the application, Alembic and seed entry points."""


def load_models() -> None:
    """Register all current models on the shared Base, without creating an engine."""
    # Local imports keep importing this registry independent of loading domains.
    # Python's module cache makes repeated calls safe without a second registry.
    from app.modules.interventions.models.checklist_item import ChecklistItem  # noqa: F401
    from app.modules.interventions.models.checklist import ChecklistTemplate, InterventionChecklist  # noqa: F401
    from app.modules.customers.models import Client, Site  # noqa: F401
    from app.modules.equipment.models import Equipment  # noqa: F401
    from app.modules.imports.models import (  # noqa: F401
        ImportBatch,
        ImportError,
        ImportRecord,
        ImportReference,
    )
    from app.modules.installations.models import Installation  # noqa: F401
    from app.modules.interventions.models.intervention import Intervention  # noqa: F401
    from app.modules.interventions.models.photo import Photo  # noqa: F401
    from app.modules.interventions.models.material_usage import MaterialUsage  # noqa: F401
    from app.modules.catalog.models import Product  # noqa: F401
    from app.modules.interventions.models.review import Review  # noqa: F401
    from app.modules.sales.models import Sale, SaleLine  # noqa: F401

    from app.modules.identity.models import User  # noqa: F401
