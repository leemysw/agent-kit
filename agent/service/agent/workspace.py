# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：workspace.py
# @Date   ：2026/2/25 23:15
# @Author ：leemysw
#
# 2026/2/25 23:15   Create
# 2026/3/4  15:09   重构：从全局单例改为 Agent 级别实例
# =====================================================

"""
Agent Workspace 管理器

[INPUT]: 依赖 agent.core.config 的 settings.WORKSPACE_PATH
[OUTPUT]: 对外提供 AgentWorkspace 类（读写 Workspace .md 文件，构建 system prompt 和 SDK options）
[POS]: agent 模块的工作区管理层，被 AgentManager 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import os
from pathlib import Path
from typing import Optional

from agent.utils.logger import logger


# =====================================================
# Workspace 文件定义
# =====================================================

WORKSPACE_FILES = {
    "agents": "AGENTS.md",       # Agent 核心行为 → system prompt
    "identity": "IDENTITY.md",   # 身份定义（名称、头像）
    "soul": "SOUL.md",           # 人设/性格
    "user": "USER.md",           # 用户偏好
    "memory": "MEMORY.md",       # 核心记忆（每次会话必读）
    "heartbeat": "HEARTBEAT.md", # 心跳任务定义
    "tools": "TOOLS.md",         # 工具使用指引
}


class AgentWorkspace:
    """Agent 的专属工作区

    每个 Agent 拥有独立的 workspace 目录，包含 prompt 文件和记忆。
    Agent 的所有 session 共享同一个 workspace。
    """

    def __init__(self, agent_id: str, base_path: Path):
        self.agent_id = agent_id
        self.path = base_path / agent_id

    def ensure_exists(self) -> None:
        """确保 Workspace 目录和子目录存在"""
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "memory").mkdir(exist_ok=True)
        logger.info(f"📁 Workspace 就绪: {self.path}")

    # =====================================================
    # 读写
    # =====================================================

    def read_file(self, name: str) -> Optional[str]:
        """读取 Workspace 文件内容"""
        filename = WORKSPACE_FILES.get(name)
        if not filename:
            return None
        filepath = self.path / filename
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8").strip()

    def write_file(self, name: str, content: str) -> bool:
        """写入 Workspace 文件"""
        filename = WORKSPACE_FILES.get(name)
        if not filename:
            logger.warning(f"⚠️ 未知的 Workspace 文件: {name}")
            return False
        filepath = self.path / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"📝 写入 Workspace: {filepath.name}")
        return True

    # =====================================================
    # System Prompt 构建
    # =====================================================

    def build_system_prompt(self) -> Optional[str]:
        """从 Workspace 文件构建 system prompt

        读取顺序: AGENTS.md → IDENTITY.md → SOUL.md → USER.md → MEMORY.md → TOOLS.md
        跳过不存在的文件。每次调用重新读取，修改后立即生效。
        """
        sections = []
        for name in ["agents", "identity", "soul", "user", "memory", "tools"]:
            content = self.read_file(name)
            if content:
                sections.append(content)

        if not sections:
            return None

        return "\n\n---\n\n".join(sections)

    def build_sdk_options(self) -> dict:
        """构建 ClaudeAgentOptions 的 workspace 相关配置"""
        options = {"cwd": str(self.path)}
        prompt = self.build_system_prompt()
        if prompt:
            options["system_prompt"] = prompt
        return options

    # =====================================================
    # 记忆存储
    # =====================================================

    def save_memory(self, filename: str, content: str) -> None:
        """保存会话摘要到 memory/ 目录"""
        memory_dir = self.path / "memory"
        memory_dir.mkdir(exist_ok=True)
        filepath = memory_dir / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"💾 保存记忆: {filepath}")


# =====================================================
# Workspace 基础路径
# =====================================================

def get_workspace_base_path() -> Path:
    """获取 workspace 基础路径"""
    from agent.core.config import settings
    workspace_path = getattr(settings, "WORKSPACE_PATH", None)
    if not workspace_path:
        workspace_path = os.path.join(os.getcwd(), "workspace")
    return Path(workspace_path)
