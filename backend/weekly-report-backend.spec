# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the production sidecar (`PKG-01`).

Produces an `onedir` build whose executable is named `weekly-report-backend`
(matching `electron/src/main/sidecar/constants.ts::PROD_SIDECAR_EXECUTABLE_NAME`)
so it can run with no system Python/uv installed on the target machine.

Build from the `backend/` directory:

    uv run --directory backend pyinstaller weekly-report-backend.spec ^
        --distpath ../build/_pyinstaller-dist --workpath ../build/_pyinstaller-work --noconfirm

That produces `build/_pyinstaller-dist/weekly-report-backend/...`; the
caller is responsible for flattening that onedir tree into `build/sidecar/`
(see `ai-docs/progress.md` for the exact commands actually used).

Collection pitfalls this spec exists to handle (see the inline comments
below at each point for the exact failure each one fixes):

1. Alembic's `alembic.ini` and the `alembic/` migration script directory are
   read from disk at runtime (`ScriptDirectory` scans `alembic/versions/*.py`
   by filename, not by import), so they must be bundled as literal `datas`,
   not inferred from the Python import graph. `app/db/migrate.py` resolves
   their location relative to `sys.executable` when frozen.
2. Several dependencies are loaded via dynamic dispatch (SQLAlchemy's
   `sqlite+aiosqlite` URL-scheme lookup, argon2-cffi's cffi backend,
   Alembic's own `env.py`/version scripts importing `alembic.op` etc. at
   runtime) rather than static top-level imports, so PyInstaller's import
   graph analysis misses them without explicit `collect_submodules`/
   `collect_all` hints.
3. PyInstaller >=6.0 changed the onedir default layout to put everything
   except the exe itself inside a `_internal/` subdirectory, which would
   separate the bundled `alembic.ini`/`alembic/` from the exe; `contents_directory="."`
   on `EXE(...)` below restores the flat layout `app/db/migrate.py` expects.
4. A transitive PyInstaller hook (`hook-pydantic.py`) drags in `pydantic.mypy`
   and the entire `mypy` package even though nothing here uses either at
   runtime; both are excluded to keep the redistributable binary smaller.
"""

from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_submodules

# `SPECPATH` is injected into this file's exec globals by PyInstaller itself
# (the directory containing this .spec file, i.e. `backend/`).
BACKEND_ROOT = Path(SPECPATH)  # noqa: F821
ALEMBIC_SOURCE_DIR = BACKEND_ROOT / "alembic"
ALEMBIC_INI_SOURCE = BACKEND_ROOT / "alembic.ini"


def _alembic_datas() -> list[tuple[str, str]]:
    """Bundles `alembic.ini` and `alembic/` as literal files next to the exe.

    Excludes `__pycache__`/`.pyc`: only source `.py` files are needed at
    runtime (Alembic's `ScriptDirectory` imports them fresh), and
    `script.py.mako` is only used by `alembic revision --autogenerate`
    (an authoring-time command, not something the frozen sidecar runs).
    """
    entries: list[tuple[str, str]] = [(str(ALEMBIC_INI_SOURCE), ".")]
    for source_path in ALEMBIC_SOURCE_DIR.rglob("*"):
        if source_path.is_dir() or "__pycache__" in source_path.parts:
            continue
        if source_path.suffix == ".pyc":
            continue
        dest_dir = source_path.parent.relative_to(BACKEND_ROOT)
        entries.append((str(source_path), str(dest_dir)))
    return entries


datas: list[tuple[str, str]] = _alembic_datas()
binaries: list[tuple[str, str]] = []
hiddenimports: list[str] = []

# Alembic's `command.upgrade()` executes `alembic/env.py` and each
# `alembic/versions/*.py` file by reading them off disk and exec'ing their
# contents (see `_alembic_datas` above) — those files' own `from alembic
# import op` / `from alembic import context` statements are *not* visible to
# PyInstaller's static analysis of `app/db/migrate.py`, so without this the
# frozen exe fails at startup with `ModuleNotFoundError: No module named
# 'alembic.op'` the first time a fresh (or out-of-date) database triggers a
# real migration run. `alembic.testing.*` is excluded: it is Alembic's own
# pytest-based test harness (never imported by `command.upgrade`/
# `ScriptDirectory` at runtime), and collecting it transitively drags in a
# full pytest + mypy install into the redistributable binary for nothing.
hiddenimports += [name for name in collect_submodules("alembic") if ".testing" not in name]

# SQLAlchemy resolves the `sqlite+aiosqlite://` URL scheme to a dialect
# module via a plugin/entry-point style lookup at connect time, not a
# top-level import PyInstaller's analyzer can see from `app/db/engine.py`.
# Without this, the frozen exe fails at startup with
# `ModuleNotFoundError: No module named 'sqlalchemy.dialects.sqlite.aiosqlite'`.
hiddenimports += collect_submodules("sqlalchemy.dialects.sqlite")
hiddenimports += collect_submodules("aiosqlite")

# argon2-cffi ships a compiled cffi backend (`_argon2_cffi_bindings`) that is
# loaded dynamically by `argon2/low_level.py`; `collect_all` (not just
# `collect_submodules`) is needed because the compiled extension module and
# its metadata are not picked up by import-graph analysis alone. Without
# this the frozen exe fails at first login/password-hash attempt with
# `ModuleNotFoundError: No module named '_argon2_cffi_bindings'`.
for package_name in ("argon2", "_argon2_cffi_bindings"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# uvicorn[standard]'s optional accelerators (`uvloop`, `httptools`,
# `websockets`) are selected via try/except feature-detection at import
# time, so a missing one is not fatal by itself — but collecting uvicorn's
# own submodules avoids missing its *required* protocol/loop selection
# machinery under PyInstaller's static analysis.
hiddenimports += collect_submodules("uvicorn")

# `pyinstaller-hooks-contrib`'s bundled `hook-pydantic.py` unconditionally
# does `collect_submodules("pydantic")`, which pulls in `pydantic.mypy` (a
# mypy *plugin* pydantic ships for users' own static type checking) and
# transitively the entire `mypy` package. Nothing in this sidecar's runtime
# path ever imports `pydantic.mypy` or `mypy`; excluding them drops a whole
# static type checker from the redistributable binary for no functional
# loss.
analysis = Analysis(
    ["sidecar_entrypoint.py"],
    pathex=[str(BACKEND_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["mypy", "pydantic.mypy"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="weekly-report-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # PyInstaller >=6.0 defaults onedir builds to a `_internal/` subdirectory
    # for everything except the exe itself (datas included), which would put
    # the bundled `alembic.ini`/`alembic/` next to the *interpreter*, not
    # next to `weekly-report-backend.exe`. `app/db/migrate.py` resolves the
    # bundled Alembic files relative to `sys.executable`'s own directory, so
    # this restores the pre-6.0 flat onedir layout where every collected
    # file (including our datas) sits directly beside the exe.
    contents_directory=".",
)

COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="weekly-report-backend",
)
