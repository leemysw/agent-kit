# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：session_store.py
# @Date   ：2025/11/28 22:29
# @Author ：leemysw

# 2025/11/28 22:29   Create
# =====================================================

from typing import Dict, List, Optional

from agent.service.db.session_repository import session_repository
from agent.service.schema.model_message import AMessage
from agent.service.schema.model_session import ASession
from agent.utils.logger import logger


class MessageHistoryStore:
    """消息历史存储 - 使用ORM持久化会话和消息"""

    def __init__(self):
        logger.info(f"📁 历史存储初始化: 使用ORM")

    async def save_message(self, message: AMessage) -> bool:
        """
        保存消息到历史记录

        Args:
            message: 消息对象

        Returns:
            bool: 是否成功保存
        """
        try:
            # 确保会话存在，不存在则创建
            session_info = await session_repository.get_session(message.agent_id)
            if not session_info:
                raise Exception(f"❌ 会话不存在: {message.agent_id}")

            # 保存消息
            success = await session_repository.create_message(message=message)

            if success:
                logger.debug(f"💾 保存消息成功: {message.message_id}")
            return success

        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}")
            return False

    async def get_session_messages(self, agent_id: str) -> List[ASession]:
        """
        获取会话的所有历史消息

        Args:
            agent_id: 客户端会话ID

        Returns:
            List[Dict]: 消息列表
        """
        try:
            messages = await session_repository.get_session_messages(agent_id)
            logger.info(f"📥 加载历史消息: {agent_id}, 共{len(messages)}条")
            return messages

        except Exception as e:
            logger.error(f"❌ 获取历史消息失败: {e}")
            return []

    async def update_session(
            self,
            agent_id: str,
            session_id: Optional[str] = None,
            title: Optional[str] = None,
            options: Optional[Dict] = None
    ) -> bool:
        """
        创建或更新会话信息

        Args:
            agent_id: 前端会话ID (主键)
            session_id: SDK内部会话ID
            title: 会话标题
            options: 会话配置选项

        Returns:
            bool: 是否成功更新
        """
        try:
            session_info = await session_repository.get_session(agent_id)

            if not session_info:
                # 创建新会话
                success = await session_repository.create_session(
                    agent_id=agent_id,
                    session_id=session_id,
                    title=title or 'New Chat',
                    options=options
                )
                if success:
                    logger.info(f"✅ 创建会话记录: agent_id={agent_id}, session_id={session_id}")
                return success
            else:
                # 更新会话
                success = await session_repository.update_session(
                    agent_id=agent_id,
                    session_id=session_id,
                    title=title,
                    options=options
                )
                if success:
                    logger.info(f"🔄 更新会话记录: agent_id={agent_id}")
                return success

        except Exception as e:
            logger.error(f"❌ 更新会话失败: {e}")
            return False

    async def get_session_info(self, agent_id: str) -> Optional[ASession]:
        """
        获取会话信息

        Args:
            agent_id: 客户端会话ID

        Returns:
            Optional[Dict]: 会话信息
        """
        try:
            session_info = await session_repository.get_session(agent_id)
            return session_info

        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: {e}")
            return None

    async def get_all_sessions(self) -> List[ASession]:
        """
        获取所有会话列表（按最后活动时间降序）

        Returns:
            List[Dict]: 会话列表
        """
        try:
            sessions = await session_repository.get_all_sessions()
            logger.info(f"📋 获取会话列表: 共{len(sessions)}个会话")
            return sessions

        except Exception as e:
            logger.error(f"❌ 获取会话列表失败: {e}")
            return []

    async def delete_session(self, agent_id: str) -> bool:
        """
        删除会话及其所有消息

        Args:
            agent_id: 客户端会话ID

        Returns:
            bool: 是否成功删除
        """
        try:
            success = await session_repository.delete_session(agent_id)
            if success:
                logger.info(f"🗑️ 删除会话: {agent_id}")
            return success

        except Exception as e:
            logger.error(f"❌ 删除会话失败: {e}")
            return False

    async def delete_round(self, agent_id: str, round_id: str) -> int:
        """
        删除一轮对话的所有消息

        Args:
            agent_id: 客户端会话ID
            round_id: 轮次ID

        Returns:
            int: 删除的消息数量，-1 表示失败
        """
        try:
            deleted_count = await session_repository.delete_round(agent_id, round_id)
            if deleted_count >= 0:
                logger.info(f"🗑️ 删除轮次: {agent_id}/{round_id}, 共{deleted_count}条")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ 删除轮次失败: {e}")
            return -1

    async def get_latest_round_id(self, agent_id: str) -> str | None:
        """
        获取指定 agent_id 最新的 round_id

        Args:
            agent_id: 客户端会话ID

        Returns:
            str | None: 最新的 round_id，如果没有消息则返回 None
        """
        try:
            round_id = await session_repository.get_latest_round_id(agent_id)
            return round_id
        except Exception as e:
            logger.error(f"❌ 获取最新 round_id 失败: {e}")
            return None


# 全局实例
session_store = MessageHistoryStore()
