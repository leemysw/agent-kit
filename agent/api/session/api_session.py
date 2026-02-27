# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：api_session.py
# @Date   ：2025/11/28 22:37
# @Author ：leemysw
#
# 2025/11/28 22:37   Create
# 2026/2/25          重构：session_key 路由
# =====================================================

"""
会话 API

[INPUT]: 依赖 session_store, session_manager, session_router
[OUTPUT]: 对外提供 /sessions CRUD 端点
[POS]: api 层的会话管理端点，被前端消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.service.process.conversation_protocol_adapter import ConversationProtocolAdapter
from agent.service.schema.model_session import ASession
from agent.service.session.session_router import build_session_key
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.shared.server.common import resp

router = APIRouter(tags=["session"])
protocol_adapter = ConversationProtocolAdapter()


# =====================================================
# 桥接层 — 前端 agent_id ↔ 内部 session_key
# =====================================================

def _to_session_key(agent_id: str) -> str:
    """前端 agent_id → 内部 session_key"""
    return build_session_key(channel="ws", chat_type="dm", ref=agent_id)


# =====================================================
# 请求模型
# =====================================================

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    agent_id: str
    title: Optional[str] = "New Chat"
    options: Optional[Dict[str, Any]] = None


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


# =====================================================
# API 端点
# =====================================================

@router.get("/sessions", response_model=List[ASession])
async def get_sessions():
    """获取所有会话列表"""
    sessions = await session_store.get_all_sessions()
    data = [s.model_dump() for s in sessions]
    return resp.ok(resp.Resp(data=data))


@router.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """创建新会话"""
    session_key = _to_session_key(request.agent_id)

    existing = await session_store.get_session_info(session_key)
    if existing:
        raise HTTPException(status_code=409, detail="Session already exists")

    success = await session_store.update_session(
        session_key=session_key,
        title=request.title,
        options=request.options,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create session")

    session_info = await session_store.get_session_info(session_key)
    if not session_info:
        raise HTTPException(status_code=500, detail="Failed to retrieve created session")

    return resp.ok(resp.Resp(data=session_info.model_dump()))


@router.patch("/sessions/{agent_id}")
async def update_session(agent_id: str, request: UpdateSessionRequest):
    """更新会话信息"""
    session_key = _to_session_key(agent_id)

    existing = await session_store.get_session_info(session_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.options is not None:
        update_success = await session_manager.update_session_options(session_key=session_key)
        if not update_success:
            raise HTTPException(status_code=409, detail="Failed to update session options")

    success = await session_store.update_session(
        session_key=session_key,
        title=request.title,
        options=request.options,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update session")

    session_info = await session_store.get_session_info(session_key)
    return resp.ok(resp.Resp(data=session_info.model_dump()))


@router.get("/sessions/{agent_id}/messages")
async def get_session_messages(agent_id: str):
    """获取指定会话的所有消息"""
    session_key = _to_session_key(agent_id)
    messages = await session_store.get_session_messages(session_key)
    data = protocol_adapter.build_history_messages(messages)
    return resp.ok(resp.Resp(data=data))


@router.delete("/sessions/{agent_id}")
async def delete_session(agent_id: str):
    """删除会话"""
    session_key = _to_session_key(agent_id)
    session_manager.remove_session(session_key)

    success = await session_store.delete_session(session_key)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return resp.ok(resp.Resp(data={"success": True}))


@router.delete("/sessions/{agent_id}/rounds/{round_id}")
async def delete_round(agent_id: str, round_id: str):
    """删除一轮对话"""
    session_key = _to_session_key(agent_id)

    existing = await session_store.get_session_info(session_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")

    deleted_count = await session_store.delete_round(session_key, round_id)
    if deleted_count < 0:
        raise HTTPException(status_code=500, detail="Failed to delete round")

    return resp.ok(resp.Resp(data={"success": True, "deleted_count": deleted_count}))
