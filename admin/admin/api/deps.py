"""路由层依赖注入装配。

转发核心依赖，供各路由统一 import。
"""

from admin.core.deps import CurrentUser, get_current_user, require_permissions
from admin.database import get_db

__all__ = ["get_db", "get_current_user", "require_permissions", "CurrentUser"]
