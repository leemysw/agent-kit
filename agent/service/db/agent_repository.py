# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：agent_repository.py
# @Date   ：2026/3/4 15:09
# @Author ：leemysw
# 2026/3/4 15:09   Create
# =====================================================

"""
Agent 数据仓库

[INPUT]: 依赖 db/models 的 Agent ORM，依赖 schema/model_agent 的 AAgent
[OUTPUT]: 对外提供 AgentRepository（Agent CRUD）
[POS]: db 模块的 Agent 持久化层，被 agent_manager 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select

from agent.service.db.models import Agent
from agent.service.schema.model_agent import AAgent, AgentOptions
from agent.shared.database.async_sqlalchemy import db
from agent.utils.logger import logger


class AgentRepository:
    """Agent 数据仓库"""

    # =====================================================
    # 创建
    # =====================================================

    async def create_agent(
        self,
        agent_id: str,
        name: str,
        workspace_path: str,
        options: Optional[Dict] = None,
    ) -> Optional[str]:
        """创建 Agent，返回 agent_id"""
        try:
            async with db.session() as session:
                agent = Agent(
                    agent_id=agent_id,
                    name=name,
                    workspace_path=workspace_path,
                    options=options,
                    status="active",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(agent)
                await session.commit()
                logger.info(f"✅ Agent 创建成功: {agent_id} ({name})")
                return agent_id
        except Exception as e:
            logger.error(f"❌ 创建 Agent 失败: {e}")
            return None

    # =====================================================
    # 查询
    # =====================================================

    async def get_agent(self, agent_id: str) -> Optional[AAgent]:
        """按 agent_id 获取 Agent"""
        try:
            async with db.session() as session:
                result = await session.execute(
                    select(Agent).where(Agent.agent_id == agent_id)
                )
                row = result.scalar_one_or_none()
                if not row:
                    return None
                return AAgent(
                    agent_id=row.agent_id,
                    name=row.name,
                    workspace_path=row.workspace_path,
                    options=AgentOptions(**(row.options or {})),
                    created_at=row.created_at,
                    status=row.status,
                )
        except Exception as e:
            logger.error(f"❌ 获取 Agent 失败: {e}")
            return None

    async def get_all_agents(self) -> List[AAgent]:
        """获取所有活跃 Agent（按创建时间降序）"""
        try:
            async with db.session() as session:
                result = await session.execute(
                    select(Agent)
                    .where(Agent.status == "active")
                    .order_by(Agent.created_at.desc())
                )
                rows = result.scalars().all()
                return [
                    AAgent(
                        agent_id=row.agent_id,
                        name=row.name,
                        workspace_path=row.workspace_path,
                        options=AgentOptions(**(row.options or {})),
                        created_at=row.created_at,
                        status=row.status,
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"❌ 获取 Agent 列表失败: {e}")
            return []

    # =====================================================
    # 更新
    # =====================================================

    async def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> bool:
        """更新 Agent"""
        try:
            async with db.session() as session:
                result = await session.execute(
                    select(Agent).where(Agent.agent_id == agent_id)
                )
                agent = result.scalar_one_or_none()
                if not agent:
                    return False

                if name is not None:
                    agent.name = name
                if options is not None:
                    # 合并 options
                    existing = agent.options or {}
                    existing.update(options)
                    agent.options = existing

                await session.commit()
                logger.info(f"✅ Agent 更新成功: {agent_id}")
                return True
        except Exception as e:
            logger.error(f"❌ 更新 Agent 失败: {e}")
            return False

    # =====================================================
    # 删除
    # =====================================================

    async def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent（软删除）"""
        try:
            async with db.session() as session:
                result = await session.execute(
                    select(Agent).where(Agent.agent_id == agent_id)
                )
                agent = result.scalar_one_or_none()
                if not agent:
                    return False

                agent.status = "archived"
                await session.commit()
                logger.info(f"🗑️ Agent 已归档: {agent_id}")
                return True
        except Exception as e:
            logger.error(f"❌ 删除 Agent 失败: {e}")
            return False


# 全局实例
agent_repository = AgentRepository()
