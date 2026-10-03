"""INT-109: one direct API recipe on a disposable SQLite or PostgreSQL schema."""

import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.catalog.models import Product
from app.modules.customers.models import Client
from app.modules.identity.models import Role, User
from app.modules.sales.models import Sale
from app.modules.showroom.models import ShowroomVisit, ShowroomVisitProduct


@pytest.fixture
async def context(tmp_path):
    url = os.environ.get("TERVO_SHOWROOM_TEST_DATABASE_URL")
    admin_engine = None
    if url:
        assert url.startswith("postgresql+asyncpg://"), "Only a disposable PostgreSQL test server"
        schema = "showroom_test_" + uuid4().hex
        admin_engine = create_async_engine(url)
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'showroom.db'}")

        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        admin = User(username="showroom-admin", email="admin@showroom.invalid",
                     role=Role.ADMIN, **{"hashed_" + "password": "unused"})
        tech = User(username="showroom-tech", email="tech@showroom.invalid",
                    role=Role.TECHNICIAN, **{"hashed_" + "password": "unused"})
        customer = Client(full_name="Client showroom", phone="0000000000", address="Paris")
        products = [
            Product(reference=f"SHOW-{i}", name=f"Produit {i}", brand="B", model="M", category="PAC",
                    active=i != 3) for i in range(1, 4)
        ]
        db.add_all([admin, tech, customer, *products])
        await db.commit()
        ids = admin.id, tech.id, customer.id, *(product.id for product in products)

    async def database():
        async with sessions() as db:
            yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, ids
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()
        if admin_engine is not None:
            async with admin_engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await admin_engine.dispose()


async def test_showroom_prospect_to_follow_up_api(context):
    client, sessions, (admin, tech, customer, product1, product2, inactive) = context
    path = "/api/v1/showroom/visits"

    def headers(user):
        return {"Authorization": "Bearer " + create_access_token(user)}

    async def call(method, endpoint, expected, *, who=admin, **kwargs):
        response = await client.request(
            method, endpoint, headers=headers(who) if who else {}, **kwargs,
        )
        assert response.status_code == expected, (endpoint, response.status_code, response.text)
        return response

    prospect_data = {"visitor_name": "  Sarah Martin  ", "visited_at": "2026-09-21T14:30:00+02:00",
                     "notes": "PAC", "follow_up_status": "TO_FOLLOW_UP"}
    await call("POST", path, 401, who=None, json=prospect_data)
    await call("POST", path, 403, who=tech, json=prospect_data)
    await call("GET", path, 403, who=tech)
    for payload in (
        {"visited_at": prospect_data["visited_at"], "visitor_name": "  "},
        {**prospect_data, "follow_up_status": "NOT_A_STATUS"},
        {**prospect_data, "client_id": -1},
        {**prospect_data, "salesperson_id": -1},
    ):
        await call("POST", path, 422, json=payload)
    await call("POST", path, 403, json={**prospect_data, "salesperson_id": tech})
    await call("POST", path, 404, json={**prospect_data, "client_id": 99999})

    created = (await call("POST", path, 201, json={**prospect_data, "salesperson_id": admin})).json()
    visit_id = created["id"]
    assert created["visitor_name"] == "Sarah Martin" and created["client_id"] is None
    assert created["visited_at"].startswith("2026-09-21T12:30:00")
    assert created["salesperson_id"] == admin and created["product_ids"] == []
    for product_id in (product1, product2):
        result = (await call("POST", f"{path}/{visit_id}/products", 201,
                             json={"product_id": product_id})).json()
        assert product_id in result["product_ids"]
    await call("POST", f"{path}/{visit_id}/products", 409, json={"product_id": product1})
    await call("POST", f"{path}/{visit_id}/products", 409, json={"product_id": inactive})
    await call("POST", f"{path}/{visit_id}/products", 404, json={"product_id": 99999})
    await call("POST", f"{path}/99999/products", 404, json={"product_id": product1})
    await call("PATCH", f"{path}/{visit_id}", 422, json={"follow_up_status": "UNKNOWN"})
    await call("PATCH", f"{path}/{visit_id}", 422, json={"visited_at": None})
    await call("PATCH", f"{path}/{visit_id}", 422, json={"salesperson_id": tech})
    await call("PATCH", f"{path}/{visit_id}", 422, json={"client_id": None, "visitor_name": None})
    changed = (await call("PATCH", f"{path}/{visit_id}", 200,
                          json={"client_id": customer, "follow_up_status": "SOLD"})).json()
    assert changed["client_id"] == customer and changed["follow_up_status"] == "SOLD"
    assert changed["product_ids"] == [product1, product2]

    known = (await call("POST", path, 201, json={
        "client_id": customer, "visited_at": "2026-09-22T15:00:00",
        "follow_up_status": "QUOTE_REQUESTED",
    })).json()
    assert known["visitor_name"] is None and known["id"] != visit_id
    for params, expected in (
        ({"client_id": customer}, 2), ({"salesperson_id": admin}, 2),
        ({"follow_up_status": "SOLD"}, 1), ({"product_id": product1}, 1),
        ({"visited_from": "2026-09-22T00:00:00"}, 1),
    ):
        listing = (await call("GET", path, 200, params=params)).json()
        assert listing["total"] == expected and len(listing["items"]) == expected
    listing = (await call("GET", path, 200, params={"page_size": 1, "page": 2})).json()
    assert listing["total"] == 2 and listing["pages"] == 2 and len(listing["items"]) == 1
    await call("GET", path, 422, params={"follow_up_status": "INVALID"})
    await call("GET", path, 422, params={"visited_from": "2026-09-23T00:00:00",
                                         "visited_to": "2026-09-20T00:00:00"})
    await call("GET", f"{path}/99999", 404)

    async with sessions() as db:
        db.add(ShowroomVisitProduct(visit_id=visit_id, product_id=product1))
        with pytest.raises(IntegrityError):
            await db.commit()  # Composite PK guards concurrent duplicate presentation.
        await db.rollback()
        assert await db.scalar(select(func.count(Sale.id))) == 0  # SOLD is not a sale.
        assert await db.scalar(select(func.count(ShowroomVisitProduct.visit_id))) == 2
        assert (await db.get(ShowroomVisit, visit_id)).client_id == customer

    # A catalogue deactivation cannot rewrite a past presentation.
    async with sessions() as db:
        product = await db.get(Product, product1)
        product.active = False
        await db.commit()
    assert (await call("GET", f"{path}/{visit_id}", 200)).json()["product_ids"] == [product1, product2]
    assert (await call("DELETE", f"/api/v1/clients/{customer}", 409)).json()["detail"]
    await call("DELETE", f"{path}/{visit_id}/products/{product2}", 204)
    await call("DELETE", f"{path}/{visit_id}/products/{product2}", 404)
    assert (await call("GET", f"{path}/{visit_id}", 200)).json()["product_ids"] == [product1]
