# weekly-report

个人日报周报管理桌面应用。当前技术基线为 Electron 39、Vue 3、FastAPI 和 SQLite，首发平台为 Windows 10/11 x64。

## 环境要求

- Node.js 22.12+
- npm 10+
- Python 3.12（由 uv 按 .python-version 管理）
- uv

## 开发命令

    npm ci
    uv sync --directory backend --frozen
    npm run dev

前端质量门禁：

    npm run lint
    npm run typecheck
    npm test
    npm run build

后端质量门禁：

    uv run --directory backend ruff check .
    uv run --directory backend mypy
    uv run --directory backend pytest

本地运行数据写入仓库根目录的 .local-data/，该目录不会提交到 Git。生产环境数据将写入 Electron userData 目录。
