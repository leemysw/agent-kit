#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：chat_handler.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# 2026/2/25    重构：接受 PermissionStrategy 替代 PermissionHandler
# =====================================================

"""
聊天消息处理器

[INPUT]: 依赖 channel.channel 的 MessageSender/PermissionStrategy,
         依赖 session_manager 和 session_store 管理会话,
         依赖 ChatMessageProcessor 处理 SDK 响应
[OUTPUT]: 对外提供 ChatHandler
[POS]: handler 模块的核心处理器，负责用户消息 → Agent 调用 → 流式响应
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
from typing import Any, Dict

from claude_agent_sdk import ClaudeSDKClient, PermissionResult, ToolPermissionContext

from agent.service.channel.channel import MessageSender, PermissionStrategy
from agent.service.handler.base_handler import BaseHandler
from agent.service.process.chat_message_processor import ChatMessageProcessor
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.utils.logger import logger


class ChatHandler(BaseHandler):
    """聊天消息处理器"""

    def __init__(self, sender: MessageSender, permission_strategy: PermissionStrategy):
        super().__init__(sender)
        self.permission_strategy = permission_strategy

    async def handle_chat_message_with_task(
            self,
            message: Dict[str, Any],
            chat_tasks: Dict[str, Any],
    ) -> None:
        """处理聊天消息，包含任务管理逻辑"""
        agent_id = message.get("agent_id")
        if not agent_id:
            error_response = self.create_error_response(
                error_type="validation_error",
                message="agent_id is required for chat messages",
            )
            await self.send(error_response)
            return

        # 如果有正在运行的任务，先取消
        if agent_id in chat_tasks and not chat_tasks[agent_id].done():
            logger.info(f"⚠️ 取消旧的chat任务: {agent_id}")
            chat_tasks[agent_id].cancel()

        # 创建新任务
        task = asyncio.create_task(self.handle_chat_message(message))
        chat_tasks[agent_id] = task

        task.add_done_callback(lambda t: self.on_chat_task_done(agent_id, t))

    @staticmethod
    def on_chat_task_done(agent_id: str, task: asyncio.Task) -> None:
        """chat任务完成回调"""
        if task.cancelled():
            logger.info(f"🛑chat任务被取消: {agent_id}")
        elif task.exception():
            logger.error(f"❌chat任务异常: {agent_id}, error={task.exception()}")
        else:
            logger.debug(f"✅chat任务完成: {agent_id}")

    async def handle_chat_message(self, message: Dict[str, Any]) -> None:
        """处理聊天消息 — 懒加载模式"""
        agent_id = message.get("agent_id")
        content = message.get("content")
        round_id = message.get("round_id")

        # 按需获取或创建 client
        try:
            client = await self._get_or_create_client(agent_id)
        except Exception as e:
            logger.error(f"❌获取client失败: {e}")
            error_response = self.create_error_response(
                error_type="client_error",
                message=f"Failed to get or create client: {str(e)}",
                agent_id=agent_id,
            )
            await self.send(error_response)
            return

        # 使用锁确保同一会话的顺序处理
        async with session_manager.get_lock(agent_id):
            logger.info(f"📨处理消息: agent_id={agent_id}, round_id={round_id}")

            await client.query(content)

            # 初始化消息处理器
            processor = ChatMessageProcessor(agent_id=agent_id, query=content, round_id=round_id)

            # 流式响应
            async for response_msg in client.receive_messages():
                processed_messages = await processor.process_messages(response_msg)
                for a_message in processed_messages:
                    await self.send(a_message)
                if processor.subtype in ["success", "error"]:
                    break

            logger.info(f"✅消息处理完成: agent_id={agent_id}, 共处理 {processor.message_count} 条响应消息")

    async def _get_or_create_client(self, agent_id: str) -> ClaudeSDKClient:
        """懒加载：按需获取或创建 SDK client"""
        # 1. 检查内存中是否已有 client
        client = await session_manager.get_session(agent_id)
        if client:
            logger.debug(f"♻️ 复用现有session: {agent_id}")
            return client

        # 2. 查询数据库获取 session 配置
        existing_session = await session_store.get_session_info(agent_id)

        session_options = None
        session_id = None
        if existing_session:
            session_options = existing_session.options
            session_id = existing_session.session_id

        # 确保 session_options 中有 cwd（Discord/Telegram 新会话可能没有）
        if not session_options:
            session_options = {}
        if "cwd" not in session_options or not session_options["cwd"]:
            import os
            session_options["cwd"] = os.getcwd()
            logger.info(f"📁 使用默认 cwd: {session_options['cwd']}")

        # 3. 创建权限回调 — 委托给 PermissionStrategy
        async def can_use_tool(name: str, data: dict[str, Any], context: ToolPermissionContext) -> PermissionResult:
            return await self.permission_strategy.request_permission(agent_id, name, data)

        # 4. 创建 client
        client = await session_manager.create_session(
            agent_id=agent_id,
            can_use_tool=can_use_tool,
            session_id=session_id,
            session_options=session_options,
        )

        # 5. 连接 SDK
        await client.connect()

        logger.info(f"✅ Client准备就绪: agent_id={agent_id}, session_id={session_id}")
        return client
