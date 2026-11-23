from typing import AsyncGenerator
from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import Config
from alembic import command
from alembic.config import Config as AlembicConfig

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

def run_alembic_migration():
    alembic_config = AlembicConfig("alembic.ini")
    command.upgrade(alembic_config, "head")
    

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
