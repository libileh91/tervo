"""Versioned definitions and snapshots created in the caller's transaction."""
from fastapi import HTTPException
from sqlalchemy import select, update
from app.modules.interventions.models.checklist import ChecklistTemplate, InterventionChecklist
from app.modules.interventions.models.checklist_item import ChecklistItem
from app.modules.interventions.repositories.checklist import ChecklistRepository

DEFAULT_PRE_ITEMS = [
    ("Vérifier équipement de protection individuelle (EPI)", 1),
    ("Vérifier les accès et sécuriser la zone de travail", 2),
    ("Couper l'alimentation électrique de l'équipement", 3),
]
DEFAULT_POST_ITEMS = [
    ("Nettoyer la zone de travail et remettre en état", 1),
    ("Rétablir l'alimentation et tester le fonctionnement", 2),
]


class ChecklistService:
    def __init__(self, db):
        self.db = db
        self.repo = ChecklistRepository(db)

    async def create_snapshot(self, intervention_id, template_id=None):
        if template_id is None:
            name, version = "Checklist par défaut", 1
            definitions = [
                {"label": label, "position": pos, "category": category}
                for category, entries in (("pre_intervention", DEFAULT_PRE_ITEMS), ("post_intervention", DEFAULT_POST_ITEMS))
                for label, pos in entries
            ]
        else:
            # Read the whole version coherently; lock until the snapshot commits
            # on PostgreSQL (SQLite serializes writes instead).
            template = (await self.db.execute(select(ChecklistTemplate)
                .where(ChecklistTemplate.id == template_id).with_for_update()
                .execution_options(populate_existing=True))).scalar_one_or_none()
            if template is None:
                raise HTTPException(404, "Modèle de checklist non trouvé")
            if not template.active:
                raise HTTPException(422, "Modèle de checklist inactif")
            name, version, definitions = template.name, template.version, template.items
        snapshot = InterventionChecklist(
            intervention_id=intervention_id, template_id=template_id,
            template_name=name, template_version=version,
            items=[ChecklistItem(**definition) for definition in definitions],
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def create_default_items(self, intervention_id):
        """Mock setup helper; transaction is owned by the caller."""
        return await self.create_snapshot(intervention_id)

    async def get_items(self, intervention_id):
        return await self.repo.get_items(intervention_id)

    async def get_snapshot(self, intervention_id):
        snapshot = await self.repo.get_snapshot(intervention_id)
        if snapshot is None:
            raise HTTPException(404, "Checklist non trouvée")
        return snapshot

    async def update_item(self, item_id, data):
        item = await self.repo.get_item(item_id)
        if item is None:
            raise HTTPException(404, "Item de checklist non trouvé")
        return await self.repo.update_item(item, data)

    async def validate_all_checked(self, intervention_id):
        counts = await self.repo.count_unchecked_by_category(intervention_id)
        errors = [f"{count} item(s) {'pré-intervention' if category == 'pre_intervention' else 'post-intervention'} non réalisés"
                  for category, count in counts.items()]
        return {"is_valid": not counts, "errors": errors,
                "detail": f"{sum(counts.values())} items non réalisés ({', '.join(errors)})"}

    async def list_templates(self):
        return list((await self.db.execute(select(ChecklistTemplate).order_by(ChecklistTemplate.id))).scalars())

    async def create_template(self, body):
        template = ChecklistTemplate(**body.model_dump())
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(self, template_id, body):
        template = (await self.db.execute(select(ChecklistTemplate)
            .where(ChecklistTemplate.id == template_id)
            .execution_options(populate_existing=True))).scalar_one_or_none()
        if template is None:
            raise HTTPException(404, "Modèle de checklist non trouvé")
        # Atomic compare-and-swap works on both PostgreSQL and SQLite.
        version = template.version
        result = await self.db.execute(update(ChecklistTemplate)
            .where(ChecklistTemplate.id == template_id, ChecklistTemplate.version == version)
            .values(**body.model_dump(exclude_unset=True), version=version + 1)
            .execution_options(synchronize_session=False))
        if result.rowcount != 1:
            await self.db.rollback()
            raise HTTPException(409, "Le modèle de checklist a été modifié")
        await self.db.commit()
        await self.db.refresh(template)
        return template
