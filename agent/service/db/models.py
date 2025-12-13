# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：models
# @Date   ：2025/8/30 14:35
# @Author ：leemysw

# 2025/8/30 14:35   Create
# =====================================================

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from agent.shared.database.async_sqlalchemy import Base


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', agent_id='{self.agent_id}', title='{self.title}')>"


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    round_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # 移除外键，保留字段
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # assistant/user/system/result
    block_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # text/thinking/tool_use/tool_result
    message: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Message(message_id={self.message_id}, session_id='{self.session_id}', round_id={self.round_id}, type='{self.message_type}')>"
