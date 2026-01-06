#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：chat_message_processor.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# =====================================================

import uuid
from typing import Optional

from claude_agent_sdk import Message, ResultMessage, SystemMessage, UserMessage

from agent.service.process.sdk_message_processor import sdk_message_processor
from agent.service.schema.model_message import AMessage
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.utils.logger import logger


class ChatMessageProcessor:
    """单轮聊天消息处理器 - 管理消息状态和处理逻辑"""

    def __init__(self, agent_id: str, query: str, round_id: Optional[str] = None):
        self.query = query
        self.agent_id = agent_id
        self.subtype: Optional[str] = None
        # 如果前端提供了 round_id 则使用，否则后端会在 save_user_message 时生成
        self.round_id: Optional[str] = round_id
        self.parent_id: Optional[str] = None
        self.session_id: Optional[str] = None

        self.message_count: int = 0
        self.is_streaming: bool = False
        self.is_streaming_tool: bool = False
        self.is_save_user_message: bool = False
        self.stream_message_id: Optional[str] = None

    async def process_messages(self, response_msg: Message) -> list[AMessage]:
        """
        处理响应消息，管理消息状态

        Args:
            response_msg: 从SDK接收的原始响应消息

        Returns:
            processed_messages
        """

        # 打印消息
        sdk_message_processor.print_message(response_msg, self.agent_id)

        # 获取session_id并建立映射关系，保存用户消息（如果是第一次）
        self.set_subtype(response_msg)
        self.set_session_id(response_msg)
        await self.save_user_message(self.query)

        # 转换为AMessage对象并处理
        messages = sdk_message_processor.process_message(
            message=response_msg,
            agent_id=self.agent_id,
            session_id=self.session_id,
            round_id=self.round_id,
            parent_id=self.parent_id,
        )

        # 处理所有返回的消息
        processed_messages = []
        for a_message in messages:
            # 处理流式消息状态
            self.update_stream_state(a_message)

            # 不推送流失的工具消息
            if a_message.message_type == "stream" and self.is_streaming_tool:
                continue

            # 更新parent_id（非stream消息）
            if a_message.message_type != "stream":
                self.parent_id = a_message.message_id
                await session_store.save_message(a_message)

            processed_messages.append(a_message)
            self.message_count += 1

        return processed_messages

    def set_session_id(self, response_msg: Message) -> Optional[str]:
        """
        处理session映射关系

        Args:
            response_msg: 处理后的消息列表
        """

        if self.session_id is None:
            if isinstance(response_msg, SystemMessage):
                self.session_id = response_msg.data.get("session_id", None)
            else:
                raise ValueError("⚠️When session_id is None, response_msg must be a SystemMessage")

            # 建立映射关系并更新数据库
            session_manager.register_sdk_session(agent_id=self.agent_id, session_id=self.session_id)
            # 注意：这里不直接更新数据库，而是返回给调用者处理
            logger.debug(f"🔗需要建立映射: agent_id={self.agent_id} ↔ sdk_session={self.session_id}")

    def set_subtype(self, response_msg: Message) -> None:
        """
        设置消息子类型

        Args:
            response_msg: 处理后的消息列表
        """

        if hasattr(response_msg, 'subtype'):
            self.subtype = response_msg.subtype

        if isinstance(response_msg, ResultMessage):
            if response_msg.subtype == "success":
                self.subtype = "success"
            else:
                self.subtype = "error"

    def update_stream_state(self, a_message: AMessage) -> None:
        """
        更新流式处理状态

        Args:
            a_message: 消息对象
        """
        if a_message.message_type == "stream" and a_message.message.event["type"] == "message_start":
            # 开启流式，记录stream_message_id
            self.is_streaming = True
            self.stream_message_id = a_message.message_id

        if self.is_streaming:
            if a_message.message_type == "stream":
                a_message.message_id = self.stream_message_id

                if a_message.message.event["type"] == "content_block_start":
                    if a_message.message.event["content_block"]["type"] == "tool_use":
                        self.is_streaming_tool = True

                if self.is_streaming_tool and a_message.message.event["type"] == "content_block_stop":
                    self.is_streaming_tool = False

            elif a_message.message_type == "assistant":
                # 交换消息ID
                a_message.message_id, self.stream_message_id = self.stream_message_id, a_message.message_id
                self.parent_id = a_message.message_id

        if a_message.message_type == "stream" and a_message.message.event["type"] == "message_stop":
            # 关闭流式，清空stream_message_id
            self.is_streaming = False
            self.stream_message_id = None

    async def save_user_message(self, content: str):
        """
        保存的用户消息

        Args:
            content: 用户消息内容
        """

        if not self.is_save_user_message:
            # 如果前端没有提供 round_id，则后端生成
            if not self.round_id:
                self.round_id = str(uuid.uuid4())

            user_message = AMessage(
                agent_id=self.agent_id,
                round_id=self.round_id,
                message_id=self.round_id,
                session_id=self.session_id,
                message_type="user",
                block_type="text",
                message=UserMessage(content=content)
            )

            await session_store.save_message(user_message)
            await session_manager.increment_message_count(self.agent_id)

            self.is_save_user_message = True
