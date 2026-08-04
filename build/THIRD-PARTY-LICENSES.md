# 第三方许可证与来源记录（基线）

> 状态：DESK-01 建立，随依赖变更更新。
> 用途：可追溯的许可证基线。正式安装包内的完整许可证打包与核对由 PKG-01 负责。

## 说明

- 以下为桌面骨架 17 个直接依赖（root workspace：`weekly-report` + `electron/`）。
- 传递依赖（如 typescript-eslint 等）的完整清单、许可证原文与安装包内分发由 PKG-01 统一生成和打包。
- 所有 npm 包均来自 npm 官方 registry（https://registry.npmjs.org/）。
- 版本号以根 `package-lock.json` 锁定为准（本记录仅登记直接依赖）。

## 依赖镜像与完整性策略

- 根 `.npmrc` 仅配置两个镜像，作用范围限 Electron 相关**官方二进制分发**的下载加速：
  `electron_mirror`（Electron 运行时二进制）与 `electron_builder_binaries_mirror`
  （electron-builder 打包工具二进制）。npm 包本体不经过任何镜像。
- 完整性：Electron 二进制下载由 `@electron/get` 依据官方 `SHASUMS256.txt` 强制校验
  （zip 哈希不一致即失败）；electron-builder 二进制按官方元数据校验。
  信任边界：镜像必须忠实转发官方哈希文件，除此之外不引入任何第三方二进制或
  未经记录的压缩包。
- 变更规则：镜像域名固定并登记在本文件；生产/CI 环境网络允许时应直连官方源；
  PKG-01 打包阶段对全部产物做来源与完整性复核。

## 直接依赖清单

| 包名 | 版本 | 许可证 | 来源 | 用途 |
|---|---|---|---|---|
| electron | 39.8.10 | MIT | https://registry.npmjs.org/electron | 桌面运行时 |
| electron-vite | 5.0.0 | MIT | https://registry.npmjs.org/electron-vite | 构建/开发工具 |
| electron-builder | 26.15.3 | MIT | https://registry.npmjs.org/electron-builder | 打包工具（M17 占位） |
| @electron-toolkit/utils | 4.0.0 | MIT | https://registry.npmjs.org/@electron-toolkit/utils | 主进程工具 |
| @electron-toolkit/tsconfig | 2.0.0 | MIT | https://registry.npmjs.org/@electron-toolkit/tsconfig | TS 工程配置 |
| @electron-toolkit/eslint-config-ts | 3.1.0 | MIT | https://registry.npmjs.org/@electron-toolkit/eslint-config-ts | ESLint 配置 |
| @electron-toolkit/eslint-config-prettier | 3.0.0 | MIT | https://registry.npmjs.org/@electron-toolkit/eslint-config-prettier | ESLint 配置 |
| @types/node | 22.20.1 | MIT | https://registry.npmjs.org/@types/node | Node 类型 |
| @vitejs/plugin-vue | 6.0.8 | MIT | https://registry.npmjs.org/@vitejs/plugin-vue | Vue 渲染构建插件 |
| vue | 3.5.40 | MIT | https://registry.npmjs.org/vue | 占位页框架（FE-01 将接管渲染层） |
| vite | 7.3.6 | MIT | https://registry.npmjs.org/vite | 渲染层构建 |
| typescript | 5.9.3 | Apache-2.0 | https://registry.npmjs.org/typescript | 类型检查 |
| eslint | 9.39.5 | MIT | https://registry.npmjs.org/eslint | Lint |
| eslint-plugin-vue | 10.10.0 | MIT | https://registry.npmjs.org/eslint-plugin-vue | Lint |
| vue-eslint-parser | 10.4.1 | MIT | https://registry.npmjs.org/vue-eslint-parser | Lint |
| vue-tsc | 3.3.9 | MIT | https://registry.npmjs.org/vue-tsc | Vue 类型检查 |
| prettier | 3.9.6 | MIT | https://registry.npmjs.org/prettier | 格式化 |

> 注：electron 的二进制包含 Chromium/Node 等组件，其各自的许可证原文随 Electron
> 分发（LICENSE 文件），安装包阶段由 PKG-01 核对后随包分发。

## 变更规则

- 依赖升级或增删必须同步更新本表并重新生成 `package-lock.json`，经审查后合并。
- 不引入未经记录来源的镜像压缩包或模板（见 DESK-01 任务说明 §3.2）。
