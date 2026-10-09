"""Compare supplied original templates with synthetic exports; never alter inputs."""

import argparse
import hashlib
import json
import tempfile
from copy import copy
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from app.core.context import AppContext
from app.core.schemas import RecordFilter
from app.services.excel_common import load_compatible


def audit(paths):
    results = []
    with tempfile.TemporaryDirectory(prefix="qc-template-audit-") as folder:
        ctx = AppContext(Path(folder))
        try:
            filters = RecordFilter(
                start="2026-01-01", end="2026-12-31", source="demo", descending=False
            )
            ctx.demo.generate(1825, filters.start, filters.end, ["U1", "U2", "U3"], seed=20261008)
            for path in paths:
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                original = load_compatible(path)
                ctx.settings.update({"template_path": str(path.resolve())})
                output = ctx.excel.export(
                    Path(folder) / "result.xlsx", filters, legacy=True, prefer_com=False
                )
                result = load_compatible(output)
                try:
                    assert result.sheetnames == original.sheetnames
                    for name in result.sheetnames:
                        target, source = result[name], original[name]
                        allowed_columns = {
                            "成品日检表": {"N", "O"}, "工具": {"D", "E", "F"},
                        }.get(name, set())
                        assert set(target.column_dimensions) - set(source.column_dimensions) <= allowed_columns
                        assert target.page_margins == source.page_margins
                        assert target.page_setup == source.page_setup
                        assert target.merged_cells == source.merged_cells
                        for key, dimension in source.column_dimensions.items():
                            if name == "成品日检表" and key == "N":
                                continue  # Existing hidden source metadata column.
                            for attr in (
                                "width",
                                "hidden",
                                "min",
                                "max",
                                "bestFit",
                                "outlineLevel",
                                "collapsed",
                            ):
                                assert getattr(target.column_dimensions[key], attr) == getattr(
                                    dimension, attr
                                ), (name, key, attr)
                    target, source = result["成品日检表"], original["成品日检表"]
                    for row in (2, 500, 501, 502, 1826):
                        if target.cell(row, 8).value:
                            assert source.row_dimensions[2].height <= target.row_dimensions[row].height <= 409.5
                        else:
                            assert target.row_dimensions[row].height == source.row_dimensions[2].height
                        for column in range(1, 12):
                            a, b = target.cell(row, column), source.cell(2, column)
                            for attr in (
                                "font",
                                "border",
                                "fill",
                                "alignment",
                                "number_format",
                                "protection",
                            ):
                                expected = copy(getattr(b, attr))
                                if column == 8 and attr == "alignment" and a.value:
                                    expected.wrap_text = True  # Chinese names now wrap within original width.
                                assert copy(getattr(a, attr)) == expected, (
                                    row,
                                    column,
                                    attr,
                                )
                    assert target.print_area == "'成品日检表'!$B$1:$K$1826"
                    assert target.print_title_rows == "$1:$1"
                    assert target.freeze_panes == "C2" and target.sheet_view.topLeftCell == "A1"
                    charts, old = result["数据分析表"]._charts, original["数据分析表"]._charts
                    assert len(charts) == len(old) == 6
                    for chart_index, (a, b) in enumerate(zip(charts, old, strict=True), 1):
                        assert type(a) is type(b)
                        assert a.anchor._from == b.anchor._from and a.anchor.to == b.anchor.to
                        assert a.style == b.style
                        assert a.graphical_properties == b.graphical_properties
                        assert a.series[0].graphicalProperties == b.series[0].graphicalProperties

                        # Compare serialized axes: openpyxl's reload turns empty
                        # dummy text runs into the Python string "None". The actual
                        # OOXML still contains empty text, not that string.
                        def semantic(node):
                            return (
                                node.tag.rsplit("}", 1)[-1],
                                dict(node.attrib),
                                node.text or "",
                                [semantic(c) for c in node],
                            )

                        with ZipFile(output) as archive:
                            xml = ET.fromstring(archive.read(f"xl/charts/chart{chart_index}.xml"))
                        for axis_name, tag in (("x_axis", "catAx"), ("y_axis", "valAx")):
                            actual = xml.find(
                                f".//{{http://schemas.openxmlformats.org/drawingml/2006/chart}}{tag}"
                            )
                            expected = getattr(b, axis_name).to_tree()
                            assert semantic(actual) == semantic(expected), (chart_index, axis_name)
                    with ZipFile(path) as archive:
                        wps_objects = "xl/cellimages.xml" in archive.namelist()
                    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
                    results.append(
                        {
                            "template": path.name,
                            "sha256": before,
                            "records": 1825,
                            "sheets": 4,
                            "charts": 6,
                            "layout_styles_print_views": "PASS",
                            "authorized_display_change": "不良项目显示中文；仅有内容的 H 列换行并按需增加行高",
                            "source_unchanged": True,
                            "wps_private_image_objects": wps_objects,
                            "office_visual_acceptance": "未完成实机验收",
                        }
                    )
                finally:
                    result.close()
                    original.close()
        finally:
            ctx.db.dispose()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("templates", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.templates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
