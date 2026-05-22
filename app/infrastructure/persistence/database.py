from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from ..config.settings import get_settings
from .models.base import Base

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session

    Usage:
        async def my_function(db: AsyncSession = Depends(get_db)):
            # Use db session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialise database - create all tables"""
    # Import models
    from .models import (
        UserModel,
        DocumentModel,
        DocumentChunkModel,
        ChatSessionModel,
        ChatMessageModel,
        ChatTriageModel,
        TicketModel,
        TicketActivityModel,
        LibraryFolderModel,
        LibraryFileModel,
    )

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        print("Database tables created successfully")


async def drop_all_tables():
    """Drop all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("All tables dropped")
