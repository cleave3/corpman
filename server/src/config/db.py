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

def _execute_alembic_upgrade():
    config = AlembicConfig("alembic.ini")
    command.upgrade(config, "head") 
    
async def run_safe_migration():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT pg_try_advisory_lock(1)")) 
        has_lock = result.scalar()
        
        if has_lock:
            try:
                print("starting migration...")
                await asyncio.to_thread(_execute_alembic_upgrade)
                print("DB migration sucessfull...")
            except Exception as e:
                print(f"Migration faile: {e}")
            finally:
                await conn.execute(text("SELECT pg_try_advisory_unlock(1)"))      
        else:
            print("Another instance has lock")          

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
