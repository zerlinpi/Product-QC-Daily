import logging
import os
from copy import copy
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.units import pixels_to_EMU
from openpyxl.workbook.properties import CalcProperties

from app.core.labels import source_label
from app.services.excel_common import load_compatible, write_text

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
    "检验员",
    "备注",
    "数据来源",
]


def style_table(ws):
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(name="Microsoft YaHei", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="253D75")
        cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(42, max(15, len(str(col[0].value or "")) * 2 + 4))


def add_signature(ws, index: int, path: Path, preserve_height=False):
    if not path.is_file():
        raise ValueError(f"签名图片丢失：{path.name}，请补充后再导出")
    image = Image(BytesIO(path.read_bytes()))
    if not preserve_height:
        ws.row_dimensions[index].height = max(ws.row_dimensions[index].height or 18, 40)
    width = (ws.column_dimensions["J"].width or 13) * 7 + 5
    height = (ws.row_dimensions[index].height or ws.sheet_format.defaultRowHeight) * 4 / 3
    scale = min(max(1, width - 8) / image.width, max(1, height - 8) / image.height, 1)
    image.width, image.height = image.width * scale, image.height * scale
    image.anchor = OneCellAnchor(
        _from=AnchorMarker(
            col=9,
            row=index - 1,
            colOff=pixels_to_EMU((width - image.width) / 2),
            rowOff=pixels_to_EMU((height - image.height) / 2),
        ),
        ext=XDRPositiveSize2D(pixels_to_EMU(image.width), pixels_to_EMU(image.height)),
    )
    ws.add_image(image)


def repair_analysis(wb, start: date, end: date, record_count: int):
    ws = wb["数据分析表"]
    last = max(record_count + 1, 2)
    dates = f"'成品日检表'!$B$2:$B${last}"
    codes = f"'成品日检表'!$H$2:$H${last}"
    groups = f"'成品日检表'!$C$2:$C${last}"
    judgments = f"'成品日检表'!$I$2:$I${last}"
    ws["L2"], ws["M2"] = start, end
    week_start = end - timedelta(days=end.weekday())
    ws["L32"], ws["M32"] = week_start, week_start + timedelta(days=6)
    ws["L1"], ws["M1"] = "开始日期（含）", "结束日期（含）"
    ws["L31"], ws["M31"] = "周开始（含）", "周结束（含）"
    ws["A2"] = '=IF(AND(YEAR(L2)=YEAR(M2),MONTH(L2)=MONTH(M2)),MONTH(L2),"区间")'
    ws["A32"] = "=WEEKNUM(L32,21)"
    for cell in ("L2", "M2", "L32", "M32"):
        ws[cell].number_format = "yyyy-mm-dd"
    for first, total_row, control in ((4, 28, 2), (34, 58, 32)):
        date_args = f'{dates},">="&$L${control},{dates},"<"&($M${control}+1)'
        ws.cell(control, 2, "月出货抽检不良统计表" if first == 4 else "周出货抽检不良统计表")
        for i in range(24):
            r, code = first + i, chr(97 + i)
            ws.cell(r, 2, f'=COUNTIFS({date_args},{codes},"*{code}*")')
            ws.cell(r, 3, f"=RANK(B{r},$B${first}:$B${first + 23},0)")
        ws.cell(total_row, 2, f"=SUM(B{first}:B{first + 23})")
        for i in range(8):
            r = first + i
            ws.cell(r, 6, f'=COUNTIFS({date_args},{groups},E{r},{judgments},"返工")')
        ws.cell(first + 8, 6, f"=SUM(F{first}:F{first + 7})")
        for target, source in (("H", "E"), ("I", "F"), ("J", "G")):
            ws[f"{target}{first}"] = (
                f"=SUMIFS('成品日检表'!${source}$2:${source}${last},{date_args})"
            )
        ws[f"K{first}"] = f"=IFERROR(J{first}/I{first},0)"
        ws[f"K{first}"].number_format = "0.00%"
    ws["A61"] = "项目统计为出现批次；不良率=不良件数/抽检件数。逐项已知数量见标准报表。"
    for column in ("L", "M"):
        ws.column_dimensions[column].width = max(ws.column_dimensions[column].width, 12)
        for row in (1, 31):
            ws.cell(row, 12 if column == "L" else 13).alignment = Alignment(
                wrap_text=True, vertical="center"
            )
    ws.data_validations.dataValidation.clear()
    wb.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True, forceFullCalc=True)


def recalculate_com(path: Path) -> bool:
    if os.name != "nt":
        return False
    excel = workbook = None
    initialized = False
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        initialized = True
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3
        workbook = excel.Workbooks.Open(str(path.resolve()), UpdateLinks=0, ReadOnly=False)
        excel.CalculateFullRebuild()
        workbook.Save()
        return True
    except Exception:
        logging.getLogger("qc.excel").info("Excel COM 不可用，保留 openpyxl 导出", exc_info=True)
        return False
    finally:
        # A crashed Excel process can also fail during cleanup. Keep the
        # already-generated workbook and still release the remaining resources.
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:
                logging.getLogger("qc.excel").warning("关闭 Excel 工作簿失败", exc_info=True)
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                logging.getLogger("qc.excel").warning("退出 Excel 失败", exc_info=True)
        if initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                logging.getLogger("qc.excel").warning("释放 Excel 组件失败", exc_info=True)


def export_workbook(ctx, path: Path, filters, legacy=False, prefer_com=True) -> Path:
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        raise ValueError("导出文件必须使用 .xlsx 扩展名")
    path.parent.mkdir(parents=True, exist_ok=True)
    if legacy:
        template = Path(ctx.settings.get("template_path") or ctx.paths.template)
        if not template.is_file():
            raise ValueError("Excel 模板不存在，请在设置中选择正确模板")
        if path.resolve() == template.resolve():
            raise ValueError("导出不能覆盖模板，请选择新文件名")
        wb = load_compatible(template)
        if not {"成品日检表", "成品日检表报表", "数据分析表", "工具"} <= set(wb.sheetnames):
            raise ValueError("模板缺少必要工作表")
        ws = wb["成品日检表"]
        write_text(ws["N1"], "数据来源")
        ws.column_dimensions["N"].hidden = True
        row_style = [copy(c._style) for c in ws[2]]
        row_height = ws.row_dimensions[2].height or ws.sheet_format.defaultRowHeight
        for name in ("成品日检表", "成品日检表报表"):
            sheet = wb[name]
            sheet.delete_rows(2, max(sheet.max_row - 1, 1))
            sheet._images.clear()
            for index in list(sheet.row_dimensions):
                if index > 1:
                    del sheet.row_dimensions[index]
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "检验记录"
        ws.append(HEADERS)
        detail = wb.create_sheet("不良明细")
        detail.append(["填写ID", "编码", "名称", "已知件数（空=未知）", "备注"])
        dictionary = wb.create_sheet("不良项目")
        dictionary.append(["编码", "名称", "分类", "启用", "排序", "说明"])
        for item in ctx.defects.list():
            dictionary.append(
                [
                    item["code"],
                    item["name"],
                    item["category"],
                    item["enabled"],
                    item["sort_order"],
                    item["description"],
                ]
            )
    count, minimum, maximum = 0, None, None
    for count, row in enumerate(ctx.inspections.iter_records(filters), 1):
        index = count + 1
        codes = [d["code"] for d in row["defects"]]
        if legacy and any(
            len(code) != 1 or code not in "abcdefghijklmnopqrstuvwx" for code in codes
        ):
            raise ValueError("该记录含扩展编码，请选择标准报表；旧版仅支持 a–x")
        stamp = datetime.fromisoformat(f"{row['inspection_date']}T{row['inspection_time']}")
        minimum = min(minimum, stamp.date()) if minimum else stamp.date()
        maximum = max(maximum, stamp.date()) if maximum else stamp.date()
        values = [
            row["inspection_no"],
            stamp,
            row["team"],
            row["work_order"],
            row["inspection_quantity"],
            row["sampling_quantity"],
            row["defect_quantity"],
            ("" if legacy else ";").join(codes),
            row["judgment"],
            "",
        ]
        if not legacy:
            values += [row["inspector"], row["remark"], source_label(row["source"])]
        for col, value in enumerate(values, 1):
            cell = ws.cell(index, col)
            write_text(cell, value)
            if legacy and col <= len(row_style):
                cell._style = copy(row_style[col - 1])
        ws.cell(index, 2).number_format = "yyyy-mm-dd hh:mm:ss"
        if legacy:
            write_text(ws.cell(index, 14), source_label(row["source"]))
            ws.row_dimensions[index].height = row_height
        if row["signature_path"]:
            add_signature(ws, index, ctx.paths.signatures / row["signature_path"], legacy)
        if not legacy:
            for d in row["defects"]:
                detail.append(
                    [row["inspection_no"], d["code"], d["name"], d["quantity"], d["remark"]]
                )
    if legacy:
        # The hidden duplicate is intentionally empty to avoid two copies being imported.
        repair_analysis(
            wb,
            filters.start or minimum or date.today(),
            filters.end or maximum or date.today(),
            count,
        )
        for chart in wb["数据分析表"]._charts:
            clear_chart_caches(chart)
            repair_chart_ranges(chart)
        ws.freeze_panes = "C2"
    else:
        summary = wb.create_sheet("统计摘要")
        summary.append(["指标", "数值"])
        labels = {
            "batches": "检验批次",
            "inspection_quantity": "检验数量",
            "sampling_quantity": "抽检数量",
            "defect_quantity": "不良件数",
            "defect_rate": "不良率",
            "rework_batches": "返工批次",
            "rework_rate": "返工率",
            "pass_batches": "合格批次",
            "pass_rate": "合格率",
        }
        for key, value in ctx.statistics.summary(filters).items():
            summary.append([labels.get(key, key), value])
            if key.endswith("rate"):
                summary.cell(summary.max_row, 2).number_format = "0.00%"
        summary.append(["口径", "不良率=不良件数/抽检件数；项目件数未知保留空白，多缺陷可重叠。"])
        summary.append(["数据范围", source_label(filters.source)])
        for sheet in wb:
            for cells in sheet:
                for cell in cells:
                    if cell.data_type == "f":
                        cell.data_type = "s"
            style_table(sheet)
    # A full timestamp needs more room than the short date in the old template.
    # Apply this after standard table styling, which otherwise resets B to 15.
    ws.column_dimensions["B"].width = max(ws.column_dimensions["B"].width, 26)
    with NamedTemporaryFile(suffix=".xlsx", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        wb.save(temp)
        wb.close()
        if legacy and prefer_com:
            recalculate_com(temp)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    logging.getLogger("qc.excel").info("导出 %s rows=%s legacy=%s", path, count, legacy)
    return path


def clear_chart_caches(chart):
    """Keep native chart formatting while removing saved production values."""
    sources = [chart.title.tx] if chart.title and chart.title.tx else []
    for series in chart.series:
        sources.extend(
            getattr(series, name, None)
            for name in ("cat", "val", "xVal", "yVal", "bubbleSize", "tx")
        )
    for source in sources:
        for reference in ("numRef", "strRef", "multiLvlStrRef"):
            ref = getattr(source, reference, None)
            for cache in ("numCache", "strCache", "multiLvlStrCache"):
                if ref is not None and hasattr(ref, cache):
                    setattr(ref, cache, None)


def repair_chart_ranges(chart):
    """Preserve the source design without restoring its known range bugs."""
    for series in chart.series:
        for data in (series.cat, series.val):
            if data is None:
                continue
            for name in ("numRef", "strRef"):
                ref = getattr(data, name, None)
                if ref is None or not ref.f:
                    continue
                ref.f = ref.f.replace("$A$4:$A$24", "$A$4:$A$27").replace(
                    "$B$4:$B$24", "$B$4:$B$27"
                )
                if getattr(chart.anchor, "_from", None) and chart.anchor._from.row >= 30:
                    ref.f = ref.f.replace("$H$3:$K$3", "$H$33:$K$33").replace(
                        "$H$4:$K$4", "$H$34:$K$34"
                    )
    # The source's weekly chart accidentally included the ranking column as
    # quantities. A zero-defect week must not show a bar of 1 for every defect.
    rank_ranges = {"数据分析表!$C$4:$C$27", "数据分析表!$C$34:$C$57"}
    chart.series = [
        series
        for series in chart.series
        if not (
            series.val and series.val.numRef and series.val.numRef.f.replace("'", "") in rank_ranges
        )
    ]


def create_empty_template(source: Path, target: Path) -> None:
    """Developer utility: preserve the layout but remove ALL production content."""
    wb = load_compatible(source)
    for name in ("成品日检表", "成品日检表报表"):
        ws = wb[name]
        for cells in ws.iter_rows(min_row=2):
            for cell in cells:
                cell.value = None
        ws.delete_rows(3, ws.max_row)
        ws._images.clear()
        for index in list(ws.row_dimensions):
            if index > 2:
                del ws.row_dimensions[index]
    analysis = wb["数据分析表"]
    analysis.delete_rows(62, max(analysis.max_row - 61, 1))
    analysis["M17"] = None  # An unused scratch calculation from the source data.
    for chart in analysis._charts:
        clear_chart_caches(chart)
        repair_chart_ranges(chart)
    repair_analysis(wb, date(2026, 1, 1), date(2026, 1, 31), 0)
    wb.properties.creator = "Product-QC-Daily"
    wb.properties.lastModifiedBy = "Product-QC-Daily"
    target.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target)
    wb.close()
