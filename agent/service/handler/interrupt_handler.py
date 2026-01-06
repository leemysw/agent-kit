#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：interrupt_handler.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# =====================================================

import asyncio
import uuid
from typing import Any, Dict

from claude_agent_sdk.types import ResultMessage

from agent.service.handler.base_handler import BaseHandler
from agent.service.schema.model_message import AMessage
from agent.service.session_manager import session_manager
from agent.service.session_store import session_store
from agent.utils.logger import logger


class InterruptHandler(BaseHandler):
    """中断消息处理器"""

    async def handle_interrupt(self, message: Dict[str, Any], chat_tasks: Dict[str, asyncio.Task]) -> None:
        """
        处理中断消息

        Args:
            message: 中断消息，包含agent_id
            chat_tasks: 正在运行的chat任务
        """
        agent_id = message.get("agent_id")
        if not agent_id:
            logger.warning("⚠️interrupt 消息缺少 agent_id")
            return

        # 在后台任务中执行中断流程，避免阻塞其他消息
        asyncio.create_task(self._handle_interrupt_async(agent_id, chat_tasks))

    async def _handle_interrupt_async(self, agent_id: str, chat_tasks: Dict[str, asyncio.Task]) -> None:
        """
        异步执行中断流程

        流程：
        1. 调用 SDK interrupt
        2. 等待任务自然结束（最多10秒）
        3. 超时后强制取消任务
        4. 发送中断结果消息

        Args:
            agent_id: 会话ID
            chat_tasks: 正在运行的chat任务
        """
        try:
            # 1. 先调用 SDK 的 interrupt
            client = await session_manager.get_session(agent_id)
            if client:
                await client.interrupt()
                logger.info(f"⏸️中断会话: agent_id={agent_id}")
            else:
                logger.warning(f"⚠️未找到会话client: agent_id={agent_id}")
                return

            # 2. 等待任务自然结束（最多10秒）

            chat_task = chat_tasks[agent_id]
            if agent_id in chat_tasks and not chat_task.done():
                try:
                    await asyncio.wait_for(chat_task, timeout=10.0)
                    logger.info(f"✅任务自然结束: {agent_id}")
                except asyncio.TimeoutError:
                    # 3. 超时后强制取消
                    logger.info(f"🛑强制取消任务: {agent_id}")
                    chat_task.cancel()
                    try:
                        await chat_task
                        # 4. 如果任务被强制取消，发送中断结果消息
                        await self._send_interrupt_result(agent_id)
                    except asyncio.CancelledError:
                        pass
            elif agent_id in chat_tasks and chat_task.done():
                logger.info(f"✅任务自然结束: {agent_id}")
            else:
                logger.warning(f"⚠️未找到任务: {agent_id}")

        except Exception as e:
            logger.error(f"❌中断处理失败: {e}")

    async def _send_interrupt_result(self, agent_id: str) -> None:
        """发送中断结果消息"""
        session_id = session_manager.get_session_id(agent_id)
        round_id = await session_store.get_latest_round_id(agent_id)

        if not round_id:
            logger.warning(f"⚠️无法获取 round_id: agent_id={agent_id}")
            return

        result_message = AMessage(
            agent_id=agent_id,
            round_id=round_id,
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            message=ResultMessage(
                subtype="interrupted",
                duration_ms=0,
                duration_api_ms=0,
                is_error=True,
                num_turns=0,
                session_id=session_id,
                total_cost_usd=0,
                usage={
                    "input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 0,
                    "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
                    "service_tier": "standard",
                    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}
                },
                result="用户中断",
            ),
            message_type="result",
        )

        await session_store.save_message(result_message)
        logger.info(f"💾保存中断消息: agent_id={agent_id}, round_id={round_id}")

        await self.send(result_message)
