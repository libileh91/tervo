"""
Tervo — SQLAlchemy models.

Legacy exports for existing callers during the modular cutover.
Entry points load models explicitly through app.model_registry.
"""

from app.core.base import Base
from app.models.checklist_item import ChecklistItem
from app.modules.customers.models import Client, Site
from app.models.intervention import Intervention
from app.models.intervention_photo import InterventionPhoto
from app.models.material import Material
from app.models.review import Review

from app.models.user import User

from app.modules.catalog.models import Product

from app.modules.equipment.models import Equipment
from app.modules.installations.models import Installation
from app.modules.sales.models import Sale, SaleLine, SaleStatus

from app.models.import_batch import ImportBatch, ImportRecord, ImportReference, ImportError
