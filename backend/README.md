# FastAPI sidecar

后端是所有业务操作和 SQLite 访问的唯一入口。开发环境使用 uv 管理 Python 3.12 与锁定依赖。

    uv sync --frozen
    uv run python -m app

质量检查：

    uv run ruff check .
    uv run mypy
    uv run pytest

服务只允许监听 127.0.0.1，端口 0 表示交由操作系统动态分配；实际绑定的端口会在启动后以一行 JSON（`{"event":"sidecar_ready","port":<port>}`）打印到 stdout。桌面进程接管启动后，会显式传入动态端口、`WEEKLY_REPORT_RUNTIME_SECRET` 和运行期目录；除 `/health` 外的所有请求都必须携带匹配的 `X-Runtime-Secret` 请求头。手动单独运行 `python -m app` 调试时，需要在 `.env` 中自行设置一个 ≥32 字符的 `WEEKLY_REPORT_RUNTIME_SECRET`（非 `test` 环境下缺失会在启动时报错）。
