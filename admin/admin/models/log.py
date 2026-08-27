"""问答访问日志（事实表，只增不改）的 ORM 模型。"""

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from admin.models.base import Base, CreatedAtMixin

# 生产库使用 JSONB；SQLite（测试）降级为通用 JSON 类型，使 qa_access_logs
# 表可在 aiosqlite 下创建，从而为看板聚合提供可单测的底座（驼同 BigInteger 的 with_variant 先例）。
_JSONField = JSONB().with_variant(JSON(), "sqlite")


class QaAccessLog(CreatedAtMixin, Base):
    """每轮鉴权问答的事实记录，供看板与沉淀异步聚合。"""

    __tablename__ = "qa_access_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    recalled_unit_ids_json: Mapped[list | None] = mapped_column(_JSONField, nullable=True)
    authorized_unit_ids_json: Mapped[list | None] = mapped_column(_JSONField, nullable=True)
    unauthorized_unit_ids_json: Mapped[list | None] = mapped_column(_JSONField, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
