"""Async database engine and session management."""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)  #连接数据库

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
) #配置并创建一个“会话工厂”

logger.info(
    "Database engine created: pool_size=%d, max_overflow=%d, pool_pre_ping=%s",
    20, 10, True,
)


class Base(DeclarativeBase):  #它内部自带了所有和数据库通信、映射、管理元数据（Metadata）的黑科技
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session  #负责把session借出给他的业务代码，函数会卡在这一行暂停执行，静静地等待业务代码把数据库操作
        finally:
            await session.close()
