"""路由层依赖注入装配。

当前仅转发核心依赖；认证/权限依赖在 T1 补充。
"""

from admin.core.deps import get_db

__all__ = ["get_db"]