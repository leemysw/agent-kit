# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 架构概述
**AI 聊天应用**: FastAPI 后端 + Next.js 前端 + WebSocket 实时通信
**核心目录:**
- `agent/` - Python 后端 (FastAPI, WebSocket, 数据库)
- `web/src/` - Next.js 前端 (React, TypeScript, Zustand)
- `alembic/` - 数据库迁移
**技术栈:**
- 后端: FastAPI + async SQLite + Alembic
- 前端: Next.js 14 + TypeScript + Tailwind CSS
- 实时通信: WebSocket
- AI 集成: Claude Agent SDK

## 核心 API
- `WebSocket /agent/v1/chat/ws` - 实时聊天
- `GET /agent/v1/sessions` - 会话管理
- `GET /agent/v1/sessions/{id}/messages` - 消息历史

**数据流:** 前端 → WebSocket → FastAPI → AI 模型 → 响应 → WebSocket → 前端

## 配置说明
**后端 (.env):**
**前端 (.env.local):**

## 开发文档索引
### 📚 详细指南
- **[前端接口文档](web/README.md)** - React 组件、类型定义和 API 接口
- **[WebSocket 流程](docs/websocket-session-flow.md)** - WebSocket 会话和数据流

### 📖 技术文档
- **[会话管理](docs/guides/sessions.md)** - 会话创建、管理和消息处理
- **[流式 vs 单次模式](docs/guides/streaming-vs-single-mode.md)** - AI 响应模式对比
- **[自定义工具](docs/guides/custom-tools.md)** - 创建和使用自定义 AI 工具
- **[Slah 命令](docs/guides/slash-commands.md)** - 自定义斜杠命令开发
- **[Skills 指南](docs/guides/skills.md)** - 技能系统使用和开发
- **[MCP 集成](docs/guides/mcp.md)** - Model Context Protocol 集成
- **[托管指南](docs/guides/hosting.md)** - 生产环境部署和配置
- **[权限管理](docs/guides/permissions.md)** - 权限控制和安全设置
- **[结构化输出](docs/guides/structured-outputs.md)** - AI 响应格式化
- **[成本追踪](docs/guides/cost-tracking.md)** - API 调用成本监控
- **[Todo 追踪](docs/guides/todo-tracking.md)** - 任务管理和进度追踪
- **[插件系统](docs/guides/plugins.md)** - 插件开发和管理

## 代码模式
**后端:** 异步编程、Pydantic 模型、FastAPI 依赖注入、WebSocket
**前端:** Zustand 状态管理、自定义 Hooks、Radix UI + Tailwind、React Markdown

## 开发规范

## 注释使用中文
- 面对对象开发
- Always respond in 中文
- 不要过度设计，保证代码简洁易懂，简单实用
- 要注意圈复杂度，代码尽可能复用
- 注意模块设计，尽量使用设计模式
- 改动时最小化修改，尽量不修改到其他模块代码