# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：models
# @Date   ：2025/8/30 14:35
# @Author ：leemysw
#
# 2025/8/30 14:35   Create
# 2026/2/25         重构：Session 增加 session_key 路由
# =====================================================

"""
数据库 ORM 模型

[INPUT]: 依赖 sqlalchemy ORM，依赖 shared.database.async_sqlalchemy 的 Base
[OUTPUT]: 对外提供 Session/Message ORM 模型
[POS]: db 模块的模型定义层，被 session_repository 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from agent.shared.database.async_sqlalchemy import Base


class Agent(Base):
    """Agent 表 — 一个 Agent = 一个工作区"""
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Agent(id='{self.agent_id}', name='{self.name}')>"


class Session(Base):
    """会话表 — 以 session_key 为主键，支持多通道路由"""
    __tablename__ = "sessions"

    # 结构化路由键: agent:<agentId>:<channel>:<chatType>:<ref>[:topic:<threadId>]
    session_key: Mapped[str] = mapped_column(String(256), primary_key=True)

    # 智能体 ID（当前固定 "main"，预留多 Agent 扩展）
    agent_id: Mapped[str] = mapped_column(String(64), default="main", index=True)

    # SDK 内部会话 ID（用于 resume）
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # 通道类型: websocket / discord / telegram
    channel_type: Mapped[str] = mapped_column(String(32), default="websocket")

    # 会话类型: dm / group / thread
    chat_type: Mapped[str] = mapped_column(String(16), default="dm")

    # 会话状态: active / expired / archived
    status: Mapped[str] = mapped_column(String(16), default="active")

    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Session(key='{self.session_key}', agent='{self.agent_id}', type='{self.chat_type}')>"


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # 关联到 Session.session_key
    session_key: Mapped[str] = mapped_column(String(256), index=True, nullable=False)

    # 保留 agent_id 方便查询
    agent_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="main")

    round_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    block_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Message(id={self.message_id}, session_key='{self.session_key}', type='{self.message_type}')>"
