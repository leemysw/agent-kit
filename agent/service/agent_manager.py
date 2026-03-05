# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：agent_manager.py
# @Date   ：2026/3/4 15:09
# @Author ：leemysw
# 2026/3/4 15:09   Create
# =====================================================

"""
Agent 生命周期管理器

[INPUT]: 依赖 db/agent_repository，依赖 agent/workspace 的 AgentWorkspace
[OUTPUT]: 对外提供 AgentManager（Agent 创建/查询/配置构建）
[POS]: service 层的 Agent 管理中心，被 ChatHandler 和 API 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Dict, List, Optional

from agent.service.agent.workspace import AgentWorkspace, get_workspace_base_path
from agent.service.db.agent_repository import agent_repository
from agent.service.schema.model_agent import AAgent, AgentOptions
from agent.utils.logger import logger


class AgentManager:
    """Agent 生命周期管理"""

    def __init__(self):
        self._workspaces: Dict[str, AgentWorkspace] = {}

    # =====================================================
    # Agent CRUD
    # =====================================================

    async def create_agent(
        self,
        name: str,
        workspace_path: Optional[str] = None,
        options: Optional[AgentOptions] = None,
    ) -> Optional[AAgent]:
        """创建 Agent，自动初始化 workspace 目录"""
        from uuid import uuid4
        agent_id = uuid4().hex[:12]

        # 优先使用前端传入的路径，fallback 到 base_path/agent_id
        if not workspace_path:
            base_path = get_workspace_base_path()
            workspace_path = str(base_path / agent_id)

        options_dict = options.model_dump(exclude_none=True) if options else None

        created_id = await agent_repository.create_agent(
            agent_id=agent_id,
            name=name,
            workspace_path=workspace_path,
            options=options_dict,
        )
        if not created_id:
            return None

        # 初始化 workspace 目录
        workspace = self._get_or_create_workspace(agent_id)
        workspace.ensure_exists()

        agent = await agent_repository.get_agent(agent_id)
        logger.info(f"✅ Agent 创建完成: {agent_id} ({name}), workspace={workspace_path}")
        return agent

    async def get_agent(self, agent_id: str) -> Optional[AAgent]:
        """获取 Agent"""
        return await agent_repository.get_agent(agent_id)

    async def get_all_agents(self) -> List[AAgent]:
        """获取所有活跃 Agent"""
        return await agent_repository.get_all_agents()

    async def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        options: Optional[AgentOptions] = None,
    ) -> bool:
        """更新 Agent 配置"""
        options_dict = options.model_dump(exclude_none=True) if options else None
        return await agent_repository.update_agent(agent_id, name=name, options=options_dict)

    async def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent（软删除）"""
        self._workspaces.pop(agent_id, None)
        return await agent_repository.delete_agent(agent_id)

    # =====================================================
    # Workspace
    # =====================================================

    def get_workspace(self, agent_id: str) -> AgentWorkspace:
        """获取 Agent 的 workspace 实例"""
        return self._get_or_create_workspace(agent_id)

    def _get_or_create_workspace(self, agent_id: str) -> AgentWorkspace:
        """惰性创建 workspace 实例"""
        if agent_id not in self._workspaces:
            base_path = get_workspace_base_path()
            self._workspaces[agent_id] = AgentWorkspace(agent_id, base_path)
        return self._workspaces[agent_id]

    # =====================================================
    # SDK 配置构建
    # =====================================================

    # SDK 不支持的配置字段（业务层专用）
    _NON_SDK_FIELDS = {"skills_enabled", "setting_sources"}

    async def build_sdk_options(self, agent_id: str) -> dict:
        """从 Agent 配置 + Workspace 构建 ClaudeAgentOptions 参数

        合并顺序: workspace options (cwd + system_prompt) → agent options (model + tools + ...)
        每次调用重新读取 workspace 文件，修改后立即生效。
        """
        agent = await agent_repository.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Workspace 层: cwd + system_prompt
        workspace = self._get_or_create_workspace(agent_id)
        workspace.ensure_exists()
        sdk_options = workspace.build_sdk_options()

        # Agent 层: model + tools + permissions + ...（过滤掉非 SDK 字段）
        agent_opts = agent.options.model_dump(exclude_none=True)
        for field in self._NON_SDK_FIELDS:
            agent_opts.pop(field, None)
        sdk_options.update(agent_opts)

        return sdk_options


# 全局实例
agent_manager = AgentManager()
