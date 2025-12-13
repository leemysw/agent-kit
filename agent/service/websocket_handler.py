# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：websocket_handler.py
# @Date   ：2025/11/28 15:27
# @Author ：leemysw

# 2025/11/28 15:27   Create
# =====================================================

import asyncio
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from agent.service.handler import ChatHandler, ErrorHandler, InterruptHandler, PermissionHandler, PingHandler
from agent.service.session_manager import session_manager
from agent.utils.logger import logger


class WebSocketHandler:
    """WebSocket消息处理器"""

    def __init__(self):
        self.websocket: Optional[WebSocket] = None
        # 跟踪每个agent_id的处理任务
        self.chat_tasks: Dict[str, asyncio.Task] = {}

        self.permission_handler: Optional[PermissionHandler] = None
        self.chat_handler: Optional[ChatHandler] = None
        self.interrupt_handler: Optional[InterruptHandler] = None
        self.ping_handler: Optional[PingHandler] = None
        self.error_handler: Optional[ErrorHandler] = None

    def init_handlers(self, websocket: WebSocket) -> None:
        # 初始化各个处理器
        self.permission_handler = PermissionHandler(websocket)
        self.chat_handler = ChatHandler(websocket, self.permission_handler)
        self.interrupt_handler = InterruptHandler(websocket)
        self.ping_handler = PingHandler(websocket)
        self.error_handler = ErrorHandler(websocket)

    async def handle_websocket_connection(self, websocket: WebSocket) -> None:
        """
        处理WebSocket连接的主要逻辑

        Args:
            websocket: FastAPI WebSocket实例
        """
        self.websocket = websocket
        await self.websocket.accept()
        self.init_handlers(websocket)

        try:
            while True:
                # 接收前端消息
                message = await self.websocket.receive_json()
                logger.debug(f"💌收到消息: {message}")
                msg_type = message.get("type")
                await self.on_message(message, msg_type)
        except WebSocketDisconnect as wde:
            raise wde
        except Exception as e:
            await self.error_handler.handle_websocket_error(e)
        finally:
            await self.on_close()

    async def on_message(self, message: Dict[str, Any], msg_type: str) -> None:
        """
        根据消息类型处理消息

        Args:
            message: 消息内容
            msg_type: 消息类型
        """
        if msg_type == "chat":
            await self.chat_handler.handle_chat_message_with_task(message, self.chat_tasks)
        elif msg_type == "interrupt":
            await self.interrupt_handler.handle_interrupt(message, self.chat_tasks)
        elif msg_type == "permission_response":
            await self.permission_handler.handle_permission_response(message)
        elif msg_type == "ping":
            await self.ping_handler.handle_ping(message)
        else:
            await self.error_handler.handle_unknown_message_type(message)

    async def on_close(self) -> None:
        """清理WebSocket连接资源"""
        logger.info("🧹 WebSocket连接清理")

        # 1. 取消所有正在运行的chat任务
        for agent_id, task in self.chat_tasks.items():
            if not task.done():
                logger.info(f"🛑 清理: 取消chat任务 {agent_id}")
                task.cancel()

            # 2. 调用SDK的interrupt停止生成
            try:
                client = await session_manager.get_session(agent_id)
                if client:
                    await client.interrupt()
                    logger.info(f"⏸️ 清理: 中断SDK生成 {agent_id}")
            except Exception as e:
                logger.warning(f"⚠️ 中断SDK失败 {agent_id}: {e}")

        # 3. 等待所有任务完成取消
        if self.chat_tasks:
            await asyncio.gather(*self.chat_tasks.values(), return_exceptions=True)

        self.chat_tasks.clear()
        self.websocket = None
