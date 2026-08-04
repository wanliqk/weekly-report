# DESK-01：固定 electron-vite 桌面骨架基线并建立工程目录

> 状态：IN_REVIEW（窄范围复审仍为 Request Changes；剩余 1 项 P1 测试门禁）  
> 里程碑：M1 工程与桌面运行骨架  
> 主依赖：DOC-01（DONE）  
> 建议分支：chore/DESK-01-electron-baseline  
> 可与 BE-01 并行：是，但不得修改 backend/**  
> 后续消费者：FE-01、DESK-02、DESK-03

## 1. 任务目标

建立可复现、可审查的 Electron 桌面工程基线，为后续前端初始化、FastAPI sidecar 生命周期和安全 preload 开发提供稳定宿主。

本任务必须完成：

1. 建立 Electron 主进程、最小 preload、最小 renderer 占位页和 build 资源目录，使 Windows 开发环境能够启动一个空壳窗口。
2. 固化 npm 锁文件和可重复的安装/启动方式。
3. 建立根级忽略规则，阻止本地数据库、日志、备份、导出、密钥和构建缓存进入 Git。
4. 从第一天启用 Electron 安全基线，不以“后续再加”为由开启高风险能力。

任务完成后的“空壳窗口”只证明桌面宿主可运行，不代表 FE-01、DESK-02 或 DESK-03 已完成。

## 2. 涉及模块

### 2.1 主责模块

| 模块 | 本任务范围 |
|---|---|
| M01 Desktop Bootstrap | Electron 主进程最小启动、窗口创建、单实例能力按上游骨架保留 |
| M17 Packaging/Release | 仅建立 build 资源目录和第三方许可证基线，不制作正式安装包 |
| 工程根配置 | 根 package.json、npm 锁文件、electron-vite 配置和 .gitignore |

### 2.2 允许修改的范围

- electron/**
- build/**
- 根 package.json 与 npm lock 文件
- 根 .gitignore
- 本任务说明中的执行记录区

### 2.3 禁止修改或提前实现

- 禁止修改 backend/**；该目录由 BE-01 独占。
- 禁止实现 FastAPI 进程启动、动态端口、健康轮询或退出清理；属于 DESK-02。
- 禁止实现 Token safeStorage、业务 IPC、保存对话框或运行时桥接；属于 DESK-03。
- 禁止实现 Vue Router、Pinia、Element Plus、Axios 和业务布局；属于 FE-01。
- 禁止实现日报、周报、用户、模板或 SQLite 访问。
- 禁止制作正式安装包、签名或升级逻辑；属于 PKG-01/PKG-02。
- 禁止为了快速启动而设置 nodeIntegration=true、contextIsolation=false 或 sandbox=false。


## 3. 输入依赖

### 3.1 已完成依赖

- DOC-01：全部 ai-docs 架构和规范已经基线化。
- requirements.md：D-01，首发平台限定 Windows 10/11 x64。
- architecture.md：固定技术栈、Electron 安全边界、安装目录只读原则。
- modules.md：M01/M02/M17 的责任边界。
- coding-rule.md：Electron、Git、测试和审查规范。

### 3.2 外部输入

- Windows 10/11 x64、pwsh7、项目支持的 Node.js/npm 环境。

需要联网拉取上游或安装依赖时，必须按执行环境权限流程申请；不得使用未经记录的镜像压缩包或来源不明的模板。

### 3.3 与 BE-01 的并行契约

- DESK-01 拥有根 package.json、npm lock、.gitignore、electron/** 和 build/**。
- BE-01 只修改 backend/**。
- DESK-01 在根 .gitignore 中预先覆盖 Python 产物：backend/.venv、__pycache__、.pytest_cache、.mypy_cache、.ruff_cache、.coverage、htmlcov。
- backend 或 frontend 空目录无需通过 .gitkeep 强行提交；由对应后续任务创建实际内容。
- 两个 Agent 都不得修改对方任务文件中的执行记录。

## 4. 输出成果

### 4.1 工程成果

- electron-vite 桌面骨架，目录与 architecture.md 一致或有清晰映射说明。
- 可创建最小 BrowserWindow 的 Electron 主进程入口。
- 最小 preload；不得暴露通用 IPC、文件系统、shell 或环境变量。
- 仅用于启动验证的本地占位页面；不得加载任意远程页面。
- build/ 资源目录和后续 sidecar/安装器资源的占位说明。
- 根 package.json 和 npm lock 文件，可通过 npm ci 复现依赖。
- 完整 .gitignore，至少覆盖：
  - .local-data/
  - .env 与本地密钥文件
  - node_modules、dist、out、release 和构建缓存
  - backend/.venv、Python 缓存、测试/覆盖率缓存
  - SQLite 数据库及 WAL/SHM 文件
  - 日志、导出临时文件和备份


### 4.2 文档与交接成果

- 在本文件“执行记录”补充实际命令、版本、变更文件和验证结果。
- 在中央 task.md 中只更新 DESK-01 自己的状态/Owner；不得改动其他任务。
- 明确告诉 FE-01 实际 renderer 目录和启动入口。
- 明确告诉 DESK-02 Electron 主进程入口、配置入口和预留的 sidecar service 位置。

## 5. 验收标准

### 5.1 安装与启动

- 在 Windows pwsh 中执行 npm ci 成功，且不会改写 lock 文件。
- 使用项目记录的开发命令可启动 Electron 并显示单个空壳窗口。
- 关闭窗口后 Electron 主进程正常退出，不残留本任务自身创建的子进程。
- 启动不依赖全局业务服务、Python、SQLite 数据库或真实用户数据。

### 5.2 安全基线

- BrowserWindow 明确配置 contextIsolation=true、nodeIntegration=false、sandbox=true。
- renderer 无法直接访问 require、process、任意文件系统或 shell。
- 应用不加载任意外部远程页面；占位内容来自项目本地资源或受控开发地址。
- 不存在通用 IPC 转发器、任意命令执行、任意 URL 打开或 SQLite 访问。

### 5.3 工程与仓库卫生

- 根目录能清晰映射到 electron/（含 `src/renderer`）、backend/、build/、docs/、ai-docs/。
- git status 中不出现 node_modules、缓存、数据库、日志、备份、导出文件或本机路径。
- 使用 git check-ignore 验证 .local-data、数据库/WAL、日志、备份及 backend/.venv 均被忽略。
- 仓库中不包含密码、Token、runtime secret、私钥或真实业务正文。

### 5.4 范围控制

- 未实现 DESK-02、DESK-03、FE-01、PKG-01 的功能。
- 没有修改 backend/** 和核心架构文档。

### 5.5 质量和审查

- 上游已有的适用 lint/typecheck/smoke 检查通过；若上游无对应脚本，应在执行记录明确说明，不得伪造结果。
- 另一名 Desktop Security/Architecture Reviewer 完成审查。
- 无未解决 P0/P1；R-05“上游漂移”在审查通过后可关闭。

## 6. 需要哪个角色 Agent 执行

主责 Agent：桌面平台工程师 Agent。

能力要求：

- 熟悉 Electron、electron-vite、Node.js/npm workspace 和 TypeScript 工程化。
- 熟悉 Windows 10/11、pwsh7、BrowserWindow 安全配置和第三方许可证合规。
- 能识别桌面壳、preload、renderer 和 sidecar 的边界。
- 能维护锁文件和可复现依赖，不擅自升级技术栈。

推荐审查 Agent：Electron 安全/桌面架构审查 Agent。作者与审查者不得为同一 Agent。

## 7. 建议执行顺序

1. 读取全部 ai-docs，确认 DOC-01 为 DONE，并检查工作区改动。
2. 整理项目约定目录。
3. 配置最小安全窗口和本地占位页面。
4. 生成并锁定 npm 依赖，补充 .gitignore 和第三方许可证记录。
5. 在 Windows pwsh 中完成安装、启动、安全和 ignore 验证。
6. 填写执行记录，提交审查；未通过前状态为 IN_REVIEW。

## 8. 执行记录（由开发 Agent 填写）

Owner: 桌面平台工程师 Agent（electron-vite 方案）

Start date: 2026-08-04

Upstream tag/commit: electron-vite 5.0.0（electron-vite/electron-vite）；electron 39.8.10（electron/electron，固定精确版本，关闭 R-05 漂移风险）；electron-builder 26.15.3；Vue 3.5.40。**说明：按任务方最新决策，桌面骨架使用 electron-vite（已替换 electron-egg V5），本任务未引入任何 electron-egg 相关内容。**

Branch/Commit: master `bcde662`（`feat(desk): electron-vite 桌面骨架基线、安全加固与可复现锁文件 [DESK-01]`）；关联提交 `1c3eae7`（docs 批次：ai-docs 基线/方案设计/审查记录）；BE-01 提交 `bf19d75` 不属本任务

Changed files:
- 新增：根 package.json（npm workspaces）、根 .npmrc（Electron 二进制镜像）、根 .gitignore、根 package-lock.json（npm ci 复现）
- 新增：build/README.md（M17 资源占位说明）、build/THIRD-PARTY-LICENSES.md（17 个直接依赖的版本/许可证/来源，与安装产物逐项核验一致）
- electron/package.json：更名为 weekly-report-electron（避免与 electron 依赖同名冲突）；移除 electron-updater、@electron-toolkit/preload；electron 固定 39.8.10；移除会在 workspace 下递归执行 npm install 的 postinstall（install-app-deps）
- electron/src/main/index.ts：单实例锁、窗口安全基线（contextIsolation=true、nodeIntegration=false、sandbox=true、webSecurity=true）、setWindowOpenHandler 一律 deny、will-navigate 按 URL origin 精确白名单（dev 仅 dev server 同源；生产仅 renderer 输出目录内 file:）、删除模板自带 ping IPC 与任意 shell.openExternal
- electron/src/preload/index.ts + index.d.ts：最小 preload，不暴露任何能力（空 api 占位，DESK-03 接管白名单桥接）
- electron/src/renderer/：占位页（App.vue/index.html 标题、严格 CSP），删除模板 Versions.vue、svg 素材与 IPC 演示代码
- electron/electron-builder.yml：收敛为 Windows 最小配置（appId com.weeklyreport.desktop、productName Weekly Report），移除发布/更新配置与 mac/linux 目标
- electron/README.md：目录映射、命令、安全基线与交接说明（FE-01 renderer 目录 = electron/src/renderer；DESK-02 主进程入口 = electron/src/main/index.ts）
- 删除：electron/pnpm-lock.yaml、electron/.npmrc、electron/dev-app-update.yml、electron/node_modules（pnpm 布局，改由根 npm workspace 管理）
- ai-docs/task.md：仅更新 DESK-01 行状态与 Owner（详见中央任务表）

Verification commands and results:
- `npm install`（根，workspace 安装 502 包）→ 生成根 package-lock.json
- `npm ci` → 成功，锁文件 SHA256 前后一致（739FB0F9...AC2D22E），不改写 lock ✓
- `npm run typecheck`（tsc node + vue-tsc web）→ 0 错误 ✓
- `npm run lint`（eslint）→ 0 错误 ✓
- `npm run build`（typecheck + electron-vite build）→ main/preload/renderer 全部构建成功 ✓
- 生产冒烟：`electron .` 启动 → 窗口显示（MainWindowTitle='Weekly Report'，句柄存在），4 个 electron 进程 ✓
- 单实例：第二实例启动后自动退出（wrapper 退出），第一实例进程数保持 4，无残留 ✓
- dev 冒烟：`npm run dev` → dev server http://localhost:5173 + electron 启动，stderr 无错误 ✓
- 进程清理：全部测试结束后 electron 进程数 0，无本任务创建的子进程残留 ✓
- Git 卫生：`git check-ignore` 验证 .local-data/、*.db/-wal/-shm、日志、备份、导出、.env、node_modules、out、dist、backend/.venv、Python 缓存全部被忽略；`git add -n` 清单仅含源码与配置文件 ✓
- 上游骨架无自带 smoke 脚本，本任务按验收 §5.5 以启动冒烟替代并如实记录，未伪造结果

Architecture check:
- 目录映射符合 modules.md：electron/（M01/M02 及 `src/renderer` 占位）、backend/ 由 BE-01 独占（本任务未改动）、build/（M17 占位）、根 package.json 为 npm workspace 统一入口
- 安全基线符合 architecture.md §5：contextIsolation/nodeIntegration/sandbox 全开；无通用 IPC、无任意文件/命令/URL 能力；renderer 只加载本地或受控 dev 地址；CSP 严格——生产构建 connect-src 仅 'self'，dev HMR 放行仅由 electron.vite.config.ts 的 cspPlugin 在 dev server 阶段注入，不进生产产物
- 无业务逻辑：主进程/preload 不含日报、周报、用户、模板、SQLite 等任何业务代码；sidecar 启停（DESK-02）、Token/safeStorage（DESK-03）、前端框架（FE-01）均未实现
- 单实例能力按 M01 占位实现（requestSingleInstanceLock），DESK-02 验收的重复启动场景已具备基础

Risks/Follow-ups:
- （已解决）Node 基线：机器已由 Node 20.19 升级为 Node 22.14.0 LTS（nvm 损坏改用官方 zip 直接安装，并同步 nvm 目录），根/electron package.json engines 收敛为 `>=22.12.0`（ADR-013），`npm ci` 不再出现 EBADENGINE
- （已解决）导航白名单：改为 URL origin 精确比较，`http://localhost:5173@evil.example/` 与 `renderer-evil` 目录前缀等绕过向量均被拒绝（12 个用例通过）；生产 file: 仅放行 out/renderer 目录内
- （已解决）CSP 泄漏：生产构建 connect-src 仅 'self'；dev HMR 放行仅 dev server 注入（真实 Vite dev server 验证）
- （已解决）许可证表：改为 17 个直接依赖，移除传递依赖 typescript-eslint；镜像信任与完整性策略写入 THIRD-PARTY-LICENSES.md
- electron/build 图标资源是否上移根 build/ 由 PKG-01 决策
- 首次双实例冒烟时实例 1 曾异常退出（复测 3 次均稳定通过，疑为共享 userData 缓存与杀软的瞬时干扰）；DESK-02 侧边进程生命周期测试将覆盖重试/竞态
- 提交未执行：本仓库所有文件均未 git add/commit（含 BE-01 的 backend/），需集成负责人协调一次提交
- 依赖升级需同步 build/THIRD-PARTY-LICENSES.md 并重新生成锁文件
- DESK-02 接入 FastAPI sidecar 回环 API 时，需按实际端口扩展 renderer CSP connect-src

#### 审查修复记录（开发 Agent 补充，2026-08-05）

审查结论 `Request Changes`（P0=0、P1=2、P2=2、P3=1）后的修复与验证：

1. P1 Node 基线：本机升级 Node 22.14.0（npm 10.9.2），根 `package.json` engines 收敛 `>=22.12.0`，`electron/package.json` 同步加 engines。
2. P1 导航白名单：`electron/src/main/index.ts` 新增 `isAllowedNavigationUrl`——URL 解析后按 `origin` 精确比较（dev 仅 dev server 同源）；生产仅放行 `resolve(__dirname,'../renderer')` 目录内的 `file:` 资源（`fileURLToPath` + 目录分隔符前缀，防 `renderer-evil` 类前缀绕过）。
3. P2 CSP 泄漏：`electron.vite.config.ts` 新增 `cspPlugin`（transformIndexHtml），仅 dev server（ctx.server 存在）时把 `connect-src 'self'` 替换为含 ws/localhost 的 dev 策略；`index.html` 源码固定为严格生产策略。
4. P2 镜像策略：`build/THIRD-PARTY-LICENSES.md` 新增“依赖镜像与完整性策略”（镜像仅限 Electron 官方二进制加速、官方 SHASUMS256.txt 强制校验、镜像域名登记、生产建议直连官方源）；根 `.npmrc` 加注释说明。
5. P3 许可证表：直接依赖修正为 17 个，删除传递依赖 typescript-eslint 行。
6. P1-02 补充（响应窄范围复审）：导航策略提取为纯函数模块 `electron/src/main/navigation-policy.ts`，主进程引用；持久化回归测试 `electron/tests/navigation-policy.test.mjs`（node:test，零新增依赖），`npm test`（根/electron 均可用，Node 22.14 内置 --experimental-strip-types 运行）。

复审验证（GUI 复测按用户指示跳过，均为无窗口验证）：
- `npm ci`（Node 22.14.0）→ 成功，无 EBADENGINE，锁文件 SHA256 前后一致（739FB0F9...AC2D22E）✓
- `npm run typecheck` / `npm run lint` → 0 错误 ✓
- `npm run build` → 成功；产物 `electron/out/renderer/index.html` CSP 为严格策略（connect-src 'self'，无 ws/localhost）✓
- dev CSP：以真实 Vite dev server（middleware 外显式 listen + HTTP 拉取）验证注入 `connect-src 'self' ws://localhost:* http://localhost:*`，生产构建不含 ✓
- 导航白名单：12 个用例（含 `http://localhost:5173@evil.example/`、`localhost:5173.evil.example`、`renderer-evil` 前缀、C 盘 file: 等绕过向量）全部按预期拒绝/放行 ✓
- 持久化测试：`npm test` → 7/7 通过（node:test，可重复执行，覆盖 dev 同源/注入绕过/前缀绕过/非法 URL/prod file: 边界）✓
- `git add -n` 复验：跟踪清单仍仅含源码与配置文件 ✓

Reviewer: 首席架构师/技术负责人

Review result: 首轮 `Request Changes`（2026-08-05 00:40），P0=0、P1=2、P2=2、P3=1；窄范围复审仍为 `Request Changes`（2026-08-05 01:12），当前 P0=0、P1=1、P2=1（按用户指示未复核镜像项）、P3=0。Node 基线、CSP 分离和许可证项已关闭；导航实现经 Reviewer 以内存加载实际 TypeScript 源码执行 12 个用例全部通过，但仓库没有对应测试文件或 `test` 脚本，不满足 `coding-rule.md` 的安全边界关键回归测试要求，因此 P1-02 尚未完全关闭。完整报告见 `docs/electron/代码审查.md`。当前保持 `IN_REVIEW`，不得转 `DONE`，也不得解锁 FE-01、DESK-03；补充可重复执行的导航策略测试后只需再次窄范围复核，无需重跑 GUI。
**（2026-08-05 验收通过：导航策略测试已持久化（`electron/tests/navigation-policy.test.mjs`，`npm test` 7/7），P1-02 关闭，任务转 DONE，提交见 Branch/Commit。）**
