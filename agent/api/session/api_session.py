# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：history.py
# @Date   ：2025/11/28 22:37
# @Author ：leemysw

# 2025/11/28 22:37   Create
# =====================================================

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.service.schema.model_message import AMessage
from agent.service.schema.model_session import ASession
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.shared.server.common import resp

router = APIRouter(tags=["session"])


# ==================== 请求模型 ====================

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    agent_id: str
    title: Optional[str] = "New Chat"
    options: Optional[Dict[str, Any]] = None


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


# ==================== API 端点 ====================

@router.get("/sessions", response_model=List[ASession])
async def get_sessions():
    """获取所有会话列表"""
    sessions = await session_store.get_all_sessions()
    data = []
    for session in sessions:
        data.append(session.model_dump())

    response = resp.Resp(data=data)
    return resp.ok(response)


@router.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """创建新会话"""
    # 检查会话是否已存在
    existing = await session_store.get_session_info(request.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail="Session already exists")

    # 创建会话记录
    success = await session_store.update_session(
        agent_id=request.agent_id,
        title=request.title,
        options=request.options
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # 获取创建后的会话信息
    session_info = await session_store.get_session_info(request.agent_id)
    if not session_info:
        raise HTTPException(status_code=500, detail="Failed to retrieve created session")

    response = resp.Resp(data=session_info.model_dump())
    return resp.ok(response)


@router.patch("/sessions/{agent_id}")
async def update_session(agent_id: str, request: UpdateSessionRequest):
    """更新会话信息（标题、选项等）"""
    # 检查会话是否存在
    existing = await session_store.get_session_info(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")

    # 如果要更新options，先检查会话是否正忙
    if request.options is not None:

        # 更新内存中的session manager（重置ClaudeSDKClient）
        update_success = await session_manager.update_session_options(
            agent_id=agent_id,
            options=request.options
        )
        if not update_success:
            raise HTTPException(
                status_code=409,
                detail="Failed to update session options. Session may be in use."
            )

    # 更新数据库中的会话记录
    success = await session_store.update_session(
        agent_id=agent_id,
        title=request.title,
        options=request.options
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update session")

    # 获取更新后的会话信息
    session_info = await session_store.get_session_info(agent_id)
    response = resp.Resp(data=session_info.model_dump())
    return resp.ok(response)


@router.get("/sessions/{agent_id}/messages", response_model=List[AMessage])
async def get_session_messages(agent_id: str):
    """获取指定会话的所有消息"""
    messages = await session_store.get_session_messages(agent_id)
    data = []
    for message in messages:
        data.append(message.model_dump())

    response = resp.Resp(data=data)
    return resp.ok(response)


@router.delete("/sessions/{agent_id}")
async def delete_session(agent_id: str):
    """删除会话"""
    # 从内存中移除
    session_manager.remove_session(agent_id)

    # 从数据库中删除
    success = await session_store.delete_session(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    response = resp.Resp(data={"success": True})
    return resp.ok(response)


@router.delete("/sessions/{agent_id}/rounds/{round_id}")
async def delete_round(agent_id: str, round_id: str):
    """删除一轮对话（包含用户问题和所有回答）"""
    # 检查会话是否存在
    existing = await session_store.get_session_info(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")

    # 删除轮次
    deleted_count = await session_store.delete_round(agent_id, round_id)
    if deleted_count < 0:
        raise HTTPException(status_code=500, detail="Failed to delete round")

    response = resp.Resp(data={"success": True, "deleted_count": deleted_count})
    return resp.ok(response)
