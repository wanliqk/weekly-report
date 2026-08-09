import asyncio
import json
import socket
import sys

import uvicorn

from app.core.config import Settings, get_settings
from app.core.paths import ensure_runtime_directories
from app.db.engine import create_engine as create_db_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.main import create_app
from app.services.backup import cleanup_stale_manual_backups
from app.services.export import ExportService
from app.services.wecom_sync import WeComSyncService


class _AnnouncingServer(uvicorn.Server):
    """Uvicorn server that reports its actually bound port on stdout.

    ``port=0`` lets the OS pick a free loopback port; the parent Electron
    process has no other way to learn which one was chosen, so we print it
    as a single structured line right after the listening socket is bound.
    """

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if not self.servers:
            return
        bound_sockets = self.servers[0].sockets
        if not bound_sockets:
            return
        bound_port = bound_sockets[0].getsockname()[1]
        sys.stdout.write(json.dumps({"event": "sidecar_ready", "port": bound_port}) + "\n")
        sys.stdout.flush()


async def _cleanup_expired_exports(settings: Settings) -> None:
    engine = create_db_engine(settings)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            await ExportService(session, settings).cleanup_expired()
    finally:
        await engine.dispose()


async def _recover_stale_wecom_syncs(settings: Settings) -> None:
    engine = create_db_engine(settings)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            await WeComSyncService(session).recover_stale_syncing_records()
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    cleanup_stale_manual_backups(settings)
    asyncio.run(_cleanup_expired_exports(settings))
    asyncio.run(_recover_stale_wecom_syncs(settings))
    application = create_app(settings)
    config = uvicorn.Config(
        application,
        host=settings.host,
        port=settings.port,
        workers=1,
        reload=False,
    )
    _AnnouncingServer(config).run()


if __name__ == "__main__":
    main()
