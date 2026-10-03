"""Read-only media routes must not take mutation locks."""
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.parametrize("module", ["photos", "materials"])
@pytest.mark.parametrize("for_update", [False, True])
async def test_parent_lookup_only_locks_mutations(module, for_update):
    router = import_module("app.modules.interventions.api." + module)
    parent = object()
    result = MagicMock()
    result.scalar_one_or_none.return_value = parent
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    assert await router._get_intervention_or_404(db, 1, for_update=for_update) is parent
    query = db.execute.await_args.args[0]
    assert (query._for_update_arg is not None) == for_update
    if for_update:
        assert query.get_execution_options()["populate_existing"] is True
