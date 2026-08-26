"""鉴权与安全：JWT 签发/校验、密码散列。

密码散列采用 bcrypt、JWT 采用 python-jose（依赖已在 pyproject.toml 声明）。
JWT 签发/校验的完整实现见实施任务分解 T1.1；此处仅提供种子数据所需的密码散列函数。
"""
import bcrypt


def hash_password(plain: str) -> str:
    """对明文密码做 bcrypt 散列，返回可直接落库的字符串。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与散列是否匹配（常量时间比较）。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))