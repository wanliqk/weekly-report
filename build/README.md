# build/ — 打包与发布资源（M17 基线占位）

> 本目录属于 `build/**`，由 DESK-01 建立，PKG-01/PKG-02 在后续任务中充实内容。
> V1 发布平台：Windows 10/11 x64（见 ai-docs 风险登记 R-01）。

## 本目录用途（占位说明）

| 子项 | 用途 | 当前状态 |
|---|---|---|
| `THIRD-PARTY-LICENSES.md` | 第三方依赖许可证与来源基线记录 | 已有（DESK-01） |
| 图标/安装器资源 | 安装包图标、banner、安装器配置 | 待 PKG-01 |
| sidecar 资源 | PyInstaller `onedir` 产物、Alembic 迁移、许可证打包为 extraResources | 待 PKG-01/PKG-02 |
| 签名/升级配置 | Windows 签名证书策略、升级与回滚说明 | 待 PKG-01/PKG-02 |

## 与 electron/ 的关系

- `electron/build/`（electron-builder 的 buildResources）当前存放脚手架自带图标
  （icon.ico/icon.icns/icon.png 与 entitlements.mac.plist），由 `electron-builder.yml`
  引用；是否上移到本根目录由 PKG-01 统一决策，本任务不擅自移动。
- 根 `build/` 只放跨端、跨安装包的资源与记录，避免与 electron-builder 的
  buildResources 目录混淆。

## 规则

- 安装目录视为只读：任何运行期数据（数据库、日志、备份、导出、密钥）禁止进入
  `build/`，也不得写入安装目录。
- 正式安装包、签名、升级逻辑由 PKG-01/PKG-02 负责；本目录当前仅做占位与记录。
