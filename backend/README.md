# FastAPI sidecar

后端是所有业务操作和 SQLite 访问的唯一入口。开发环境使用 uv 管理 Python 3.12 与锁定依赖。

    uv sync --frozen
    uv run python -m app

质量检查：

    uv run ruff check .
    uv run mypy
    uv run pytest

服务只允许监听 127.0.0.1，端口 0 表示交由操作系统动态分配。桌面进程接管启动后，会显式传入已预留的动态端口。
