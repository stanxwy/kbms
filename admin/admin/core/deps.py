"""依赖注入装配：当前用户、RBAC 校验等。

完整实现见实施任务分解 T1（认证与组织架构）；P0 仅建立模块骨架。
数据库会话依赖可直接复用 `admin.database.get_db`。
"""

from admin.database import get_db

__all__ = ["get_db"]