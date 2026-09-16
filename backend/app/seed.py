"""
Tervo — Seed script : utilisateurs + données demo.

Idempotent : supprime toutes les données existantes avant de recréer.
Utilisable en dev (SQLite) comme en prod (PostgreSQL).

Usage:
    uv run python -m app.seed                # local
    docker exec <container> python -m app.seed   # Docker
"""

import asyncio
from datetime import date, datetime, time, timedelta

from sqlalchemy import text

from app.core.database import async_session, engine
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.client import Client
from app.models.job import Job, JobStatus, Priority
from app.models.user import Role, User


async def seed():
    # ── 0. Créer les tables si elles n'existent pas ──────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # ── 1. Nettoyage (ordre inverse des dépendances) ──────
        print("🧹 Cleaning existing data…")
        for table in [
            "review",
            "material",
            "job_photo",
            "checklist_item",
            "job",
            "client",
            '"user"',  # quoted: reserved keyword in PostgreSQL
        ]:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()
        print("✅ Clean complete")

        # ── 2. Utilisateurs ────────────────────────────────────
        print("👤 Creating users…")

        admin = User(
            username="admin",
            email="admin@tervo.app",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin Tervo",
            role=Role.ADMIN,
            is_active=True,
        )
        session.add(admin)

        tech1 = User(
            username="tech1",
            email="tech1@tervo.app",
            hashed_password=get_password_hash("password123"),
            full_name="Guuleed Liban",
            role=Role.TECHNICIAN,
            is_active=True,
        )
        session.add(tech1)
        await session.flush()  # get IDs

        print(
            f"  ✅ admin  — username='admin',      password='admin123',    role='admin'"
        )
        print(
            f"  ✅ tech1  — username='tech1',      password='password123', role='technician'"
        )

        # ── 3. Clients ─────────────────────────────────────────
        print("🏢 Creating clients…")

        clients_data = [
            # ── Particuliers (noms somali) ──────────────────
            Client(
                full_name="Ahmed Cabdullahi",
                phone="06 11 22 33 44",
                email="ahmed.cabdullahi@email.com",
                address="123 Rue de Paris",
                postal_code="75001",
                city="Paris",
            ),
            Client(
                full_name="Xasan Maxamed",
                phone="06 55 66 77 88",
                email="xasan.maxamed@email.com",
                address="45 Rue de la République",
                postal_code="69002",
                city="Lyon",
            ),
            Client(
                full_name="Fadumo Cali",
                phone="07 12 34 56 78",
                email="fadumo.cali@email.com",
                address="8 Avenue Victor Hugo",
                postal_code="13001",
                city="Marseille",
            ),
            Client(
                full_name="Cabdiraxmaan Cismaan",
                phone="06 98 76 54 32",
                email="cabdiraxmaan.cismaan@email.com",
                address="67 Boulevard Haussmann",
                postal_code="75009",
                city="Paris",
            ),
            Client(
                full_name="Maryan Axmed",
                phone="07 44 55 66 77",
                email="maryan.axmed@email.com",
                address="15 Rue de la Paix",
                postal_code="44000",
                city="Nantes",
            ),
            # ── Entreprises ─────────────────────────────────
            Client(
                full_name="Barwaaqo Électrique SARL",
                phone="01 88 99 00 11",
                email="contact@barwaaqo.fr",
                address="34 Rue du Faubourg Saint-Antoine",
                postal_code="75012",
                city="Paris",
            ),
            Client(
                full_name="Cagdheer Telecom",
                phone="04 77 88 99 00",
                email="info@cagdheer.fr",
                address="5 Rue de la Bourse",
                postal_code="69001",
                city="Lyon",
            ),
            Client(
                full_name="Horn Solutions Bâtiment",
                phone="01 66 77 88 99",
                email="contact@horn-solutions.fr",
                address="18 Rue de la Chapelle",
                postal_code="75018",
                city="Paris",
            ),
        ]
        for c in clients_data:
            session.add(c)
        await session.flush()  # get client IDs

        print(f"  ✅ {len(clients_data)} clients created")
        for c in clients_data:
            print(f"     - {c.full_name} ({c.city})")

        # ── 4. Jobs ────────────────────────────────────────────
        print("📋 Creating jobs…")
        today = date.today()

        jobs_data = [
            # ── Jobs aujourd'hui ────────────────────────────
            Job(
                client_id=clients_data[0].id,
                technician_id=tech1.id,
                title="Installation climatisation réversible",
                description="Installation clim réversible 80m² - 3 splits + unité extérieure",
                status=JobStatus.PLANIFIE,
                priority=Priority.HAUTE,
                scheduled_date=today,
                scheduled_start_time=time(9, 0),
                scheduled_end_time=time(12, 0),
            ),
            Job(
                client_id=clients_data[3].id,
                technician_id=tech1.id,
                title="Dépannage chaudière gaz",
                description="Chaudière gaz Viessmann qui ne s'allume plus - code erreur F4",
                status=JobStatus.PLANIFIE,
                priority=Priority.URGENTE,
                scheduled_date=today,
                scheduled_start_time=time(14, 0),
                scheduled_end_time=time(16, 0),
            ),
            Job(
                client_id=clients_data[5].id,
                technician_id=tech1.id,
                title="Maintenance chaudière collective",
                description="Entretien annuel chaudière collective immeuble 12 logements",
                status=JobStatus.TERMINE,
                priority=Priority.NORMALE,
                scheduled_date=today - timedelta(days=1),
                scheduled_start_time=time(8, 0),
                scheduled_end_time=time(12, 0),
                started_at=datetime.combine(today - timedelta(days=1), time(8, 10)),
                completed_at=datetime.combine(today - timedelta(days=1), time(11, 45)),
            ),
            # ── Jobs passés (terminés) ──────────────────────
            Job(
                client_id=clients_data[1].id,
                technician_id=tech1.id,
                title="Dépannage urgence fuite gaz",
                description="Fuite sur raccord chaudière - intervention rapide",
                status=JobStatus.TERMINE,
                priority=Priority.URGENTE,
                scheduled_date=today - timedelta(days=2),
                scheduled_start_time=time(18, 0),
                scheduled_end_time=time(20, 0),
                started_at=datetime.combine(today - timedelta(days=2), time(18, 15)),
                completed_at=datetime.combine(today - timedelta(days=2), time(19, 45)),
            ),
            # ── Jobs à venir ────────────────────────────────
            Job(
                client_id=clients_data[2].id,
                technician_id=tech1.id,
                title="Remplacement chauffe-eau",
                description="Remplacement chauffe-eau électrique 200L - cumulus usé",
                status=JobStatus.PLANIFIE,
                priority=Priority.NORMALE,
                scheduled_date=today + timedelta(days=1),
                scheduled_start_time=time(8, 0),
                scheduled_end_time=time(11, 0),
            ),
            Job(
                client_id=clients_data[4].id,
                technician_id=tech1.id,
                title="Installation pompe à chaleur",
                description="PAC air-eau pour maison individuelle 120m²",
                status=JobStatus.PLANIFIE,
                priority=Priority.NORMALE,
                scheduled_date=today + timedelta(days=3),
                scheduled_start_time=time(9, 0),
                scheduled_end_time=time(17, 0),
            ),
            Job(
                client_id=clients_data[6].id,
                technician_id=tech1.id,
                title="Dépannage climatisation Cagdheer",
                description="Climatisation centrale qui ne refroidit plus - local serveurs",
                status=JobStatus.PLANIFIE,
                priority=Priority.HAUTE,
                scheduled_date=today + timedelta(days=2),
                scheduled_start_time=time(13, 0),
                scheduled_end_time=time(15, 0),
            ),
        ]
        for j in jobs_data:
            session.add(j)

        await session.commit()

        print(f"  ✅ {len(jobs_data)} jobs created")
        for j in jobs_data:
            print(f"     - [{j.status.value}] {j.title} — {j.client.full_name}")

        print("\n🎉 Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
