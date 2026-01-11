#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：permission_handler.py
# @Date   ：2025/12/06
# @Author ：leemysw
#
# 2025/12/06   Create
# =====================================================

import asyncio
from typing import Any, Dict

from claude_agent_sdk import PermissionResult, PermissionResultAllow, PermissionResultDeny
from fastapi import WebSocket

from agent.service.handler.base_handler import BaseHandler
from agent.service.schema.model_message import AEvent
from agent.service.session_manager import session_manager
from agent.utils.logger import logger


class PermissionHandler(BaseHandler):
    """权限请求处理器"""

    def __init__(self, websocket: WebSocket):
        super().__init__(websocket)

        # 跟踪权限请求和响应
        self._permission_requests: Dict[str, asyncio.Event] = {}
        self._permission_responses: Dict[str, Dict[str, Any]] = {}

    async def request_permission(self, agent_id: str, tool_name: str, input_data: dict[str, Any]) -> PermissionResult:
        """
        请求前端用户权限确认

        Args:
            agent_id: 会话ID
            tool_name: 工具名称
            input_data: 工具输入参数

        Returns:
            权限决策结果
        """
        import uuid
        request_id = str(uuid.uuid4())

        logger.info(f"🔐 请求工具权限: agent_id={agent_id}, tool={tool_name}, request_id={request_id}")

        # 创建等待事件
        event = asyncio.Event()
        self._permission_requests[request_id] = event

        # 发送权限请求到前端
        permission_event = AEvent(
            event_type="permission_request",
            agent_id=agent_id,
            session_id=session_manager.get_session_id(agent_id),
            data={
                "request_id": request_id,
                "tool_name": tool_name,
                "tool_input": input_data
            }
        )
        await self.send(permission_event)

        # 等待前端响应（60秒超时）
        try:
            await asyncio.wait_for(event.wait(), timeout=60.0)

            # 获取响应
            response = self._permission_responses.get(request_id, {})
            decision = response.get("decision", "deny")

            # 清理
            del self._permission_requests[request_id]
            if request_id in self._permission_responses:
                del self._permission_responses[request_id]

            if decision == "allow":
                logger.info(f"✅ 权限允许: {tool_name}")

                # 如果是 AskUserQuestion，构建 SDK 要求的 answers 格式
                updated_input = input_data.copy()
                if tool_name == "AskUserQuestion" and "user_answers" in response:
                    user_answers = response["user_answers"]
                    questions = input_data.get("questions", [])

                    # 构建 {question_text: selected_labels} 格式
                    answers = {}
                    for answer in user_answers:
                        question_idx = answer.get("questionIndex", 0)
                        selected_options = answer.get("selectedOptions", [])

                        if 0 <= question_idx < len(questions):
                            question_text = questions[question_idx].get("question", "")
                            # 多选用 ", " 连接
                            answers[question_text] = ", ".join(selected_options)

                    updated_input["answers"] = answers
                    logger.info(f"📝 AskUserQuestion 用户回答: {answers}")

                return PermissionResultAllow(updated_input=updated_input)
            else:
                logger.info(f"❌ 权限拒绝: {tool_name}")
                return PermissionResultDeny(message=response.get("message", "User denied permission"))

        except asyncio.TimeoutError:
            logger.warning(f"⏰ 权限请求超时: {tool_name}")
            # 清理
            del self._permission_requests[request_id]
            return PermissionResultDeny(message="Permission request timeout")

    async def handle_permission_response(self, message: Dict[str, Any]) -> None:
        """
        处理前端权限响应

        Args:
            message: 权限响应消息
        """
        request_id = message.get("request_id")
        if not request_id:
            logger.warning("⚠️ permission_response消息缺少request_id")
            return

        # 保存响应
        response_data = {
            "decision": message.get("decision", "deny"),
            "message": message.get("message", "")
        }

        # 如果是 AskUserQuestion 的回答，直接保存原始用户答案
        user_answers = message.get("user_answers")
        if user_answers:
            response_data["user_answers"] = user_answers
            logger.debug(f"📝 收到 AskUserQuestion 用户答案: {user_answers}")

        self._permission_responses[request_id] = response_data

        # 触发等待事件
        if request_id in self._permission_requests:
            self._permission_requests[request_id].set()
            logger.debug(f"📨 收到权限响应: request_id={request_id}, decision={message.get('decision')}")
        else:
            logger.warning(f"⚠️ 未找到对应的权限请求: request_id={request_id}")
