"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create async engine
database_uri = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(database_uri, echo=settings.DATABASE_ECHO, future=True)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
