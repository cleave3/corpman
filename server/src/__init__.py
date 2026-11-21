import os
from fastapi import Depends, FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import text
from src.config.db import engine
from src.middleware.dependencies import PermissionChecker
from src.common.utilities import response
from src.common.permissions import user_permission_actions
from src.modules.auth.routes import auth_router
from src.modules.admin.routes import admin_router
from src.modules.business.routes import busines_router
from src.modules.customers.routes import customer_router
from src.modules.transaction.routes import transaction_router
from src.modules.analytics.routes import analytics_router
from src.middleware.middleware import register_middleware
from src.config.app_options import app_options
from .common.errors import register_all_errors
from contextlib import asynccontextmanager
import asyncio
from alembic import command
from alembic.config import Config as AlembicConfig

version_prefix = f"/api/{app_options['version']}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            if(await conn.execute(text("SELECt pg_try_advisory_lock(1)"))).scalar():
                try:
                    await asyncio.to_thread(command.upgrade, AlembicConfig("alembic.ini"), "head")
                finally:
                    await conn.execute(text("SELECt pg_try_advisory_lock(1)"))
    except Exception as e:
        print(f"Lifespan migration warning: {e}")
    yield

app = FastAPI(lifespan=lifespan, **app_options)

app.mount("/static", StaticFiles(directory="static"), name="static")

register_all_errors(app)

register_middleware(app)


@app.get("/", status_code=200, include_in_schema=False)
def app_entry():
    return response(message="Corpman API is live 🚀")

@app.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    return response(message="Corpman API is alive 🚀")

@app.get(f"{version_prefix}/health/readiness", status_code=status.HTTP_200_OK)
async def readiness():
    # Verify DB connectivity to prevent routing traffic before database is ready
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return response(message="Corpman API is ready 🚀")
    except Exception as e:
        return response(message=f"Corpman API is not ready {str(e)} ❌", code=503)


@app.get("/error-log", status_code=200, include_in_schema=False)
def download_error_log():
    log_file_path = "error.log"
    if os.path.exists(log_file_path):
        return FileResponse(
            path=log_file_path, media_type="text/plain", filename="error.log"
        )
    return response(message="No error.log file found", code=404)


app.include_router(
    analytics_router,
    tags=["Analytics"],
    prefix=f"{version_prefix}/analytics",
    dependencies=[
        Depends(
            PermissionChecker(
                allowed_permissions=[
                    user_permission_actions["dashboard_overview"],
                    user_permission_actions["dashboard_revenue"],
                    user_permission_actions["dashboard_due_payments"],
                    user_permission_actions["dashboard_pending"],
                    user_permission_actions["dashboard_chart"],
                    user_permission_actions["dashboard_customers"],
                    user_permission_actions["dashboard_payouts"],
                ]
            )
        )
    ],
)
app.include_router(auth_router, tags=["Onboarding"], prefix=f"{version_prefix}/auth")
app.include_router(admin_router, tags=["Admin"], prefix=f"{version_prefix}/admin")
app.include_router(
    busines_router, tags=["Business"], prefix=f"{version_prefix}/business"
)
app.include_router(
    customer_router, tags=["Customer"], prefix=f"{version_prefix}/customer"
)
app.include_router(
    transaction_router, tags=["Transaction"], prefix=f"{version_prefix}/transaction"
)
