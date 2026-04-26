"""Pytest configuration: pre-mock prefect so tests don't depend on it.

prefect==2.19.4 uses griffe.dataclasses which was removed in griffe 1.0.
We pin griffe<1.0 in requirements.txt, but as a belt-and-suspenders measure
we also stub prefect here so unit/integration tests stay fast and isolated
from the orchestration layer regardless of environment.
"""

import sys
from unittest.mock import MagicMock


def _make_prefect_mock() -> MagicMock:
    mock = MagicMock()

    def flow(**kwargs):
        def decorator(fn):
            return fn
        return decorator

    def task(**kwargs):
        def decorator(fn):
            return fn
        return decorator

    mock.flow = flow
    mock.task = task
    mock.get_run_logger.return_value = MagicMock()
    return mock


# Only inject the mock when the real prefect isn't importable cleanly.
try:
    import prefect  # noqa: F401
except Exception:
    sys.modules["prefect"] = _make_prefect_mock()
