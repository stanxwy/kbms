"""ORM 声明基类与通用时间戳 MIXIN。"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类（迁移目标元数据由它聚合）。"""


class TimestampMixin:
    """追加 created_at / updated_at（TIMESTAMPTZ，DEFAULT now()）的通用 MIXIN。"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """仅追加 created_at（TIMESTAMPTZ）的 MIXIN，用于只增不改的事实表。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
