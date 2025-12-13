#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：error_handler.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# =====================================================

from abc import ABC
from typing import Any, Dict, Optional, Union

from fastapi import WebSocket

from agent.service.schema.model_message import AError, AEvent, AMessage
from agent.utils.logger import logger


class BaseHandler(ABC):

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send(self, message: Union[AEvent, AError, AMessage]) -> None:
        """发送消息到前端"""
        logger.debug(f"💬发送消息: {message}")
        message = message.model_dump()
        message["timestamp"] = message["timestamp"].isoformat()
        await self.websocket.send_json(message)
        print("x" * 80)
        print()

    def create_error_response(
            self, error_type: str, message: str,
            agent_id: Optional[str] = None,
            session_id: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ) -> AError:
        """创建错误响应模型"""
        return AError(
            error_type=error_type,
            message=message,
            session_id=session_id,
            agent_id=agent_id,
            details=details
        )
