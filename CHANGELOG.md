# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- 清理 Session 级执行配置契约，`/sessions` 接口不再接收和持久化 `model`、`system_prompt`、`allowed_tools` 等执行选项
- Agent 设置中的 `system_prompt` 已接入后端持久化，并在运行时与 Workspace Prompt 组合为最终系统提示词
- Agent 设置中的 `include_partial_messages` 已接入前端会话渲染控制，默认值为 `true`

## [0.3.2] - 2026-03-09

### Changed
- PyPI 发布名调整为 `harness-agent-kit`，避免与现有项目名称过于相似而被拒绝
- README 中的 pip 安装说明同步更新为新的发布名

## [0.3.1] - 2026-03-09

### 🚀 Major Refactoring

#### 存储层重构
- 会话与 Agent 持久化从 SQLite/Alembic 迁移为基于 Workspace 的文件存储
- 新增 `agent/service/storage/file_store.py`，统一管理 `agent.json`、`meta.json`、`messages.jsonl`
- 删除 SQLAlchemy ORM、Alembic 迁移脚本和运行时数据库初始化逻辑

### Added
- 支持从旧 `cache/data/agent-kit.db` 自动迁移历史数据到文件存储
- 历史消息加载时自动补齐未自然结束轮次的中断 `tool_result` 和 `result`

### Changed
- Docker 部署改为持久化 `./data -> /home/agent/.agent-kit`
- `makefile` 中数据库命令调整为文件存储相关命令
- README 与部署文档统一更新为 Workspace 文件存储说明
- 新增 Python 包发布流程，并补充 PyPI 所需元数据与说明

### Removed
- `deploy/init-db.sh`
- Alembic 相关配置与迁移文件
- SQLite ORM 模型与数据库初始化入口

## [0.3.0] - 2026-03-09

### 🚀 Major Refactoring

#### Agent 管理与工作空间
- 引入 Agent 管理系统，支持创建、编辑、删除和切换多个 Agent
- 每个 Agent 绑定独立 Workspace，统一管理 `cwd`、system prompt 和规则文件
- 会话路由与 Agent 工作空间配置统一，支持更清晰的多 Agent 运行方式

### Added
- CLI 增加通道配置参数，支持按需启用 WebSocket、Discord、Telegram
- Agent 管理相关前端交互与配置界面
- Agent 管理系统特性文档

### Changed
- 前后端会话与 Agent 交互模型重构
- 会话创建、恢复、路由逻辑统一到 `session_key`

## [0.2.0] - 2026-02-28

### 🚀 Major Refactoring

#### 会话协议与消息模型
- 重构消息通道架构，支持 Discord、Telegram 多通道接入
- 重构 `session_key` 路由和相关配置，统一会话寻址方式
- 统一前后端字段命名规范，清理冗余类型定义
- 统一会话消息协议，修复中断终态与历史容错问题

### Added
- 第三方 IM 集成文档
- README 中的多通道接入说明
- JSON 字段中文字符保留能力

### Changed
- 流式内容块处理逻辑调整，减少 assistant 中间块丢失
- 历史消息兼容逻辑增强，改善异常和脏数据恢复

## [0.1.4] - 2026-01-11

### Added
- 新增飞书文档阅读 Skill

### Changed
- 升级 Claude Agent SDK

## [0.1.3] - 2026-01-06

### Added
- 工具流式消息控制
- Skills 配置能力
- 获取最新 `round_id` 的能力
- 中断结果消息处理

### Changed
- 默认模型更新为 `glm-4.7`
- 优化会话处理逻辑并移除部分冗余代码
- 更新 Dockerfile 与 GitHub Action 配置

## [0.1.2] - 2025-12-16

### Changed
- 更新 Dockerfile
- 统一镜像名称为 `agent-kit`

## [0.1.1] - 2025-12-16

### Added
- 优化加载动画和消息统计组件

### Fixed
- 修复 regenerate 相关问题
- 修复删除和重新生成流程中的异常
- 更新 README

## [0.1.0] - 2025-12-13

### Added
- 初始版本发布
- FastAPI 后端与 Next.js 前端基础结构
- WebSocket 对话能力
- 基础会话管理与消息渲染能力
