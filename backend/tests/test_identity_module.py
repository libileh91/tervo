"""R10/INT-122: identity cutover and focused real-JWT regressions.

Application imports stay inside tests/fixtures so collection works before cutover.
"""

import ast
from importlib.util import resolve_name

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python


RETIRED_MODULES = (
    "app.models.user",
    "app.schemas.auth",
    "app.api.v1.auth",
    "app.core.deps",
)
IDENTITY = "app.modules.identity"


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield node, [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = resolve_name(
                    "." * node.level + module,
                    ".".join(path.parent.relative_to(BACKEND).parts),
                )
            yield node, [module, *(module + "." + alias.name for alias in node.names)]


def test_identity_layout_and_cutover_imports():
    package = BACKEND / "app/modules/identity"
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py", "models.py", "schemas.py", "api.py", "dependencies.py",
    }
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    assert not tree.body or (len(tree.body) == 1 and ast.get_docstring(tree) is not None)
    assert not [
        name for name in RETIRED_MODULES
        if (BACKEND / (name.replace(".", "/") + ".py")).exists()
    ]
    violations = []
    for root in (BACKEND / "app", BACKEND / "tests"):
        for path in root.rglob("*.py"):
            for node, modules in _imports(path):
                if any(name == old or name.startswith(old + ".")
                       for name in modules for old in RETIRED_MODULES):
                    violations.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not violations, violations


def test_identity_root_import_is_pure(tmp_path):
    _run_python(tmp_path, """
        from importlib import import_module
        from app.core.base import Base
        import_module("app.modules.identity")
        assert not Base.metadata.tables
        assert not list(Base.registry.mappers)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", IDENTITY + ".models", IDENTITY + ".schemas",
            IDENTITY + ".dependencies", IDENTITY + ".api",
        ))


@pytest.mark.parametrize("module", ["models", "schemas"])
def test_identity_leaf_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base
        imported = import_module("app.modules.identity." + {module!r})
        if {module!r} == "models":
            assert set(Base.metadata.tables) == {{"user"}}
            assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{imported.User}}
            assert imported.User.metadata is Base.metadata
        else:
            assert not Base.metadata.tables
            assert not list(Base.registry.mappers)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", IDENTITY + ".dependencies", IDENTITY + ".api",
        ) + ((IDENTITY + ".models",) if module == "schemas" else ()))


@pytest.mark.parametrize("order", ["registry-first", "identity-first"])
def test_identity_one_user_mapper_and_role_in_both_orders(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base
        from app.model_registry import load_models
        if {order!r} == "registry-first":
            load_models()
        identity = import_module("app.modules.identity.models")
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        assert mappers <= set(Base.registry.mappers)
        complete = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert set(Base.registry.mappers) == complete
        User, Role = identity.User, identity.Role
        assert identity.Base is Base
        assert issubclass(User, Base)
        assert User.__table__ is Base.metadata.tables["user"]
        assert inspect(User) is next(
            mapper for mapper in Base.registry.mappers if mapper.class_ is User
        )
        assert len([m for m in Base.registry.mappers
                    if m.local_table.name == "user"]) == 1
        assert {{role.name: role.value for role in Role}} == {{
            "ADMIN": "admin", "TECHNICIAN": "technician"
        }}
        assert User.__table__.c.role.type.enum_class is Role
        assert User.__table__.c.role.default.arg is Role.TECHNICIAN
        assert set(User.__table__.c.keys()) == {{
            "id", "username", "email", "hashed_password", "full_name", "role",
            "is_active", "created_at", "updated_at"
        }}
        assert User.__table__.c.username.unique
        assert User.__table__.c.email.unique
        assert not User.__table__.c.hashed_password.nullable
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


def test_identity_four_routes_and_shared_dependencies(tmp_path):
    _run_python(tmp_path, """
        from fastapi import routing
        from fastapi.routing import APIRoute
        from app.main import app
        from app.modules.identity.api import router
        from app.modules.identity.dependencies import get_current_user, bearer_scheme
        from app.core.database import get_db
        assert get_current_user.__module__ == "app.modules.identity.dependencies"
        assert get_current_user.__defaults__[0].dependency is bearer_scheme
        assert get_current_user.__defaults__[1].dependency is get_db
        expected = {
            ("/api/v1/auth/login", "POST"), ("/api/v1/auth/refresh", "POST"),
            ("/api/v1/auth/me", "GET"), ("/api/v1/auth/me", "PUT")
        }
        iterator = getattr(routing, "_iter_routes_with_context", None)
        included = iterator(app.routes) if iterator else ((r, None) for r in app.routes)
        routes = [(r, context if context is not None else r)
                  for r, context in included if isinstance(r, APIRoute)]
        auth = [(r, context) for r, context in routes
                if context.path.startswith("/api/v1/auth")]
        assert len(auth) == len(router.routes) == 4
        assert {(context.path, method) for r, context in auth for method in context.methods} == expected
        assert {r.endpoint for r, context in auth} == {r.endpoint for r in router.routes}
        guarded = []
        def walk(dependency):
            for child in dependency.dependencies:
                yield child
                yield from walk(child)
        for route, context in routes:
            for dependency in walk(route.dependant):
                if getattr(dependency.call, "__name__", None) == "get_current_user":
                    assert dependency.call is get_current_user, context.path
                    guarded.append(context.path)
        assert "/api/v1/auth/me" in guarded
        assert any(path.startswith("/api/v1/installations") for path in guarded)
        assert any(not path.startswith("/api/v1/auth") for path in guarded)
        for module in tuple(sys.modules.values()):
            if getattr(module, "__name__", "").startswith("app."):
                candidate = vars(module).get("get_current_user")
                if candidate is not None:
                    assert candidate is get_current_user
        """, forbidden=RETIRED_MODULES, block_engine=False)


def test_core_security_remains_domain_free_and_owns_primitives(tmp_path):
    security = BACKEND / "app/core/security.py"
    for _, modules in _imports(security):
        assert not any(
            name.startswith(("app.modules", "app.models", "app.schemas", "app.api"))
            for name in modules
        ), modules
    tree = ast.parse(security.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Name) and node.id in {"User", "Role"}
                   for node in ast.walk(tree))
    _run_python(tmp_path, """
        from app.core import security
        names = ("get_password_hash", "verify_password", "create_access_token",
                 "create_refresh_token", "decode_token")
        assert all(getattr(security, name).__module__ == "app.core.security"
                   for name in names)
        assert security.pwd_context.schemes() == ("bcrypt",)
        hashed = security.get_password_hash("identity-test-only-password")
        assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
        assert security.verify_password("identity-test-only-password", hashed)
        assert not security.verify_password("wrong-test-password", hashed)
        for kind, create in (("access", security.create_access_token),
                             ("refresh", security.create_refresh_token)):
            payload = security.decode_token(create(123))
            assert payload["sub"] == "123" and payload["type"] == kind
            assert payload["exp"] > payload["iat"]
        assert security.decode_token("not-a-jwt") is None
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.modules", "app.models", "app.schemas",
        ))


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # Reuse the real-JWT installation harness, but never its optional PostgreSQL.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bootstrap.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    from tests.test_installations import context as installation_context

    async for value in installation_context.__wrapped__(tmp_path):
        yield value


async def _login(context, role):
    from sqlalchemy import select
    from app.core.security import get_password_hash
    from app.modules.identity.models import User

    ac, sessions, _, _ = context
    async with sessions() as db:
        user = await db.scalar(select(User).where(User.role == role))
        user.hashed_password = get_password_hash("identity-test-only-password")
        await db.commit()
    response = await ac.post("/api/v1/auth/login", json={
        "username": role.value, "password": "identity-test-only-password",
    })
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert tokens["expires_in"] == 1800
    assert tokens["token_type"] == "bearer"
    return tokens


async def test_real_jwt_access_and_refresh_are_not_interchangeable(context):
    from app.modules.identity.models import Role

    ac, _, _, _ = context
    tokens = await _login(context, Role.TECHNICIAN)
    assert (await ac.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["access_token"],
    })).status_code == 401
    ac.headers["Authorization"] = "Bearer " + tokens["refresh_token"]
    assert (await ac.get("/api/v1/auth/me")).status_code == 401
    assert (await ac.get("/api/v1/installations")).status_code == 401
    refreshed = await ac.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["expires_in"] == 1800
    ac.headers["Authorization"] = "Bearer " + refreshed.json()["access_token"]
    assert (await ac.get("/api/v1/auth/me")).status_code == 200


async def test_disabling_user_invalidates_already_issued_tokens(context):
    from sqlalchemy import select
    from app.modules.identity.models import Role, User

    ac, sessions, _, _ = context
    tokens = await _login(context, Role.TECHNICIAN)
    async with sessions() as db:
        user = await db.scalar(select(User).where(User.role == Role.TECHNICIAN))
        user.is_active = False
        await db.commit()
    ac.headers["Authorization"] = "Bearer " + tokens["access_token"]
    assert (await ac.get("/api/v1/auth/me")).status_code == 401
    assert (await ac.put("/api/v1/auth/me", json={"full_name": "Blocked"})).status_code == 401
    assert (await ac.get("/api/v1/installations")).status_code == 401
    assert (await ac.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })).status_code == 401


@pytest.mark.parametrize("role_name", ["ADMIN", "TECHNICIAN"])
async def test_profiles_preserve_roles_and_never_expose_password_hash(context, role_name):
    from sqlalchemy import select
    from app.modules.identity.models import Role, User

    role = Role[role_name]
    ac, sessions, _, _ = context
    tokens = await _login(context, role)
    ac.headers["Authorization"] = "Bearer " + tokens["access_token"]
    before = await ac.get("/api/v1/auth/me")
    assert before.status_code == 200, before.text
    updated = await ac.put("/api/v1/auth/me", json={
        "full_name": "Identity Test", "email": f"{role.value}@identity.test",
        "role": "admin" if role == Role.TECHNICIAN else "technician",
        "is_active": False, "hashed_password": "not-a-real-hash",
    })
    assert updated.status_code == 200, updated.text
    for response in (before, updated, await ac.get("/api/v1/auth/me")):
        assert response.status_code == 200
        assert set(response.json()) == {
            "id", "username", "email", "full_name", "role", "is_active",
        }
        assert response.json()["role"] == role.value
        assert response.json()["is_active"] is True
    assert updated.json()["full_name"] == "Identity Test"
    async with sessions() as db:
        user = await db.scalar(select(User).where(User.role == role))
        assert user.role is role and user.is_active
        assert user.email == f"{role.value}@identity.test"
        assert user.hashed_password.startswith(("$2a$", "$2b$", "$2y$"))
