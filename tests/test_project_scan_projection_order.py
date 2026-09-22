from __future__ import annotations

import inspect

from testamur.project_supply_chain_projection import project_supply_chain_projections


def test_cross_binding_projection_orders_by_observation_time_not_record_ordinal() -> None:
    source = inspect.getsource(project_supply_chain_projections)
    assert "ORDER BY rev.recorded_at DESC, rev.revision_id DESC" in source
    assert "ORDER BY rev.ordinal DESC" not in source
