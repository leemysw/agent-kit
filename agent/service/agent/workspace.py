# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：workspace.py
# @Date   ：2026/2/25 23:15
# @Author ：leemysw
#
# 2026/2/25 23:15   Create
# =====================================================

"""
Workspace 管理器

[INPUT]: 依赖 agent.core.config 的 settings.WORKSPACE_PATH
[OUTPUT]: 对外提供 Workspace 类（读写 Workspace .md 文件，构建 system prompt）
[POS]: agent 模块的工作区管理层，被 ChatHandler 在创建 SDK client 时消费
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
    "agents": "AGENTS.md",      # Agent 核心行为 → system prompt
    "identity": "IDENTITY.md",  # 身份定义（名称、头像）
    "soul": "SOUL.md",          # 人设/性格
    "user": "USER.md",          # 用户偏好
    "memory": "MEMORY.md",      # 核心记忆（每次会话必读）
    "heartbeat": "HEARTBEAT.md",# 心跳任务定义
    "tools": "TOOLS.md",        # 工具使用指引
}


class Workspace:
    """Agent Workspace 管理器"""

    def __init__(self, workspace_path: str):
        self.path = Path(workspace_path)

    def ensure_exists(self) -> None:
        """确保 Workspace 目录和子目录存在"""
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "memory").mkdir(exist_ok=True)
        logger.info(f"📁 Workspace 就绪: {self.path}")

    # =====================================================
    # 读写
    # =====================================================

    def read_file(self, name: str) -> Optional[str]:
        """读取 Workspace 文件内容

        Args:
            name: 文件键名（如 "agents"、"memory"）

        Returns:
            文件内容，文件不存在返回 None
        """
        filename = WORKSPACE_FILES.get(name)
        if not filename:
            return None
        filepath = self.path / filename
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8").strip()

    def write_file(self, name: str, content: str) -> bool:
        """写入 Workspace 文件

        Args:
            name: 文件键名
            content: 文件内容

        Returns:
            是否成功
        """
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
        跳过不存在的文件。
        """
        sections = []

        for name in ["agents", "identity", "soul", "user", "memory", "tools"]:
            content = self.read_file(name)
            if content:
                sections.append(content)

        if not sections:
            return None

        return "\n\n---\n\n".join(sections)

    # =====================================================
    # 会话摘要存储
    # =====================================================

    def save_memory(self, filename: str, content: str) -> None:
        """保存会话摘要到 memory/ 目录

        Args:
            filename: 文件名（如 "2026-02-25.md"）
            content: 摘要内容
        """
        memory_dir = self.path / "memory"
        memory_dir.mkdir(exist_ok=True)
        filepath = memory_dir / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"💾 保存记忆: {filepath}")


# =====================================================
# 全局 Workspace 实例（延迟初始化）
# =====================================================

_workspace: Optional[Workspace] = None


def get_workspace() -> Workspace:
    """获取全局 Workspace 实例"""
    global _workspace
    if _workspace is None:
        from agent.core.config import settings
        workspace_path = getattr(settings, "WORKSPACE_PATH", None)
        if not workspace_path:
            workspace_path = os.path.join(os.getcwd(), "workspace")
        _workspace = Workspace(workspace_path)
        _workspace.ensure_exists()
    return _workspace
