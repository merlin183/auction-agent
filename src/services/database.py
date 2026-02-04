"""데이터베이스 서비스"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

import sys
sys.path.append("..")
from config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy Base"""
    pass


class DatabaseService:
    """비동기 데이터베이스 서비스"""

    def __init__(self, database_url: Optional[str] = None):
        settings = get_settings()
        self.database_url = database_url or settings.database_url

        self.engine = create_async_engine(
            self.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """테이블 생성"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """테이블 삭제"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """세션 컨텍스트 매니저"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """연결 종료"""
        await self.engine.dispose()


# 싱글톤 인스턴스
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """데이터베이스 서비스 싱글톤 반환"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
