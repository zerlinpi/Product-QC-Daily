from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DefectInput(BaseModel):
    defect_id: int = Field(gt=0)
    quantity: int | None = Field(default=None, ge=1)
    remark: str = Field(default="", max_length=1000)


class InspectionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    inspection_date: date = Field(default_factory=date.today)
    inspection_time: time = Field(
        default_factory=lambda: datetime.now().time().replace(microsecond=0)
    )
    team: str = Field(min_length=1, max_length=80)
    work_order: str = Field(min_length=1, max_length=200)
    inspection_quantity: int = Field(gt=0, le=100_000_000)
    sampling_quantity: int = Field(gt=0, le=100_000_000)
    defect_quantity: int = Field(default=0, ge=0, le=100_000_000)
    judgment: Literal["合格", "返工"] = "合格"
    inspector: str = Field(min_length=1, max_length=100)
    signature_path: str | None = None
    remark: str = Field(default="", max_length=5000)
    source: Literal["manual", "excel", "demo"] = "manual"
    defects: list[DefectInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def quantities(self):
        if self.sampling_quantity > self.inspection_quantity:
            raise ValueError("抽检数不能超过检验数量")
        if self.defect_quantity > self.sampling_quantity:
            raise ValueError("不良数不能超过抽检数")
        if bool(self.defect_quantity) != bool(self.defects):
            raise ValueError("有不良数时请选择不良项目；没有不良数时不能选择不良项目")
        ids = [d.defect_id for d in self.defects]
        if len(ids) != len(set(ids)):
            raise ValueError("不良项目不可重复")
        if any(d.quantity is not None and d.quantity > self.defect_quantity for d in self.defects):
            raise ValueError("单项不良件数不能超过不良总件数")
        return self


class RecordFilter(BaseModel):
    start: date | None = None
    end: date | None = None
    team: str = ""
    work_order: str = ""
    inspector: str = ""
    judgment: str = ""
    defect_id: int | None = None
    has_defects: bool | None = None
    search: str = ""
    source: Literal["production", "demo", "all"] = "production"
    deleted: bool = False
    ids: list[int] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort: str = "inspection_date"
    descending: bool = True

    @model_validator(mode="after")
    def range_order(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("开始日期不能晚于结束日期")
        return self

    @field_validator("judgment")
    @classmethod
    def valid_judgment(cls, value):
        if value not in ("", "合格", "返工"):
            raise ValueError("判定无效")
        return value
