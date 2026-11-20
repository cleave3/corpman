import asyncio
from typing import AsyncGenerator
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from alembic.config import Config as AlembicConfig
from alembic import command
from src.config import Config

# Ensure Render's standard postgresql:// URL uses the asyncpg driver
db_url = str(Config.DATABASE_URL)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = AsyncEngine(
    create_engine(
        url=db_url,
        echo=False,
        pool_size=5,
        max_overflow=2,
    )
)

MIGRATION_LOCK_ID = 84920481  # Unique 64-bit integer advisory lock key for Corpman migrations


def _execute_alembic_upgrade():
    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")


async def run_safe_migrations():
    """Executes Alembic migrations safely under a PostgreSQL advisory lock without blocking the event loop."""
    async with engine.connect() as conn:
        result = await conn.execute(text(f"SELECT pg_try_advisory_lock({MIGRATION_LOCK_ID})"))
        has_lock = result.scalar()

        if has_lock:
            try:
                print("🔒 Acquired migration lock. Running alembic upgrade head...")
                await asyncio.to_thread(_execute_alembic_upgrade)
                print("✅ Database migrations completed successfully.")
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                raise e
            finally:
                await conn.execute(text(f"SELECT pg_advisory_unlock({MIGRATION_LOCK_ID})"))
                print("🔓 Released migration lock.")
        else:
            print("⏳ Another instance holds the migration lock. Skipping duplicate execution.")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
