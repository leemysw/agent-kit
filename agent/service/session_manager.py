# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：session_manager.py
# @Date   ：2025/11/27 15:33
# @Author ：leemysw

# 2025/11/27 15:33   Create
# =====================================================


import asyncio
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from agent.service.schema.model_session import ASession
from agent.service.session_store import session_store
from agent.utils.logger import logger


class SessionManager:
    """
    管理活跃的 ClaudeSDKClient 会话。
    将 message_id 映射到客户端实例和会话数据。
    """

    def __init__(self):
        self._sessions: Dict[str, ClaudeSDKClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._session_data: Dict[str, ASession] = {}

        # SDK session ID映射 (前端session_id <-> SDK message_id)
        self._chat_sdk_map: Dict[str, str] = {}  # agent_id -> sdk_id
        self._sdk_chat_map: Dict[str, str] = {}  # sdk_id -> agent_id

    def get_a_session(self, agent_id: str) -> ASession:
        return self._session_data[agent_id]

    async def get_session(self, agent_id: str) -> Optional[ClaudeSDKClient]:
        """
        获取现有会话的客户端实例。

        Args:
            agent_id: 前端会话ID

        Returns:
            Optional[ClaudeSDKClient]: 客户端实例，如果会话不存在则返回None
        """
        client = self._sessions.get(agent_id)
        if client:
            # 更新会话活动时间
            self.update_session_activity(agent_id)
        return client

    async def create_session(
            self,
            agent_id: str,
            session_id: Optional[str] = None,
            options: Optional[ClaudeAgentOptions] = None,
    ) -> ClaudeSDKClient:
        """
        创建新会话或返回现有会话。支持resume已有会话。

        Args:
            agent_id: 前端会话ID
            session_id: SDK session ID (用于resume)
            options: Claude Agent 选项

        Returns:
            ClaudeSDKClient: 客户端实例
        """
        if agent_id in self._sessions:
            logger.info(f"🔄返回现有会话: {agent_id}")
            # 更新会话活动时间
            self.update_session_activity(agent_id)
            return self._sessions[agent_id]

        try:
            # 如果需要resume，在options中设置resume参数
            if session_id:
                if options is None:
                    options = ClaudeAgentOptions()
                options.resume = session_id
                logger.info(f"🔄恢复SDK会话: {session_id}")

            # 初始化客户端
            client = ClaudeSDKClient(options=options)
            self._sessions[agent_id] = client
            self._locks[agent_id] = asyncio.Lock()

            # 创建会话数据模型
            options.debug_stderr = None
            session = ASession(
                agent_id=agent_id,
                session_id=None,
                is_active=True,
                message_count=0,
                options=asdict(options) if options else {},
            )
            self._session_data[agent_id] = session

            # 记录到数据库
            try:
                await session_store.update_session(
                    agent_id=session.agent_id,
                    session_id=session.session_id,
                    title=session.title
                )
                logger.info(f"💾会话已记录到数据库: {agent_id}")
            except Exception as db_error:
                logger.warning(f"⚠️会话记录到数据库失败: {db_error}")

            logger.info(f"✅创建新会话: {agent_id}")
            return client

        except Exception as e:
            logger.error(f"❌创建会话失败 {agent_id}: {e}")
            raise

    def get_lock(self, agent_id: str) -> asyncio.Lock:
        """
        获取指定会话的锁，确保操作期间的线程安全。

        Args:
            agent_id: 前端会话ID

        Returns:
            asyncio.Lock: 会话锁
        """
        if agent_id not in self._locks:
            self._locks[agent_id] = asyncio.Lock()
        return self._locks[agent_id]

    async def increment_message_count(self, agent_id: str) -> int:
        """
        增加会话消息计数。

        Args:
            agent_id: 前端会话ID

        Returns:
            int: 更新后的消息数量
        """
        if agent_id in self._session_data:
            self._session_data[agent_id].message_count += 1
            self.update_session_activity(agent_id)
            return self._session_data[agent_id].message_count
        return 0

    async def update_session_options(self, agent_id: str, options: Dict) -> bool:
        """
        更新会话的 options 配置。
        如果会话正忙（ClaudeSDKClient 正在使用中），则返回 False 并跳过更新。
        如果会话空闲，则使用新的 options 重置 ClaudeSDKClient。

        Args:
            agent_id: 前端会话ID
            options: 新的选项配置

        Returns:
            bool: 是否成功更新
        """
        # 检查会话是否存在于内存中
        if agent_id not in self._sessions:
            # 会话不在内存中，跳过
            logger.info(f"❌会话不存在于内存中: {agent_id}")
            return True

        # 获取锁以确保线程安全
        async with self.get_lock(agent_id):
            try:
                # 关闭旧的 ClaudeSDKClient
                old_client = self._sessions.get(agent_id)
                try:
                    await old_client.disconnect()
                    logger.info(f"🔌断开旧的SDK连接: {agent_id}")
                except Exception as e:
                    logger.warning(f"⚠️断开旧连接时出错: {e}")

                # 移除旧的 client
                del self._sessions[agent_id]

                # 更新 session_data 中的 options
                self._session_data[agent_id].options.update(options)

                # 注意：不立即创建新的 ClaudeSDKClient
                # 新的 client 将在下次发送消息时通过 _get_or_create_client 懒加载创建
                # 这样可以使用数据库中最新的 options 配置

                logger.info(f"✅会话选项已更新，client 已重置: {agent_id}")
                return True

            except Exception as e:
                logger.error(f"❌更新会话选项失败 {agent_id}: {e}")
                return False

    def update_session_activity(self, agent_id: str):
        """
        更新会话活动时间。

        Args:
            agent_id: 会话ID
        """
        if agent_id in self._session_data:
            self._session_data[agent_id].last_activity = datetime.now()
            self._session_data[agent_id].is_active = True

    def register_sdk_session(self, agent_id: str, session_id: str) -> None:
        """
        注册 agent_id 与 SDK session_id 的映射关系
        
        Args:
            agent_id: 前端 chat ID
            session_id: SDK session ID
        """
        self._chat_sdk_map[agent_id] = session_id
        self._sdk_chat_map[session_id] = agent_id

        # 同时更新 session_data 中的 session_id
        if agent_id in self._session_data:
            self._session_data[agent_id].session_id = session_id

        logger.info(f"📝注册会话映射: {agent_id} ↔ {session_id}")

    def get_session_id(self, agent_id: str) -> Optional[str]:
        """
        获取 agent_id 对应的 SDK session_id
        
        Args:
            agent_id: 前端 chat ID
            
        Returns:
            Optional[str]: SDK session ID，如果不存在则返回 None
        """
        return self._chat_sdk_map.get(agent_id, None)

    def get_agent_id(self, session_id: str) -> Optional[str]:
        """
        获取 SDK session_id 对应的 agent_id
        
        Args:
            session_id: SDK session ID
            
        Returns:
            Optional[str]: 前端 chat ID，如果不存在则返回 None
        """
        return self._sdk_chat_map.get(session_id)

    def remove_session(self, agent_id: str) -> None:
        """
        从内存中移除会话及其相关资源
        
        Args:
            agent_id: 前端会话ID
        """
        # 移除client
        if agent_id in self._sessions:
            del self._sessions[agent_id]
            logger.debug(f"🗑️已移除session client: {agent_id}")

        # 移除lock
        if agent_id in self._locks:
            del self._locks[agent_id]

        # 移除session data
        if agent_id in self._session_data:
            del self._session_data[agent_id]

        # 移除映射关系
        sdk_id = self._chat_sdk_map.get(agent_id)
        if sdk_id:
            del self._chat_sdk_map[agent_id]
            if sdk_id in self._sdk_chat_map:
                del self._sdk_chat_map[sdk_id]

        logger.info(f"✅已移除session: {agent_id}")


# Global instance
session_manager = SessionManager()
