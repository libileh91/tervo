"""INT-105 media/material contracts on disposable databases and upload directories."""
import os
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import httpx
import pytest
from PIL import Image
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.customers.models import Client, Site
from app.modules.identity.models import Role, User
from app.modules.interventions.models.photo import Photo
from app.modules.interventions.models.material_usage import MaterialUsage
from app.modules.interventions.services.photo import MAX_FILE_SIZE
from app.modules.interventions.services.photo import PhotoService
from starlette.datastructures import Headers, UploadFile

USAGES = ("BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER")


@pytest.fixture
async def media(tmp_path, monkeypatch):
    """Real JWT, FK enforcement; PostgreSQL uses a random schema, never public."""
    url = os.environ.get("TERVO_MEDIA_TEST_DATABASE_URL")
    schema = "media_test_" + uuid4().hex
    admin = None
    if url:
        assert url.startswith("postgresql+asyncpg://"), "Use an asyncpg test URL"
        admin = create_async_engine(url)
        async with admin.begin() as db:
            await db.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'media.db'}")
        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    upload = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        tech = User(username="media-tech", email="media-tech@test.fr", hashed_password="unused", role=Role.TECHNICIAN)
        foreign = User(username="media-other", email="media-other@test.fr", hashed_password="unused", role=Role.TECHNICIAN)
        owner = Client(full_name="Media owner", phone="0102030405", address="Paris")
        db.add_all([tech, foreign, owner])
        await db.flush()
        site = Site(client_id=owner.id, name="Media", address="Paris")
        db.add(site)
        await db.commit()
        site_id = site.id
        tokens = [{"Authorization": "Bearer " + create_access_token(user.id)} for user in (tech, foreign)]
    async def database():
        async with sessions() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=tokens[0]) as client:
            parents = []
            for title in ("A", "B"):
                response = await client.post("/api/v1/interventions", json={
                    "site_id": site_id, "title": title, "scheduled_date": "2026-09-28",
                })
                assert response.status_code == 201, response.text
                parents.append("/api/v1/interventions/" + str(response.json()["id"]))
            yield client, sessions, parents, tokens[1], upload
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()
        if admin:
            async with admin.begin() as db:
                await db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await admin.dispose()


def image_file(format="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", (640, 480), "blue").save(buffer, format)
    suffix, mime = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}[format]
    return ("media." + suffix, buffer.getvalue(), mime)


async def test_all_usages_formats_detail_urls_thumbnail_and_deleted_files(media):
    client, sessions, (parent, _), _, upload = media
    photos = []
    for index, usage in enumerate(USAGES):
        response = await client.post(parent + "/photos", data={"usage": usage},
                                     files={"file": image_file(("JPEG", "PNG", "WEBP")[index % 3])})
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["usage"] == usage and "category" not in data
        assert data["file_url"].startswith("/uploads/photos/")
        assert data["thumbnail_url"].startswith("/uploads/photos/")
        async with sessions() as db:
            photo = await db.get(Photo, data["id"])
            assert photo.usage == usage
            assert Path(photo.file_path).read_bytes() == image_file(("JPEG", "PNG", "WEBP")[index % 3])[1]
            with Image.open(photo.thumbnail_path) as thumbnail:
                thumbnail.load()
                assert max(thumbnail.size) <= 300
            photos.append((data, [Path(photo.file_path), Path(photo.thumbnail_path)]))
    listed = await client.get(parent + "/photos")
    assert listed.status_code == 200
    assert listed.json() == [data for data, _ in photos]
    detail = (await client.get(parent)).json()
    assert detail["photos"] == listed.json()
    for data, paths in photos:
        assert (await client.delete(parent + "/photos/" + str(data["id"]))).status_code == 204
        assert all(not path.exists() for path in paths)
    assert (await client.get(parent + "/photos")).json() == []
    assert not list(upload.rglob("*.*"))


@pytest.mark.parametrize("data,file,status", [
    ({"usage": "avant"}, image_file(), 422),
    ({"usage": "INVALID"}, image_file(), 422),
    ({"category": "avant"}, image_file(), 422),
    ({"usage": "BEFORE"}, ("fake.jpg", b"not an image", "image/jpeg"), 400),
    ({"usage": "BEFORE"}, ("fake.txt", b"plain", "text/plain"), 400),
    ({"usage": "BEFORE"}, ("huge.jpg", b"x" * (MAX_FILE_SIZE + 1), "image/jpeg"), 400),
])
async def test_invalid_upload_is_atomic(media, data, file, status):
    client, sessions, (parent, _), _, upload = media
    response = await client.post(parent + "/photos", data=data, files={"file": file})
    assert response.status_code == status, response.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Photo.id))) == 0
    assert not list(upload.rglob("*.*"))


async def test_commit_failure_rolls_back_record_and_cleans_only_created_files(media):
    _, sessions, (parent, _), _, upload = media
    upload.mkdir()
    sentinel = upload / "unrelated.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    filename, content, mime = image_file()
    async with sessions() as db:
        with patch.object(db, "commit", side_effect=RuntimeError("commit seam")):
            with pytest.raises(RuntimeError, match="commit seam"):
                await PhotoService(db).upload_photo(
                    int(parent.rsplit("/", 1)[1]),
                    UploadFile(filename=filename, file=BytesIO(content), headers=Headers({"content-type": mime})),
                    "BEFORE",
                )
    async with sessions() as db:
        assert await db.scalar(select(func.count(Photo.id))) == 0
    assert list(upload.rglob("*.*")) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "preserve"


async def test_parent_scope_and_foreign_technician_are_not_child_id_authority(media):
    client, _, (first, second), foreign, _ = media
    photo = await client.post(first + "/photos", data={"usage": "BEFORE"}, files={"file": image_file()})
    material = await client.post(first + "/materials", json={"designation": "Joint", "quantity": 1, "unit": "pièce"})
    assert photo.status_code == material.status_code == 201
    photo_id, material_id = photo.json()["id"], material.json()["id"]
    requests = [("DELETE", f"/photos/{photo_id}", {}),
                ("PUT", f"/materials/{material_id}", {"json": {"quantity": 2}}),
                ("DELETE", f"/materials/{material_id}", {})]
    for method, suffix, kwargs in requests:
        assert (await client.request(method, second + suffix, **kwargs)).status_code == 404
        assert (await client.request(method, first + suffix, headers=foreign, **kwargs)).status_code == 403
    assert len((await client.get(first + "/photos")).json()) == 1
    assert (await client.get(first + "/materials")).json()[0]["quantity"] == 1
    client.headers.pop("Authorization")
    for route in ("/photos", "/materials"):
        assert (await client.get(first + route)).status_code in (401, 403)
    client.headers["Authorization"] = "Bearer invalid.jwt"
    assert (await client.get(first + "/photos")).status_code == 401


@pytest.mark.parametrize("unsafe_field", ["file_path", "thumbnail_path"])
async def test_delete_refuses_outside_upload_root_before_any_mutation(media, unsafe_field):
    client, sessions, (parent, _), _, upload = media
    outside = upload.parent / "outside-photo.jpg"
    outside.write_bytes(b"foreign file must survive")
    inside = upload / "photos" / "inside.jpg"
    inside.parent.mkdir(parents=True)
    inside.write_bytes(b"owned file must also survive the refusal")
    values = {"file_path": str(inside), "thumbnail_path": str(inside)}
    values[unsafe_field] = str(outside)
    async with sessions() as db:
        photo = Photo(intervention_id=int(parent.rsplit("/", 1)[1]), usage="BEFORE", **values)
        db.add(photo)
        await db.commit()
        photo_id = photo.id
    response = await client.delete(f"{parent}/photos/{photo_id}")
    assert response.status_code == 400, response.text
    assert outside.read_bytes() == b"foreign file must survive"
    assert inside.read_bytes() == b"owned file must also survive the refusal"
    async with sessions() as db:
        assert await db.get(Photo, photo_id) is not None


@pytest.mark.parametrize("field,value", [
    ("quantity", 0), ("quantity", -1), ("quantity", "Infinity"), ("quantity", "NaN"),
    ("quantity", 1000000000), ("quantity", "0.0001"), ("quantity", True),
    ("quantity", []), ("quantity", None), ("designation", None), ("designation", ""),
    ("designation", " "), ("designation", "x" * 256), ("unit", None),
    ("unit", ""), ("unit", " "), ("unit", "x" * 51), ("name", "old alias"),
])
async def test_material_validation_create_and_update(media, field, value):
    client, _, (parent, _), _, _ = media
    valid = {"designation": "Joint", "quantity": 1, "unit": "pièce"}
    response = await client.post(parent + "/materials", json={**valid, field: value})
    assert response.status_code == 422, response.text
    created = await client.post(parent + "/materials", json=valid)
    assert created.status_code == 201
    target = parent + "/materials/" + str(created.json()["id"])
    response = await client.put(target, json={field: value})
    assert response.status_code == 422, response.text
    assert (await client.get(parent + "/materials")).json()[0]["quantity"] == 1


async def test_material_required_fields_precision_partial_update_crud_and_historical_nulls(media):
    client, sessions, (parent, _), _, _ = media
    valid = {"designation": "Fluide", "quantity": 0.001, "unit": "kg"}
    for field in valid:
        assert (await client.post(parent + "/materials", json={k: v for k, v in valid.items() if k != field})).status_code == 422
    created = await client.post(parent + "/materials", json=valid)
    assert created.status_code == 201, created.text
    data = created.json()
    assert type(data["quantity"]) in (float, int) and data["quantity"] == 0.001
    async with sessions() as db:
        row = await db.get(MaterialUsage, data["id"])
        assert row.quantity == Decimal("0.001") and row.quantity.as_tuple().exponent == -3
        db.add(MaterialUsage(intervention_id=row.intervention_id, designation="Historique", quantity=None, unit=None, position=1))
        await db.commit()
    target = parent + "/materials/" + str(data["id"])
    changed = await client.put(target, json={"designation": "Fluide neuf"})
    assert changed.status_code == 200
    assert changed.json()["quantity"] == 0.001 and changed.json()["unit"] == "kg"
    maximum = await client.put(target, json={"quantity": "999999999.999", "unit": "litre"})
    assert maximum.status_code == 200, maximum.text
    assert maximum.json()["quantity"] == 999999999.999
    records = (await client.get(parent + "/materials")).json()
    assert records[1]["quantity"] is None and records[1]["unit"] is None
    assert (await client.delete(target)).status_code == 204
    assert (await client.delete(target)).status_code == 404
