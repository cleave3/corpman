from typing import AsyncGenerator
from sqlmodel import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import Config
from alembic import command
from alembic.config import Config as AlembicConfig
import asyncio

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
        max_overflow=2
    )
)

MIGRATION_LOCK_ID = 11223344

def _execute_alembic_upgrade():
    alembic_config = AlembicConfig("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_config, "head")

async def run_safe_migration():
    async with engine.connect() as conn:
        result = await conn.execute(text(f"SELECT pg_try_advisory_lock({MIGRATION_LOCK_ID})"))
        has_lock = result.scalar()
        
        if has_lock:
            try:
                print("Acquired lock. Running alembic upgrade...")
                await asyncio.to_thread(_execute_alembic_upgrade)
                print("DB migration completed successfully..")
            except Exception as e:
                print(f"Failed to run alembic upgrade: {e}")
            finally:
                await conn.execute(text(f"SELECT pg_try_advisory_unlock({MIGRATION_LOCK_ID})"))
                
        else:
            print("failed to acquire migration lock")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
