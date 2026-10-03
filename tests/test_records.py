import pytest
from sqlalchemy import text


def test_init_persistence_and_unique_ids(ctx, payload):
    from app.core.context import AppContext

    first = ctx.inspections.save(payload)
    second = ctx.inspections.save(payload)
    assert first["inspection_no"] != second["inspection_no"]
    assert len(ctx.defects.list()) == 24
    ctx.db.dispose()
    other = AppContext(ctx.paths.root)
    assert other.inspections.get(first["id"])["work_order"] == "MO-001"
    other.db.dispose()


def test_edit_multiple_defects_soft_delete_restore(ctx, payload):
    data = payload.model_dump()
    data.update(
        defect_quantity=2,
        defects=[{"defect_id": 1, "quantity": 2}, {"defect_id": 24, "quantity": 1}],
    )
    from app.core.schemas import InspectionInput, RecordFilter

    row = ctx.inspections.save(InspectionInput(**data))
    assert len(row["defects"]) == 2
    data.update(work_order="MO-002")
    edited = ctx.inspections.save(InspectionInput(**data), row["id"])
    assert edited["inspection_no"] == row["inspection_no"]
    assert edited["work_order"] == "MO-002"
    ctx.inspections.delete([row["id"]])
    assert ctx.inspections.query(RecordFilter())[1] == 0
    assert ctx.inspections.query(RecordFilter(deleted=True))[1] == 1
    ctx.inspections.restore([row["id"]])
    assert ctx.inspections.query(RecordFilter())[1] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"sampling_quantity": 101},
        {"defect_quantity": 21},
        {"defect_quantity": -1},
        {"work_order": "  "},
        {"inspection_quantity": 0},
        {"sampling_quantity": 1.5},
        {"defect_quantity": 1},
        {"defects": [{"defect_id": 1, "quantity": 1}]},
    ],
)
def test_invalid_quantities_and_missing_fields_rejected(ctx, payload, changes):
    from app.core.schemas import InspectionInput

    with pytest.raises(ValueError):
        ctx.inspections.save(InspectionInput(**(payload.model_dump() | changes)))


def test_invalid_defect_rolls_back_record_and_signature(ctx, payload, tmp_path):
    from PIL import Image

    from app.core.schemas import InspectionInput, RecordFilter

    signature = tmp_path / "sig.png"
    Image.new("RGB", (20, 20)).save(signature)
    data = payload.model_dump() | {
        "signature_path": str(signature),
        "defect_quantity": 1,
        "defects": [{"defect_id": 999, "quantity": 1}],
    }
    with pytest.raises(ValueError):
        ctx.inspections.save(InspectionInput(**data))
    assert ctx.inspections.query(RecordFilter())[1] == 0
    assert not list(ctx.paths.signatures.glob("*.png"))


def test_pagination_filters_bulk_and_dictionary_history(ctx, payload):
    from app.core.schemas import InspectionInput, RecordFilter

    ids = [
        ctx.inspections.save(
            InspectionInput(
                **(
                    payload.model_dump()
                    | {
                        "work_order": f"MO-{i:03}",
                        "defect_quantity": 1,
                        "defects": [{"defect_id": 24, "quantity": None}],
                    }
                )
            )
        )["id"]
        for i in range(7)
    ]
    rows, total = ctx.inspections.query(RecordFilter(page_size=3, page=2))
    assert total == 7 and len(rows) == 3
    ctx.inspections.bulk_update(ids[:2], team="U2", inspector="李工")
    assert ctx.inspections.query(RecordFilter(team="U2", inspector="李工"))[1] == 2
    assert ctx.inspections.query(RecordFilter(defect_id=24))[1] == 7
    ctx.defects.disable(24)
    assert ctx.inspections.get(ids[0])["defects"][0]["name"] == "端子深压"
    assert len(ctx.defects.list(enabled_only=True)) == 23
    with ctx.db.session() as s:
        assert s.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_signature_is_copied_and_source_not_required_after_save(ctx, payload, tmp_path):
    from PIL import Image

    from app.core.schemas import InspectionInput

    path = tmp_path / "original.png"
    Image.new("RGB", (100, 40), "white").save(path)
    saved = ctx.inspections.save(
        InspectionInput(**(payload.model_dump() | {"signature_path": str(path)}))
    )
    path.unlink()
    assert (ctx.paths.signatures / saved["signature_path"]).is_file()
