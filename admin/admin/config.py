"""应用配置：Pydantic Settings 读取环境变量与 `.env`。

.env 解析相对本文件，使 `uvicorn admin.main:app` 无论从仓库根目录还是
`admin/` 目录（`cd admin` 后 `uvicorn admin.main:app`）启动都能正确加载默认值。
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用 =====
    APP_NAME: str = "KBMS Admin"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # ===== 数据库 =====
    DATABASE_URL: str = "postgresql+asyncpg://kbms:kbms@localhost:5432/kbms"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://kbms:kbms@localhost:5432/kbms"

    # ===== RAG 集成 =====
    RAG_BASE_URL: str = "http://localhost:8000"

    # ===== JWT =====
    JWT_SECRET: str = "please-change-me-to-a-32-char-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_MIN: int = 30
    JWT_REFRESH_TTL_DAY: int = 14

    # ===== 初始超管 =====
    INITIAL_SUPERUSER_USERNAME: str = "admin"
    INITIAL_SUPERUSER_PASSWORD: str = "admin123"
    INITIAL_SUPERUSER_EMAIL: str = "admin@example.com"

    # ===== FAQ 沉淀 =====
    FAQ_MIN_FREQ_THRESHOLD: int = 5
    FAQ_MIN_WINDOW_DAYS: int = 7
    FAQ_MINER_INTERVAL_MIN: int = 60
    FAQ_MATCH_THRESHOLD: float = 0.85

    # ===== CORS =====
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """逗号分隔的 CORS 来源转列表。"""
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回单例配置。"""
    return Settings()
