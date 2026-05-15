from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMetricMySQL(Base):
    # __tablename__ 一定要与数据库里面的表名"column_metric"要一样
    __tablename__ = "column_metric"

    column_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="列编号"
    )
    metric_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="指标编号"
    )