"""Actionable validation messages shared by entry forms and Excel previews."""

from pydantic import ValidationError

FIELD_LABELS = {
    "inspection_date": "检验日期",
    "inspection_time": "检验时间",
    "team": "组别",
    "work_order": "加工单号",
    "inspector": "检验员",
    "inspection_quantity": "检验数量",
    "sampling_quantity": "抽检数量",
    "defect_quantity": "不良件数",
    "judgment": "检验判定",
    "remark": "备注",
    "signature_path": "签名图片",
    "source": "数据来源",
    "defects": "不良项目",
    "defect_id": "不良项目",
    "quantity": "件数",
    "start": "开始日期",
    "end": "结束日期",
}


def validation_message(error: ValidationError) -> str:
    messages = []
    for issue in error.errors(include_url=False, include_input=False):
        location, kind, context = issue["loc"], issue["type"], issue.get("ctx", {})
        name = FIELD_LABELS.get(location[-1], "输入内容") if location else "检验记录"
        if len(location) >= 3 and location[0] == "defects":
            name = f"第 {location[1] + 1} 个不良项目的{name}"
        if kind == "missing" or kind == "string_too_short":
            reason = "不能为空，请填写或选择此项"
        elif kind == "string_too_long":
            reason = f"不能超过 {context['max_length']} 个字符"
        elif kind in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
            operator, key = {
                "greater_than": ("必须大于", "gt"),
                "greater_than_equal": ("不能小于", "ge"),
                "less_than": ("必须小于", "lt"),
                "less_than_equal": ("不能大于", "le"),
            }[kind]
            reason = f"{operator} {context[key]}"
        elif kind.startswith("int_"):
            reason = "请填写有效的整数"
        elif kind.startswith("date"):
            reason = "请填写有效日期，例如 2026-10-03"
        elif kind.startswith("time"):
            reason = "请填写有效时间，例如 08:30:00"
        elif kind == "literal_error" and location == ("judgment",):
            reason = "请选择合格或返工"
        elif kind == "value_error":
            reason = str(context.get("error", "请检查填写内容"))
        else:
            reason = "格式不正确，请检查填写内容"
        messages.append(f"{name}：{reason}")
    return "请修改以下内容后再保存：\n" + "\n".join(messages)
