#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：chat_handler.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# =====================================================

import asyncio
from typing import Any, Dict

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk import PermissionResult, ToolPermissionContext

from agent.service.handler.base_handler import BaseHandler
from agent.service.process.chat_message_processor import ChatMessageProcessor
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.utils.logger import logger


class ChatHandler(BaseHandler):
    """聊天消息处理器"""

    def __init__(self, websocket, permission_handler=None):
        super().__init__(websocket)
        self.permission_handler = permission_handler

    async def handle_chat_message_with_task(
            self,
            message: Dict[str, Any],
            chat_tasks: Dict[str, Any]
    ) -> None:
        """
        处理聊天消息，包含任务管理逻辑

        Args:
            message: 聊天消息
            chat_tasks: 任务字典
        """
        agent_id = message.get("agent_id")
        if not agent_id:
            error_response = self.create_error_response(
                error_type="validation_error",
                message="agent_id is required for chat messages"
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

        # 添加回调清理已完成的任务
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
        """
        处理聊天消息 - 懒加载模式

        核心逻辑：
        1. 从消息中提取agent_id和content
        2. 按需获取或创建SDK client
        3. 处理消息并流式返回

        Args:
            message: 聊天消息，必须包含agent_id和content
        """
        agent_id = message.get("agent_id")
        content = message.get("content")
        round_id = message.get("round_id")  # 从前端获取 round_id

        # 按需获取或创建client
        try:
            client = await self._get_or_create_client(agent_id)
        except Exception as e:
            logger.error(f"❌获取client失败: {e}")
            error_response = self.create_error_response(
                error_type="client_error",
                message=f"Failed to get or create client: {str(e)}",
                agent_id=agent_id
            )
            await self.send(error_response)
            return

        # 使用锁确保同一会话的顺序处理
        async with session_manager.get_lock(agent_id):
            logger.info(f"📨处理消息: agent_id={agent_id}, round_id={round_id}")

            # 发送查询到Claude
            await client.query(content)

            # 为本轮对话初始化消息处理器，传递前端的 round_id
            processor = ChatMessageProcessor(agent_id=agent_id, query=content, round_id=round_id)

            # 流式响应回前端
            async for response_msg in client.receive_messages():
                # 处理消息状态和逻辑
                processed_messages = await processor.process_messages(response_msg)

                # 发送消息到前端
                for a_message in processed_messages:
                    await self.send(a_message)

                if processor.subtype in ['success', 'error']:
                    break

            logger.info(f"✅消息处理完成: agent_id={agent_id}, 共处理 {processor.message_count} 条响应消息")

    async def _get_or_create_client(self, agent_id: str) -> ClaudeSDKClient:
        """
        懒加载：按需获取或创建SDK client

        逻辑：
        1. 检查session_manager中是否已有client
        2. 有 → 直接返回
        3. 无 → 查询数据库判断新建/恢复

        Args:
            agent_id: 会话ID

        Returns:
            ClaudeSDKClient: SDK客户端实例
        """
        # 1. 先检查内存中是否已有client
        client = await session_manager.get_session(agent_id)
        if client:
            logger.debug(f"♻️ 复用现有session: {agent_id}")
            return client

        # 2. 查询数据库
        existing_session = await session_store.get_session_info(agent_id)

        session_id = None
        if existing_session and existing_session.session_id:
            # 历史会话，需要恢复
            session_id = existing_session.session_id
            logger.info(f"🔄恢复历史会话: agent_id={agent_id}, sdk_session={session_id}")
        else:
            # 新会话
            logger.info(f"✨创建新会话: agent_id={agent_id}")

        # 3. 创建或恢复client
        # 从session options中获取配置
        session_options = {}
        if existing_session and existing_session.options:
            session_options = existing_session.options

        # 创建权限回调
        async def can_use_tool(name: str, data: dict[str, Any], context: ToolPermissionContext) -> PermissionResult:
            return await self.permission_handler.request_permission(agent_id, name, data)

        options = ClaudeAgentOptions(can_use_tool=can_use_tool, **session_options)
        client = await session_manager.create_session(
            agent_id=agent_id,
            session_id=session_id,  # None表示新建，有值表示恢复
            options=options,
        )

        # 4. 连接SDK
        await client.connect()

        logger.info(f"✅ Client准备就绪: agent_id={agent_id}, session_id={session_id}, options={options}")
        return client
