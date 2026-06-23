"""Alembic 环境配置 —— 自动探测路径、显式注册模型、全量对比迁移."""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# 1. 根据当前文件位置推算项目根目录（backend/）并加入 sys.path
#    不再依赖 PYTHONPATH 环境变量或入口脚本的 cd 行为
# ---------------------------------------------------------------------------
# alembic/env.py  →  两级往上 = backend/
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 显式设置 CWD 为 backend，保证相对路径一致（如日志目录）
os.chdir(_project_root)

# ---------------------------------------------------------------------------
# 2. 导入应用配置 & 显式注册所有模型（确保 autogenerate 不漏表）
# ---------------------------------------------------------------------------
from app.config import settings           # noqa: E402
from app.database import Base             # noqa: E402

# 逐个显式导入，比 import app.models 更可靠
from app.models.project import Project                                    # noqa: E402,F401
from app.models.outline import Outline                                    # noqa: E402,F401
from app.models.character import Character                                # noqa: E402,F401
from app.models.chapter import Chapter                                    # noqa: E402,F401
from app.models.relationship import (                                     # noqa: E402,F401
    CharacterRelationship, Organization, OrganizationMember, Career,
)
from app.models.generation import GenerationHistory                       # noqa: E402,F401
from app.models.memory import StoryMemory, PlotAnalysis                   # noqa: E402,F401
from app.models.foreshadow import Foreshadow                              # noqa: E402,F401
from app.models.writing_style import WritingStyle                         # noqa: E402,F401
from app.models.mcp_plugin import MCPPlugin                               # noqa: E402,F401
from app.models.prompt_template import PromptTemplate                     # noqa: E402,F401
from app.models.background_task import BackgroundTask                     # noqa: E402,F401
from app.models.inspiration import Inspiration                            # noqa: E402,F401
from app.models.settings_model import SettingsModel, APIPreset            # noqa: E402,F401

# ---------------------------------------------------------------------------
# 3. Alembic 配置
# ---------------------------------------------------------------------------
config = context.config

# 从应用配置读取数据库 URL（而非 alembic.ini 中的静态值）
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式 —— 生成 SQL 而非直接执行."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在线模式 —— 核心迁移逻辑."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,              # 检测列类型变更
        compare_server_default=True,    # 检测默认值变更
        render_as_batch=False,          # PostgreSQL 原生 ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步迁移 —— 适配 asyncpg 引擎."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
