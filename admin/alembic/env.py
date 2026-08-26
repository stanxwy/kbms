"""Alembic 迁移环境：读取 DATABASE_SYNC_URL，目标元数据为 Base.metadata。"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 确保 `import admin` 可解析（无论从 admin/ 目录还是仓库根启动）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin.config import get_settings  # noqa: E402
from admin.models import Base  # noqa: E402,F401  # 触发所有模型注册

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 用同步 DSN 执行迁移（asyncpg 无法被 Alembic 直接使用）。
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_SYNC_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 而不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库并执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
