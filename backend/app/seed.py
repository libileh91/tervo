"""
ResQ — Seed script : utilisateurs + données demo.

Idempotent : supprime toutes les données existantes avant de recréer.
Utilisable en dev (SQLite) comme en prod (PostgreSQL).

Usage:
    uv run python -m app.seed                # local
    docker exec <container> python -m app.seed   # Docker
"""

import asyncio
from datetime import date, datetime, time, timedelta

from sqlalchemy import text

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.client import Client
from app.models.job import Job, JobStatus, Priority
from app.models.user import Role, User


async def seed():
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
            "user",
        ]:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()
        print("✅ Clean complete")

        # ── 2. Utilisateurs ────────────────────────────────────
        print("👤 Creating users…")

        admin = User(
            username="admin",
            email="admin@resq.app",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin ResQ",
            role=Role.ADMIN,
            is_active=True,
        )
        session.add(admin)

        tech1 = User(
            username="tech1",
            email="tech1@resq.app",
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
            Client(
                full_name="Monsieur Hamdi Hassan",
                phone="06 11 22 33 44",
                email="hamdi.hassan@email.com",
                address="123 Rue de Paris",
                postal_code="75001",
                city="Paris",
            ),
            Client(
                full_name="Madame Khadija Ahmed",
                phone="06 55 66 77 88",
                email="khadija.ahmed@email.com",
                address="45 Avenue des Champs-Élysées",
                postal_code="75008",
                city="Paris",
            ),
            Client(
                full_name="Société MediaPro SARL",
                phone="01 99 88 77 66",
                email="contact@mediapro.fr",
                address="12 Rue de la République",
                postal_code="69002",
                city="Lyon",
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
            Job(
                client_id=clients_data[0].id,
                technician_id=tech1.id,
                title="Installation climatisation",
                description="Installation d'un système de climatisation réversible dans un appartement parisien de 80m²",
                status=JobStatus.PLANIFIE,
                priority=Priority.HAUTE,
                scheduled_date=today,
                scheduled_start_time=time(9, 0),
                scheduled_end_time=time(12, 0),
            ),
            Job(
                client_id=clients_data[1].id,
                technician_id=tech1.id,
                title="Dépannage chaudière",
                description="Chaudière gaz qui ne s'allume plus - intervention urgente",
                status=JobStatus.TERMINE,
                priority=Priority.URGENTE,
                scheduled_date=today - timedelta(days=1),
                scheduled_start_time=time(14, 0),
                scheduled_end_time=time(16, 30),
                started_at=datetime.combine(today - timedelta(days=1), time(14, 5)),
                completed_at=datetime.combine(today - timedelta(days=1), time(16, 15)),
            ),
            Job(
                client_id=clients_data[2].id,
                technician_id=tech1.id,
                title="Maintenance annuelle chaudière",
                description="Entretien annuel obligatoire - vérification complète",
                status=JobStatus.PLANIFIE,
                priority=Priority.NORMALE,
                scheduled_date=today + timedelta(days=3),
                scheduled_start_time=time(8, 0),
                scheduled_end_time=time(10, 0),
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
