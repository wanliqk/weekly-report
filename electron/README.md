# weekly-report-electron（桌面壳）

Weekly Report 的 Electron 桌面壳：主进程 + 最小 preload + 占位 renderer。
本目录由 DESK-01 建立，后续由 FE-01（renderer）、DESK-02（sidecar 生命周期）、
DESK-03（安全运行时桥接）接管各自部分。

## 目录映射（对应 ai-docs/modules.md）

| 本目录 | 架构模块 | 说明 |
|---|---|---|
| `src/main/index.ts` | M01 Desktop Bootstrap | 主进程入口：单实例、窗口、安全基线；sidecar 启停由 DESK-02 在此扩展 |
| `src/preload/index.ts` | M02 Runtime Bridge | 最小 preload 占位，白名单桥接由 DESK-03 实现 |
| `src/renderer/` | M12 Frontend Shell（前端） | 当前仅为启动验证占位页；FE-01 实际 renderer 目录即 `electron/src/renderer` |
| `electron-builder.yml` | M17 Packaging/Release | 打包配置占位，正式安装包由 PKG-01 制作 |
| `build/`、`resources/` | M17 | electron-builder buildResources（图标等）；根 `build/` 存放跨端打包资源与许可证记录 |

## 环境要求

- Windows 10/11 x64（V1，R-01）、pwsh 7、Node.js 22.12+ LTS（ADR-013，npm 10+）。
- 依赖安装统一在仓库根目录执行（npm workspaces），禁止在 `electron/` 内单独安装。

## 常用命令（在仓库根目录执行）

```powershell
npm ci            # 按锁文件可复现安装（不改写 package-lock.json）
npm run dev       # 启动 electron-vite dev（热更新），显示空壳窗口
npm run typecheck # TS 严格类型检查（node + web）
npm run lint      # ESLint
npm run build     # typecheck + electron-vite build（输出 electron/out）
npm run build:win # 额外生成 Windows 安装包（PKG-01 前仅供冒烟，不发布）
```

## 安全基线（DESK-01 验收项）

- BrowserWindow：`contextIsolation=true`、`nodeIntegration=false`、`sandbox=true`、`webSecurity=true`。
- preload 不暴露通用 IPC、文件系统、shell、环境变量或任意命令执行。
- 不加载任意外部页面：`setWindowOpenHandler` 一律 `deny`，`will-navigate` 只放行
  受控 dev 地址或 `file:` 本地资源。
- renderer 占位页带严格 CSP（见 `src/renderer/index.html`）。
- 主进程无业务逻辑、无 SQLite 访问；业务只属于 FastAPI sidecar（DESK-02 起接入）。

## 约束（来自 DESK-01 任务说明）

- 禁止把 electron 的 Node 代码当作业务后端。
- 运行期数据（`.local-data/` 等）一律不入 Git；安装目录视为只读。
- 依赖版本以根 `package-lock.json` 为准，升级需同步更新 `build/THIRD-PARTY-LICENSES.md`。
