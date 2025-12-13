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
from typing import Any, Dict

from agent.service.handler.base_handler import BaseHandler
from agent.service.schema.model_message import AEvent, AStatus
from agent.service.session_manager import session_manager
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
            logger.warning("⚠️ interrupt消息缺少agent_id")
            return

        # 1. 取消正在运行的chat任务
        if agent_id in chat_tasks and not chat_tasks[agent_id].done():
            logger.info(f"🛑 取消chat任务: {agent_id}")
            chat_tasks[agent_id].cancel()
            # 等待任务完成取消
            try:
                await chat_tasks[agent_id]
            except asyncio.CancelledError:
                pass

        # 2. 调用SDK的interrupt
        client = await session_manager.get_session(agent_id)
        if client:
            await client.interrupt()
            logger.info(f"⏸️中断会话: agent_id={agent_id}")

            # 创建中断事件
            event = AEvent(
                event_type="interrupted",
                agent_id=agent_id,
                session_id=session_manager.get_session_id(agent_id),
                data=AStatus().model_dump(),
            )

            await self.send(event)
        else:
            logger.warning(f"⚠️ 未找到会话client: agent_id={agent_id}")
