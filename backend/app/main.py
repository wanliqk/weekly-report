from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.v1.system import router as system_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware, RuntimeSecretMiddleware
from app.db.engine import create_engine as create_db_engine
from app.db.session import create_session_factory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.db_engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    application = FastAPI(
        title="Weekly Report API",
        version="0.1.0",
        docs_url="/docs" if app_settings.environment == "development" else None,
        redoc_url=None,
        lifespan=_lifespan,
    )
    application.state.settings = app_settings
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
    )
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_router)
    application.include_router(system_router)
    return application
