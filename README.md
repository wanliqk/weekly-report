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

## 生产打包（Windows 安装包）

`npm run build:win` 只构建 Electron/Vue 前端并调用 electron-builder 打包，**不会**重新编译后端 sidecar；`build/sidecar/` 是需要手动重新生成的产物目录（已在 .gitignore 中排除）。后端代码有任何改动后，必须先完成下面两步再打包，否则安装包里仍是旧版后端行为：

    uv sync --directory backend --frozen --group build
    uv run --directory backend pyinstaller weekly-report-backend.spec --distpath ../build/_pyinstaller-dist --workpath ../build/_pyinstaller-work --noconfirm

将新产物整体搬到 build/sidecar/（覆盖旧内容，weekly-report-backend.exe 需直接位于该目录顶层）：

    Remove-Item -Recurse -Force build\sidecar -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force build\sidecar | Out-Null
    Move-Item build\_pyinstaller-dist\weekly-report-backend\* build\sidecar\

再生成安装包：

    npm run build:win

产物为 electron/dist/weekly-report-<version>-setup.exe，electron-builder 会把 build/sidecar/ 整体复制进安装包的 resources/sidecar/（见 electron/electron-builder.yml 的 extraResources）。
