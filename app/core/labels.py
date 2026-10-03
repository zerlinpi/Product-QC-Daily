"""Chinese display labels, independent of persisted database codes."""

SOURCE_LABELS = {
    "manual": "手动录入",
    "excel": "表格导入",
    "demo": "演示数据",
    "production": "正式数据",
    "all": "全部数据",
}

IMPORT_STATUS_LABELS = {
    "valid": "正常",
    "duplicate": "重复",
    "conflict": "ID冲突",
    "invalid": "异常",
    "unrecognized": "无法识别",
}


def source_label(value: str) -> str:
    return SOURCE_LABELS.get(value, "未知来源")


def import_status_label(value: str) -> str:
    return IMPORT_STATUS_LABELS.get(value, "未知状态")


def imported_source(value) -> str:
    """Accept old exports and Chinese labels without promoting demo records."""
    value = str(value or "").strip()
    if value in ("demo", SOURCE_LABELS["demo"]):
        return "demo"
    if value in ("", "manual", "excel", SOURCE_LABELS["manual"], SOURCE_LABELS["excel"]):
        return "excel"
    raise ValueError(f"数据来源无法识别：{value}，请填写手动录入、表格导入或演示数据")
