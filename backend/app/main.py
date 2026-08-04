from importlib.metadata import version as _package_version
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

_DISTRIBUTION_NAME = "weekly-report-backend"


def create_app() -> FastAPI:
    app = FastAPI(title="Weekly Report Backend", version=_package_version(_DISTRIBUTION_NAME))

    @app.get("/health")
    def health() -> JSONResponse:
        payload: dict[str, Any] = {
            "code": 0,
            "msg": "success",
            "data": {"status": "ok", "version": _package_version(_DISTRIBUTION_NAME)},
        }
        return JSONResponse(content=payload, headers={"Cache-Control": "no-store"})

    return app


app = create_app()
