from datetime import datetime

import pytest
from openpyxl import Workbook, load_workbook

HEADERS = [
    "填写ID",
    "时间",
    "检验:组别",
    "检验:加工单号",
    "检验:检验数量",
    "检验:抽检数",
    "检验:不良数",
    "检验:不良项目",
    "检验:判定",
    "签名:图片",
]


def workbook(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "成品日检表"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def row(identifier="old-1", code="eg", defect=2):
    return [
        identifier,
        datetime(2023, 12, 31, 15, 30),
        "U1",
        "MO-001",
        100,
        20,
        defect,
        code,
        "合格",
    ]


def test_split_codes_without_inventing_quantities():
    from app.services.excel_import import parse_codes

    assert parse_codes("D.e.K.", set("abcdefghijklmnopqrstuvwx")) == ["d", "e", "k"]
    for value in ["α", "y", "1", "e.槽变形"]:
        with pytest.raises(ValueError):
            parse_codes(value, set("abcdefghijklmnopqrstuvwx"))


def test_import_preview_duplicates_conflicts_invalid_and_unknown(ctx, tmp_path):
    from app.core.schemas import RecordFilter

    path = workbook(
        tmp_path / "input.xlsx",
        [row(), row("old-2", "", None), row("bad", "y"), row("bad2", "e", 25), row()],
    )
    preview = ctx.excel.preview(path)
    assert preview.counts == {
        "valid": 2,
        "duplicate": 1,
        "conflict": 0,
        "invalid": 1,
        "unrecognized": 1,
    }
    assert ctx.inspections.query(RecordFilter())[1] == 0
    assert ctx.excel.import_preview(preview) == 2
    assert ctx.inspections.query(RecordFilter())[1] == 2
    imported = ctx.inspections.query(RecordFilter())[0]
    assert any(d["code"] == "g" and d["quantity"] is None for r in imported for d in r["defects"])
    assert ctx.excel.import_preview(ctx.excel.preview(path)) == 0
    changed = workbook(tmp_path / "changed.xlsx", [row(defect=3)])
    assert ctx.excel.preview(changed).counts["conflict"] == 1
    report = ctx.excel.export_issues(preview, tmp_path / "issues.xlsx")
    assert load_workbook(report).active.max_row == 4


def test_header_detection_prefers_visible_main(ctx, tmp_path):
    path = workbook(tmp_path / "input.xlsx", [row()])
    wb = load_workbook(path)
    other = wb.copy_worksheet(wb.active)
    other.title = "成品日检表报表"
    other.sheet_state = "hidden"
    wb.save(path)
    assert ctx.excel.preview(path).sheet == "成品日检表"
    assert ctx.excel.preview(path).counts["valid"] == 1


def test_standard_export_roundtrip_details_and_formula_text(ctx, payload, tmp_path):
    from app.core.schemas import InspectionInput, RecordFilter

    ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "work_order": "=1+1",
                    "defect_quantity": 2,
                    "defects": [
                        {"defect_id": 1, "quantity": 2},
                        {"defect_id": 24, "quantity": None},
                    ],
                }
            )
        )
    )
    path = ctx.excel.export(tmp_path / "standard.xlsx", RecordFilter(), legacy=False)
    wb = load_workbook(path)
    assert wb["检验记录"]["D2"].value == "=1+1"
    assert wb["检验记录"]["D2"].data_type == "s"
    assert wb["不良明细"].max_row == 3
    from app.core.context import AppContext

    other = AppContext(tmp_path / "other")
    preview = other.excel.preview(path)
    assert preview.counts["valid"] == 1
    other.excel.import_preview(preview)
    saved = other.inspections.query(RecordFilter())[0][0]
    assert [d["quantity"] for d in saved["defects"]] == [2, None]
    other.db.dispose()


def test_legacy_template_preserves_sheets_charts_and_correct_formulas(ctx, payload, tmp_path):
    from app.core.schemas import RecordFilter

    ctx.inspections.save(payload)
    path = ctx.excel.export(tmp_path / "legacy.xlsx", RecordFilter(), legacy=True, prefer_com=False)
    wb = load_workbook(path)
    assert wb.sheetnames[:4] == ["成品日检表报表", "成品日检表", "数据分析表", "工具"]
    assert len(wb["数据分析表"]._charts) == 6
    assert "SUMIFS" in wb["数据分析表"]["J4"].value
    assert '"*x*"' in wb["数据分析表"]["B27"].value
    assert "$B$4:$B$27" in wb["数据分析表"]["C4"].value
    assert "B34:B57" in wb["数据分析表"]["B58"].value
    assert wb["成品日检表"]["A2"].value.startswith("QC-")


def test_import_preview_changed_file_is_not_silently_used(ctx, tmp_path):
    path = workbook(tmp_path / "input.xlsx", [row()])
    preview = ctx.excel.preview(path)
    workbook(path, [row("new")])
    with pytest.raises(ValueError, match="改变"):
        ctx.excel.import_preview(preview)


def test_legacy_codes_remain_concatenated_after_adding_ambiguous_code(ctx, tmp_path):
    ctx.defects.save({"code": "eg", "name": "扩展项目"})
    path = workbook(tmp_path / "legacy-input.xlsx", [row()])
    preview = ctx.excel.preview(path)
    assert preview.counts["valid"] == 1
    assert [d.defect_id for d in preview.rows[0].data.defects] == [5, 7]


def test_legacy_demo_export_cannot_turn_into_production(ctx, payload, tmp_path):
    from app.core.context import AppContext
    from app.core.schemas import InspectionInput, RecordFilter

    ctx.inspections.save(InspectionInput(**(payload.model_dump() | {"source": "demo"})))
    path = ctx.excel.export(
        tmp_path / "demo-legacy.xlsx", RecordFilter(source="demo"), legacy=True, prefer_com=False
    )
    other = AppContext(tmp_path / "isolated")
    try:
        other.excel.import_preview(other.excel.preview(path))
        assert other.inspections.query(RecordFilter())[1] == 0
        assert other.inspections.query(RecordFilter(source="demo"))[1] == 1
    finally:
        other.db.dispose()
