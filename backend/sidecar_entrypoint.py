"""PyInstaller entry point for the production sidecar executable.

In dev/test, the backend is always started as `python -m app` (see
`app/__main__.py` and `architecture.md` section 8), which puts `backend/`
itself on `sys.path` so `app`'s own absolute imports (`from app.core...`)
resolve. PyInstaller's `Analysis` needs a concrete script file to serve as
the frozen executable's entry point, and running `app/__main__.py` directly
as that script would instead put `app/`'s own directory on `sys.path` — not
its parent — breaking those same imports.

This thin wrapper is kept as a sibling of `app/` (not inside it) so that
building from it reproduces the `python -m app` layout, then just delegates
to the real entry point.
"""

from app.__main__ import main

if __name__ == "__main__":
    main()
