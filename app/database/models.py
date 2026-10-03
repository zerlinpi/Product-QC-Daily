from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class DefectItem(Base):
    __tablename__ = "defect_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80), default="装配")
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"
    __table_args__ = (
        CheckConstraint("inspection_quantity > 0"),
        CheckConstraint("sampling_quantity > 0 AND sampling_quantity <= inspection_quantity"),
        CheckConstraint("defect_quantity >= 0 AND defect_quantity <= sampling_quantity"),
        CheckConstraint("judgment IN ('合格', '返工')"),
        CheckConstraint("source IN ('manual', 'excel', 'demo')"),
        Index("ix_record_scope_date", "deleted_at", "source", "inspection_date"),
        Index("ix_record_team_date", "team", "inspection_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_no: Mapped[str] = mapped_column(String(200), unique=True)
    inspection_date: Mapped[date] = mapped_column(Date, index=True)
    inspection_time: Mapped[time] = mapped_column(Time)
    team: Mapped[str] = mapped_column(ForeignKey("teams.name", onupdate="CASCADE"))
    work_order: Mapped[str] = mapped_column(String(200), index=True)
    inspection_quantity: Mapped[int] = mapped_column(Integer)
    sampling_quantity: Mapped[int] = mapped_column(Integer)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    judgment: Mapped[str] = mapped_column(String(10), index=True)
    inspector: Mapped[str] = mapped_column(String(100), index=True)
    signature_path: Mapped[str | None] = mapped_column(String(300))
    remark: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="manual")
    import_fingerprint: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    defects: Mapped[list["InspectionDefect"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="InspectionDefect.defect_id"
    )


class InspectionDefect(Base):
    __tablename__ = "inspection_defects"
    __table_args__ = (
        UniqueConstraint("inspection_id", "defect_id"),
        CheckConstraint("quantity IS NULL OR quantity > 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"), index=True
    )
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect_items.id"), index=True)
    quantity: Mapped[int | None] = mapped_column(Integer)
    remark: Mapped[str] = mapped_column(Text, default="")
    item: Mapped[DefectItem] = relationship(lazy="joined")


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    version: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
