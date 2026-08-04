# Weekly Report Backend

FastAPI backend sidecar for the Weekly Report desktop app. Python 3.12, managed with `uv`.

This package currently only provides the application factory (`create_app()`), the stable
`app.main:app` entry point, and `GET /health`. Configuration, logging, database access,
authentication and business routes are intentionally out of scope for this baseline (see
`ai-docs/tasks/BE-01.md`) and land in later tasks (BE-02, DB-01, API-01, AUTH-02, ...).

## Requirements

- Python 3.12 (uv can provision this automatically; no system install required).
- [uv](https://docs.astral.sh/uv/) available on `PATH`.

## Setup (Windows pwsh)

```powershell
uv sync --frozen
```

`uv sync --frozen` installs the exact versions pinned in `uv.lock` and fails instead of
silently updating the lock file if `pyproject.toml` and `uv.lock` have drifted apart.

## Quality gates (Windows pwsh)

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
uv run pytest
```

All four must pass before a change is considered complete.

## Running the app locally (Windows pwsh)

The server only ever binds to the loopback address with a single worker. The port is never
hardcoded in source — it must be passed explicitly on the command line. In production the port
is chosen dynamically by the Electron main process (DESK-02); the example below uses a local
PowerShell variable purely for manual/dev testing, not a literal port to copy verbatim:

```powershell
$Port = 8000
uv run uvicorn app.main:app --host 127.0.0.1 --port $Port --workers 1
```

Verify it is alive. You can do this from the same session (after starting the server in the
background) or from a second pwsh session — a second session does **not** inherit `$Port`, so
set it there too, using the same value you passed to `--port` above:

```powershell
$Port = 8000   # must match the port the server was started with
Invoke-RestMethod "http://127.0.0.1:$Port/health"
```

Expected response body:

```json
{
  "code": 0,
  "msg": "success",
  "data": { "status": "ok", "version": "0.1.0" }
}
```

Stop the server with `Ctrl+C`; it exits cleanly and creates no database, log, or user-data
directories.

## Project layout

```
backend/
├─ pyproject.toml   # dependencies, Ruff/mypy/pytest config
├─ uv.lock           # locked dependency graph
├─ app/
│  ├─ __init__.py
│  └─ main.py        # create_app() + app = create_app() + GET /health
└─ tests/
   └─ test_health.py
```
