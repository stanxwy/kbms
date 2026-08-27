"""知识单元与四维数据权限的 ORM 模型。"""

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from admin.models.base import Base, TimestampMixin


class KnowledgeUnit(TimestampMixin, Base):
    """知识单元（一个独立导入的文档/手册）。"""

    __tablename__ = "knowledge_units"

    # with_variant(Integer, "sqlite")：SQLite 仅 INTEGER PRIMARY KEY 具备自增
    # rowid 语义，BIGINT 不会自增，故测试库降级为 Integer，生产仍为 BIGSERIAL。
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    unit_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    creator_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)


class UnitPermission(TimestampMixin, Base):
    """知识单元数据权限（global/department/role/user 四类实体，OR 判定）。"""

    __tablename__ = "unit_permissions"

    # with_variant(Integer, "sqlite")：SQLite 仅 INTEGER PRIMARY KEY 具备自增
    # rowid 语义，BIGINT 不会自增，故测试库降级为 Integer，生产仍为 BIGSERIAL。
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_units.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
