# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：__init__.py
# @Date   ：2026/2/25 23:15
# @Author ：leemysw
#
# 2026/2/25 23:15   Create
# =====================================================

"""
智能体模块

[OUTPUT]: 对外提供 Workspace, get_workspace
[POS]: agent/service/agent 的模块入口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from agent.service.agent.workspace import Workspace, get_workspace

__all__ = ["Workspace", "get_workspace"]
