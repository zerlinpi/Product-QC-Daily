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
    issue_wb = load_workbook(report)
    issue_ws = issue_wb.active
    assert issue_ws.max_row == 4
    statuses = {issue_ws.cell(row, 4).value for row in range(2, issue_ws.max_row + 1)}
    assert statuses == {"重复", "异常", "无法识别"}
    assert not statuses & {"duplicate", "invalid", "unrecognized"}
    issue_wb.close()


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


@pytest.mark.parametrize("legacy", [False, True])
def test_export_full_timestamp_fits_and_stays_a_real_date(ctx, payload, tmp_path, legacy):
    from app.core.schemas import InspectionInput, RecordFilter

    stamp = datetime(2026, 12, 31, 23, 59, 59)
    ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "inspection_date": stamp.date(),
                    "inspection_time": stamp.time(),
                }
            )
        )
    )
    path = ctx.excel.export(tmp_path / "date.xlsx", RecordFilter(), legacy=legacy, prefer_com=False)
    wb = load_workbook(path)
    ws = wb["成品日检表" if legacy else "检验记录"]
    assert ws["B2"].value == stamp
    assert ws["B2"].is_date
    assert ws["B2"].number_format == "yyyy-mm-dd hh:mm:ss"
    assert ws.column_dimensions["B"].width >= 24
    wb.close()


@pytest.mark.parametrize("legacy", [False, True])
def test_chinese_source_exports_and_demo_roundtrip(ctx, payload, tmp_path, legacy):
    from app.core.context import AppContext
    from app.core.schemas import InspectionInput, RecordFilter

    for source in ("manual", "excel", "demo"):
        ctx.inspections.save(InspectionInput(**(payload.model_dump() | {"source": source})))
    path = ctx.excel.export(
        tmp_path / "sources.xlsx", RecordFilter(source="all"), legacy=legacy, prefer_com=False
    )
    wb = load_workbook(path)
    ws = wb["成品日检表" if legacy else "检验记录"]
    column = 14 if legacy else 13
    assert {ws.cell(r, column).value for r in range(2, 5)} == {"手动录入", "表格导入", "演示数据"}
    if not legacy:
        assert dict(wb["统计摘要"].values)["数据范围"] == "全部数据"
    wb.close()
    other = AppContext(tmp_path / "other-source")
    try:
        assert other.excel.import_preview(other.excel.preview(path)) == 3
        assert other.inspections.query(RecordFilter(source="demo"))[1] == 1
        assert other.inspections.query(RecordFilter())[1] == 2
    finally:
        other.db.dispose()


def test_legacy_layout_keeps_original_chart_positions_and_signature_cell(ctx, payload, tmp_path):
    from PIL import Image

    from app.core.schemas import InspectionInput, RecordFilter

    signature = tmp_path / "signature.png"
    Image.new("RGB", (400, 100), "white").save(signature)
    ctx.inspections.save(
        InspectionInput(**(payload.model_dump() | {"signature_path": str(signature)}))
    )
    path = ctx.excel.export(tmp_path / "layout.xlsx", RecordFilter(), legacy=True, prefer_com=False)
    wb = load_workbook(path)
    ws, analysis = wb["成品日检表"], wb["数据分析表"]
    assert [(c.anchor._from.col, c.anchor._from.row) for c in analysis._charts] == [
        (4, 12),
        (7, 4),
        (4, 17),
        (7, 34),
        (3, 49),
        (3, 42),
    ]
    assert analysis._charts[2].series[0].val.numRef.f.endswith("$B$4:$B$27")
    assert analysis._charts[3].series[0].val.numRef.f.endswith("$H$34:$K$34")
    assert ws.column_dimensions["A"].hidden
    assert ws.row_dimensions[2].height == pytest.approx(34.45)
    assert ws["C2"].font.name == "微软雅黑"
    anchor = ws._images[0].anchor
    assert (anchor._from.col, anchor._from.row) == (9, 1)
    assert (anchor._from.colOff + anchor.ext.cx) / 9525 <= ws.column_dimensions["J"].width * 7 + 5
    assert (anchor._from.rowOff + anchor.ext.cy) / 9525 <= ws.row_dimensions[2].height * 4 / 3
    wb.close()


@pytest.mark.parametrize(
    "value,expected",
    [("demo", "demo"), ("演示数据", "demo"), ("manual", "excel"), ("表格导入", "excel")],
)
def test_source_import_accepts_old_and_chinese_labels(ctx, tmp_path, value, expected):
    path = workbook(tmp_path / "source-input.xlsx", [row()])
    wb = load_workbook(path)
    wb.active["N1"], wb.active["N2"] = "数据来源", value
    wb.save(path)
    preview = ctx.excel.preview(path)
    assert preview.counts["valid"] == 1
    assert preview.rows[0].data.source == expected


def test_template_keeps_chart_design_and_removes_production_caches(ctx, payload, tmp_path):
    from copy import copy
    from zipfile import ZipFile

    from openpyxl.chart.data_source import NumData, NumVal

    from app.core.schemas import RecordFilter
    from app.services.excel_export import create_empty_template

    source, target = tmp_path / "private-template.xlsx", tmp_path / "blank-template.xlsx"
    wb = load_workbook(ctx.paths.template)
    wb["成品日检表"]["A2"] = "PRIVATE-PRODUCTION-RECORD"
    chart = wb["数据分析表"]._charts[0]
    chart.series[0].graphicalProperties.solidFill = "00AA44"
    chart.series[0].val.numRef.numCache = NumData(ptCount=1, pt=[NumVal(idx=0, v=123456789)])
    original_anchor = (copy(chart.anchor._from), copy(chart.anchor.to))
    wb.save(source)
    wb.close()
    before = source.read_bytes()
    create_empty_template(source, target)
    cleaned = load_workbook(target)
    assert (
        cleaned["数据分析表"]._charts[0].series[0].graphicalProperties.solidFill.srgbClr == "00AA44"
    )
    saved_anchor = cleaned["数据分析表"]._charts[0].anchor
    assert (saved_anchor._from, saved_anchor.to) == original_anchor
    assert cleaned["成品日检表"]["A2"].value is None
    assert source.read_bytes() == before
    with ZipFile(target) as archive:
        assert not any(name.startswith("xl/media/") for name in archive.namelist())
        for name in archive.namelist():
            if name.startswith("xl/charts/"):
                content = archive.read(name)
                assert b"123456789" not in content
                assert b"numCache" not in content
    cleaned.close()
    # Selecting an external populated template must not reuse its old chart values either.
    ctx.inspections.save(payload)
    ctx.settings.update({"template_path": str(source)})
    output = ctx.excel.export(
        tmp_path / "external.xlsx", RecordFilter(), legacy=True, prefer_com=False
    )
    with ZipFile(output) as archive:
        assert b"123456789" not in archive.read("xl/charts/chart1.xml")
