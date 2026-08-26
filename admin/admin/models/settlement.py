"""知识沉淀相关模型：FAQ 与知识缺口。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from admin.models.base import Base, TimestampMixin


class FAQ(TimestampMixin, Base):
    """标准问答对（FAQ 缓存，命中直接返回答）。"""

    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_unit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_units.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending_review", server_default="pending_review", index=True
    )
    hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeGap(TimestampMixin, Base):
    """知识缺口（未命中/低置信度提问的聚类）。"""

    __tablename__ = "knowledge_gaps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    sample_questions_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ask_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unresolved", server_default="unresolved", index=True
    )
    resolved_unit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_units.id"), nullable=True
    )