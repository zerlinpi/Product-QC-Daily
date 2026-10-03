import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def ctx(tmp_path):
    from app.core.context import AppContext

    context = AppContext(tmp_path)
    yield context
    context.db.dispose()


@pytest.fixture
def payload():
    from app.core.schemas import InspectionInput

    return InspectionInput(
        inspection_date="2026-01-05",
        team="U1",
        work_order="MO-001",
        inspection_quantity=100,
        sampling_quantity=20,
        defect_quantity=0,
        judgment="合格",
        inspector="张工",
    )
