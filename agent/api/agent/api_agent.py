# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：api_agent.py
# @Date   ：2026/3/4 15:09
# @Author ：leemysw
# 2026/3/4 15:09   Create
# =====================================================

"""
Agent API

[INPUT]: 依赖 agent_manager，依赖 session_store
[OUTPUT]: 对外提供 /agents CRUD 端点 + Agent 下属 Session 查询
[POS]: api 层的 Agent 管理端点，被前端消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import List

from fastapi import APIRouter, HTTPException

from agent.service.agent_manager import agent_manager
from agent.service.schema.model_agent import AAgent, AgentOptions, CreateAgentRequest, UpdateAgentRequest
from agent.service.session_store import session_store
from agent.shared.server.common import resp

router = APIRouter(tags=["agent"])


# =====================================================
# Agent CRUD
# =====================================================

@router.get("/agents", response_model=List[AAgent])
async def get_agents():
    """获取所有 Agent 列表"""
    agents = await agent_manager.get_all_agents()
    data = [a.model_dump() for a in agents]
    return resp.ok(resp.Resp(data=data))


@router.post("/agents")
async def create_agent(request: CreateAgentRequest):
    """创建新 Agent"""
    agent = await agent_manager.create_agent(
        name=request.name,
        workspace_path=request.workspace_path,
        options=request.options,
    )
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to create agent")
    return resp.ok(resp.Resp(data=agent.model_dump()))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent 配置"""
    agent = await agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return resp.ok(resp.Resp(data=agent.model_dump()))


@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, request: UpdateAgentRequest):
    """更新 Agent 配置"""
    existing = await agent_manager.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    success = await agent_manager.update_agent(
        agent_id=agent_id,
        name=request.name,
        options=request.options,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update agent")

    agent = await agent_manager.get_agent(agent_id)
    return resp.ok(resp.Resp(data=agent.model_dump()))


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """删除 Agent（软删除）"""
    success = await agent_manager.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return resp.ok(resp.Resp(data={"success": True}))


# =====================================================
# Agent 下属 Session
# =====================================================

@router.get("/agents/{agent_id}/sessions")
async def get_agent_sessions(agent_id: str):
    """获取 Agent 下的所有会话"""
    agent = await agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    all_sessions = await session_store.get_all_sessions()
    # 过滤出属于此 Agent 的 session
    agent_sessions = [s for s in all_sessions if s.agent_id == agent_id]
    data = [s.model_dump() for s in agent_sessions]
    return resp.ok(resp.Resp(data=data))
