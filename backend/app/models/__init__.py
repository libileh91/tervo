"""
Tervo — SQLAlchemy models.

Import all models here so that Alembic's --autogenerate can discover them.
"""

from app.models.base import Base
from app.models.checklist_item import ChecklistItem
from app.models.client import Client
from app.models.intervention import Intervention
from app.models.intervention_photo import InterventionPhoto
from app.models.material import Material
from app.models.review import Review
from app.models.user import User
