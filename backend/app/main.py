import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.v1.admin_daily_reports import router as admin_daily_reports_router
from app.api.v1.auth import router as auth_router
from app.api.v1.daily_report_days import router as daily_report_days_router
from app.api.v1.daily_reports import router as daily_reports_router
from app.api.v1.exports import router as exports_router
from app.api.v1.internal_wecom import router as internal_wecom_router
from app.api.v1.settings import router as settings_router
from app.api.v1.statistics import router as statistics_router
from app.api.v1.system import router as system_router
from app.api.v1.templates import router as templates_router
from app.api.v1.users import router as users_router
from app.api.v1.wecom import day_sync_router as wecom_day_sync_router
from app.api.v1.wecom import router as wecom_router
from app.api.v1.weekly_reports import router as weekly_reports_router
from app.core.backup_registry import BackupRegistry
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.jwt_secret import load_or_create_jwt_secret
from app.core.middleware import RequestIdMiddleware, RuntimeSecretMiddleware
from app.db.engine import create_engine as create_db_engine
from app.db.session import create_session_factory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.db_engine.dispose()


def create_app(settings: Settings | None = None, *, jwt_secret: str | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    resolved_jwt_secret = jwt_secret
    if resolved_jwt_secret is None:
        resolved_jwt_secret = (
            secrets.token_hex(32)
            if app_settings.environment == "test"
            else load_or_create_jwt_secret(app_settings.data_dir)
        )
    application = FastAPI(
        title="Weekly Report API",
        version="0.3.0",
        docs_url="/docs" if app_settings.environment == "development" else None,
        redoc_url=None,
        lifespan=_lifespan,
    )
    application.state.settings = app_settings
    application.state.jwt_secret = resolved_jwt_secret
    application.state.backup_registry = BackupRegistry()
    db_engine = create_db_engine(app_settings)
    application.state.db_engine = db_engine
    application.state.db_session_factory = create_session_factory(db_engine)
    register_exception_handlers(application)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )
    # Registered before CORSMiddleware so CORS (added after, thus outer in the
    # stack) can still answer preflight OPTIONS requests without ever reaching
    # this check — browsers never send X-Runtime-Secret on a preflight.
    application.add_middleware(
        RuntimeSecretMiddleware,
        expected_secret=app_settings.runtime_secret,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Runtime-Secret"],
        # Content-Disposition isn't on the CORS response-header safelist, so
        # without this the renderer's fetch of /daily-report-exports/{id}/file
        # can never read the server-generated file name (confirmed live: the
        # save dialog silently fell back to the generic default name).
        expose_headers=["Content-Disposition"],
    )
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_router)
    application.include_router(system_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(templates_router)
    application.include_router(settings_router)
    application.include_router(daily_reports_router)
    application.include_router(daily_report_days_router)
    application.include_router(admin_daily_reports_router)
    application.include_router(exports_router)
    application.include_router(weekly_reports_router)
    application.include_router(statistics_router)
    application.include_router(wecom_router)
    application.include_router(wecom_day_sync_router)
    application.include_router(internal_wecom_router)
    return application
