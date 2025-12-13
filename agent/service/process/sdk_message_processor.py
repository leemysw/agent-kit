# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：sdk_message_processor.py
# @Date   ：2025/11/28
# @Author ：leemysw
# @Description ：Claude Agent SDK 消息处理器，将 SDK 消息类型转换为 JSON 格式
# =====================================================

import copy
import json
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List

from claude_agent_sdk.types import AssistantMessage, Message, ResultMessage, StreamEvent, SystemMessage, UserMessage
from claude_agent_sdk.types import ContentBlock, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock

from agent.service.schema.model_message import AMessage
from agent.utils.logger import logger


class SDKMessageProcessor:
    """Claude Agent SDK 消息处理器

    将 Claude Agent SDK 的各种消息类型转换为 JSON 格式，
    在保留原始数据的基础上添加 type 字段来标识消息类型。
    """

    def __init__(self):
        """初始化消息处理器"""
        self.message_type_mapping = {
            AssistantMessage: "assistant",
            UserMessage: "user",
            SystemMessage: "system",
            ResultMessage: "result",
            StreamEvent: "stream"
        }

        self.content_block_mapping = {
            TextBlock: "text",
            ThinkingBlock: "thinking",
            ToolUseBlock: "tool_use",
            ToolResultBlock: "tool_result"
        }

    def process_message(
            self, message: Message, agent_id: str, session_id: str, round_id: str, parent_id: str = None
    ) -> List[AMessage]:
        """处理 Claude Agent SDK 消息

        Args:
            message: Claude Agent SDK 消息对象
            agent_id: 聊天ID（可选）
            session_id: 会话ID
            round_id: 轮次ID
            parent_id: 父消息ID（可选）

        Returns:
            List[Dict]: 在原始数据基础上添加 type 字段的 JSON 可序列化字典列表
        """

        # 只对 AssistantMessage 和 UserMessage 进行特殊处理
        if isinstance(message, (AssistantMessage, UserMessage)):
            messages = self._process_assistant_user_message(message)
        else:
            messages = [message]

        # 其他类型消息保持原逻辑
        # 特殊处理 content 字段中的内容块
        a_messages = []
        for message in messages:
            if isinstance(message, (AssistantMessage, UserMessage)):
                block_type = self.content_block_mapping.get(type(message.content[0]))
            else:
                block_type = None

            message = AMessage(
                message_type=self.message_type_mapping.get(type(message)),  # noqa
                block_type=block_type,  # noqa
                message=message,
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                agent_id=agent_id,
                round_id=round_id,
                parent_id=parent_id,
            )
            a_messages.append(message)

        return a_messages

    @staticmethod
    def _process_assistant_user_message(message: Message) -> List[Message]:
        """处理 AssistantMessage 和 UserMessage 的特殊转换逻辑

        Args:
            message: AssistantMessage 或 UserMessage 对象

        Returns:
            List[Dict]: 处理后的消息字典列表
        """

        # 处理 content 为字符串的情况，转换为 TextBlock 列表
        if isinstance(message.content, str):
            # 将字符串转换为 TextBlock 列表
            text_block = TextBlock(text=message.content)
            message.content = [text_block]
            return [message]

        # 处理 content 为 ContentBlock 列表的情况
        elif isinstance(message.content, list) and len(message.content) > 0:
            # 如果只有一个 ContentBlock，保持原样
            if len(message.content) == 1:
                return [message]
            # 如果有多个 ContentBlock，拆分为多条消息
            else:
                results = []
                for i, block in enumerate(message.content):
                    # 复制原始消息的其他字段
                    new_message = copy.deepcopy(message)
                    new_message.content = [block]
                    results.append(new_message)
                return results
        else:
            raise ValueError(f"Invalid content type: {type(message.content)}")

    def _process_content_block(self, block: Any) -> Dict[str, Any]:
        """处理单个内容块，在原始数据基础上添加 type 字段"""
        try:
            # 直接使用 asdict 获取原始数据
            result = asdict(block)

            # 添加 type 字段
            block_type = self.content_block_mapping.get(type(block), "unknown_block")
            result["type"] = block_type

            return result

        except Exception as e:
            logger.error(f"❌Error processing content block {type(block)}: {e}")
            return {
                "type": "error_block",
                "error": str(e),
                "original_type": str(type(block))
            }

    def print_message(self, message: Message, session_id: str = None) -> None:
        """美观地打印消息，展示 agent 执行过程

        Args:
            message: Claude Agent SDK 消息对象
            session_id: 会话ID（可选）
        """
        # 获取当前时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 打印头部信息
        if session_id:
            print(f"🕐 [{timestamp}] 📋 Session: {session_id} - ", end="")
        else:
            print(f"🕐 [{timestamp}] 📋 Agent Message - ", end="")

        # 直接使用原始消息，不经过 process_message
        if isinstance(message, AssistantMessage):
            self._print_assistant_message(message)
        elif isinstance(message, UserMessage):
            self._print_user_message(message)
        elif isinstance(message, SystemMessage):
            self._print_system_message(message)
        elif isinstance(message, ResultMessage):
            self._print_result_message(message)
        elif isinstance(message, StreamEvent):
            # self._print_stream_event(message)
            ...
        else:
            print(f"❓ 未知消息类型: {type(message)}")
            self._print_pretty_json(asdict(message))

        print("=" * 80)
        print()

    @staticmethod
    def _print_block(block: ContentBlock) -> None:
        if isinstance(block, TextBlock):
            print(f"💬 文本: {block.text}")
        elif isinstance(block, ThinkingBlock):
            print(f"🤔 思考: {block.thinking}")
            print(f"🔑 签名: {block.signature}")
        elif isinstance(block, ToolResultBlock):
            print(f"🆔 工具ID: {block.tool_use_id}")
            if block.content:
                print(f"📈 结果: {block.content}")
            if block.is_error:
                print(f" ❌ 工具执行错误")
        elif isinstance(block, ToolUseBlock):
            print(f"🔧 工具调用: {block.name}({block.input}) -- {block.id}")

    def _print_user_message(self, message: UserMessage) -> None:
        """打印用户消息（原始格式）"""
        print(f"👤 用户消息 (User Message)")
        print("-" * 40)
        if message.parent_tool_use_id:
            print(f"🔗 父工具ID: {message.parent_tool_use_id}")

        content = message.content
        if isinstance(content, str):
            print(f"💬: {content}")
        elif isinstance(content, list):
            if len(content) == 1:
                self._print_block(content[0])
            else:
                for i, block in enumerate(content):
                    print(f"  📝 块 {i + 1}:")
                    self._print_block(block)

    def _print_assistant_message(self, message: AssistantMessage) -> None:
        """打印助手消息（原始格式）"""
        print(f"🤖 助手回复 (Assistant Message) - 模型: {message.model}")
        print("-" * 40)
        if message.parent_tool_use_id:
            print(f"🔗 父工具ID: {message.parent_tool_use_id}")

        if len(message.content) == 1:
            self._print_block(message.content[0])
        else:
            for i, block in enumerate(message.content):
                print(f"  📦 内容块 {i + 1}:")
                # 直接打印原始内容块
                self._print_block(block)

    @staticmethod
    def _print_system_message(message: SystemMessage) -> None:
        """打印系统消息（原始格式）"""
        print(f"⚙️ 系统消息 (System Message) - 类型: {message.subtype}")
        print("-" * 40)

        data = message.data
        if data:
            print("📋 数据内容:")
            for key, value in data.items():
                print(f"   • {key}: {value}")

    @staticmethod
    def _print_result_message(message: ResultMessage) -> None:
        """打印结果消息（原始格式）"""
        print(f"✅ 执行结果 (Result Message)")
        print("-" * 40)

        # 关键指标
        print("📊 执行统计:")
        print(f"   • 耗时: {message.duration_ms}ms")
        print(f"   • API耗时: {message.duration_api_ms}ms")
        print(f"   • 对话轮数: {message.num_turns}")
        print(f"   • 状态: {'✅ 成功' if not message.is_error else '❌ 失败'}")

        if message.total_cost_usd:
            print(f"   • 费用: ${message.total_cost_usd:.4f}")

        if message.usage:
            print(f"\n📈 使用详情:")
            for key, value in message.usage.items():
                print(f"   • {key}: {value}")

        if message.result:
            print(f"\n🎯 结果: {message.result}")

    @staticmethod
    def _print_stream_event(message: StreamEvent) -> None:
        """打印流事件（原始格式）"""
        print(f"🌊 流事件 (Stream Event)")
        print("-" * 40)
        if message.parent_tool_use_id:
            print(f"🔗 父工具ID: {message.parent_tool_use_id}")

        print(f"🆔 UUID: {message.uuid}")
        if message.event:
            event_data = message.event
            print("📦 事件数据:")
            for key, value in event_data.items():
                print(f"   • {key}: {value}")

    @staticmethod
    def _print_error_message(message: Dict[str, Any]) -> None:
        """打印错误消息"""
        print(f"❌ 错误消息 (Error Message)")
        print("-" * 40)

        print(f"🚨 错误: {message.get('error', 'Unknown error')}")
        print(f"🏷️ 原始类型: {message.get('original_type', 'Unknown')}")

    @staticmethod
    def _print_pretty_json(obj: Any, indent: int = 2) -> None:
        """美观地打印 JSON 对象"""
        try:
            formatted = json.dumps(obj, indent=indent, ensure_ascii=False)
            print(formatted)
        except Exception as e:
            # 如果 JSON 序列化失败，直接打印对象
            print(obj)
            print(f"❌Error printing JSON: {e}")


# 创建全局消息处理器实例
sdk_message_processor = SDKMessageProcessor()
