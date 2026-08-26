"""ORM 模型聚合导出：确保所有模型注册到 Base.metadata（供 Alembic autogenerate）。

注意：user.py 与 org.py 之间存在循环外键（users.department_id ↔ departments.leader_id），
因此模型间未定义 ORM relationship，仅保留 ForeignKey 约束；如后续服务层需要导航关系，
可在对应模型上按需补充 `relationship(back_populates=...)`。
"""
from admin.models.base import Base, CreatedAtMixin, TimestampMixin
from admin.models.knowledge import KnowledgeUnit, UnitPermission
from admin.models.log import QaAccessLog
from admin.models.org import Department, Role, RolePermission
from admin.models.settlement import FAQ, KnowledgeGap
from admin.models.user import User, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "CreatedAtMixin",
    "User",
    "UserRole",
    "Department",
    "Role",
    "RolePermission",
    "KnowledgeUnit",
    "UnitPermission",
    "QaAccessLog",
    "FAQ",
    "KnowledgeGap",
]
