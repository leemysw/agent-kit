# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：model_session
# @Date   ：2025/11/29 11:12
# @Author ：leemysw


# 2025/11/29 11:12   Create
# =====================================================


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class ASession(BaseModel):
    """会话模型"""
    agent_id: str = Field(..., description="客户端会话ID")
    session_id: Optional[str] = Field(default=None, description="SDK会话ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    is_active: bool = Field(default=True, description="是否活跃")
    title: Optional[str] = Field(default=None, description="会话标题")
    message_count: int = Field(0, description="消息数量")
    options: Optional[dict] = Field(default=None, description="会话选项")

    model_config = {"from_attributes": True}


class UpdateTitleRequest(BaseModel):
    title: str
