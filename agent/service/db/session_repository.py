# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：session_repository
# @Date   ：2025/8/30 14:40
# @Author ：leemysw

# 2025/8/30 14:40   Create
# =====================================================

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update

from agent.service.db.models import Message, Session
from agent.service.schema.model_message import AMessage
from agent.service.schema.model_session import ASession
from agent.shared.database.async_sqlalchemy import db
from agent.utils.logger import logger



class SessionRepository:
    """会话数据仓库"""

    def __init__(self):
        pass

    async def create_session(
            self,
            agent_id: str,
            session_id: str,
            title: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        创建新会话

        Args:
            agent_id: 前端会话ID (主键)
            session_id: SDK内部会话ID
            title: 会话标题
            options: 会话配置

        Returns:
            bool: 是否成功创建
        """
        try:
            new_session = Session(
                agent_id=agent_id,
                session_id=session_id,
                title=title or 'New Chat',
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                options=options
            )

            async with db.session() as db_session:
                db_session.add(new_session)
                await db_session.commit()
                logger.info(f"✅ 创建会话记录: agent_id={agent_id}, session_id={new_session.session_id}")
                return True

        except Exception as e:
            logger.error(f"❌ 创建会话失败: {e}")
            return False

    async def update_session(
            self,
            agent_id: str,
            session_id: Optional[str] = None,
            title: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新会话信息

        Args:
            agent_id: 前端会话ID (主键)
            session_id: SDK会话ID
            title: 会话标题
            options: 会话配置

        Returns:
            bool: 是否成功更新
        """
        try:
            async with db.session() as db_session:
                # 构建更新数据
                update_data = {'last_activity': datetime.now(timezone.utc)}

                if session_id is not None:
                    update_data['session_id'] = session_id
                if title is not None:
                    update_data['title'] = title
                if options is not None:
                    update_data['options'] = options

                # 执行更新
                stmt = (
                    update(Session)
                    .where(Session.agent_id == agent_id)
                    .values(**update_data)
                )
                await db_session.execute(stmt)
                await db_session.commit()
                logger.info(f"🔄 更新会话记录: agent_id={agent_id}")
                return True
        except Exception as e:
            logger.error(f"❌ 更新会话失败: {e}")
            return False

    async def get_session(self, agent_id: str) -> Optional[ASession]:
        """
        获取会话信息

        Args:
            agent_id: 前端会话ID (主键)

        Returns:
            Optional[Dict]: 会话信息
        """
        try:
            async with db.session() as db_session:
                stmt = select(Session).where(Session.agent_id == agent_id)
                result = await db_session.execute(stmt)
                session_obj = result.scalar_one_or_none()

                if session_obj:
                    return ASession(
                        agent_id=session_obj.agent_id,
                        session_id=session_obj.session_id,
                        title=session_obj.title,
                        created_at=session_obj.created_at,
                        last_activity=session_obj.last_activity,
                        options=session_obj.options,
                        message_count=0
                    )
                return None
        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: {e}", exc_info=True)
            return None

    async def get_all_sessions(self) -> List[ASession]:
        """
        获取所有会话列表（按最后活动时间降序）

        Returns:
            List[Dict]: 会话列表
        """
        try:
            async with db.session() as db_session:
                # 使用联接查询获取消息数量
                stmt = (
                    select(
                        Session.agent_id,
                        Session.session_id,
                        Session.created_at,
                        Session.last_activity,
                        Session.title,
                        Session.options,
                        func.count(Message.message_id).label('message_count')
                    )
                    .outerjoin(Message, Session.session_id == Message.session_id)
                    .group_by(Session.agent_id, Session.session_id, Session.created_at, Session.last_activity,
                              Session.title)
                    .order_by(Session.last_activity.desc())
                )
                result = await db_session.execute(stmt)
                rows = result.fetchall()

                sessions = []
                for row in rows:
                    sessions.append(ASession(
                        agent_id=row.agent_id,
                        session_id=row.session_id,
                        title=row.title,
                        created_at=row.created_at,
                        last_activity=row.last_activity,
                        options=row.options,
                        message_count=row.message_count
                    ))

                logger.info(f"📋 获取会话列表: 共{len(sessions)}个会话")
                return sessions
        except Exception as e:
            logger.error(f"❌ 获取会话列表失败: {e}")
            return []

    async def delete_session(self, agent_id: str) -> bool:
        """
        删除会话及其所有消息

        Args:
            agent_id: SDK会话ID

        Returns:
            bool: 是否成功删除
        """
        try:
            async with db.session() as db_session:
                # 删除消息
                stmt_message = delete(Message).where(Message.agent_id == agent_id)
                await db_session.execute(stmt_message)

                # 删除会话
                stmt_session = delete(Session).where(Session.agent_id == agent_id)
                await db_session.execute(stmt_session)

                await db_session.commit()
                logger.info(f"🗑️ 删除会话: agent_id={agent_id}")
                return True
        except Exception as e:
            logger.error(f"❌ 删除会话失败: {e}")
            return False

    async def delete_round(self, agent_id: str, round_id: str) -> int:
        """
        删除一轮对话的所有消息（包含用户问题和所有回答）

        Args:
            agent_id: 会话ID
            round_id: 轮次ID

        Returns:
            int: 删除的消息数量，-1 表示失败
        """
        try:
            async with db.session() as db_session:
                # 删除指定 round_id 的所有消息
                stmt = (
                    delete(Message)
                    .where(Message.agent_id == agent_id)
                    .where(Message.round_id == round_id)
                )
                result = await db_session.execute(stmt)
                deleted_count = result.rowcount

                await db_session.commit()
                logger.info(f"🗑️ 删除轮次: agent_id={agent_id}, round_id={round_id}, 共{deleted_count}条消息")
                return deleted_count
        except Exception as e:
            logger.error(f"❌ 删除轮次失败: {e}")
            return -1

    async def create_message(self, message: AMessage) -> bool:
        """
        保存消息（支持 upsert：如果 message_id 已存在则更新）

        Args:
            message: 消息对象

        Returns:
            bool: 是否成功保存
        """
        try:
            async with db.session() as db_session:
                # 检查是否已存在相同 message_id 的记录
                existing = await db_session.get(Message, message.message_id)
                
                if existing:
                    # 更新现有记录（upsert）
                    existing.message = asdict(message.message)
                    existing.block_type = message.block_type
                    existing.timestamp = message.timestamp if message.timestamp else datetime.now(timezone.utc)
                    logger.debug(f"📝 更新消息: {message.message_id}")
                else:
                    # 插入新记录
                    new_message = Message(
                        message_id=message.message_id,
                        agent_id=message.agent_id,
                        round_id=message.round_id,
                        session_id=message.session_id,
                        message_type=message.message_type,
                        block_type=message.block_type,
                        message=asdict(message.message),
                        parent_id=message.parent_id,
                        timestamp=message.timestamp if message.timestamp else datetime.now(timezone.utc),
                    )
                    db_session.add(new_message)
                    logger.debug(f"💾 保存消息成功: {message.message_id}")

                # 更新会话最后活动时间
                await db_session.execute(
                    update(Session)
                    .where(Session.session_id == message.session_id)
                    .values(last_activity=datetime.now(timezone.utc))
                )

                await db_session.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}")
            return False

    async def get_session_messages(self, agent_id: str) -> List[AMessage]:
        """
        获取会话的所有历史消息

        Args:
            agent_id: SDK会话ID

        Returns:
            List[Dict]: 消息列表
        """
        try:
            async with db.session() as db_session:
                stmt = (
                    select(Message)
                    .where(Message.agent_id == agent_id)
                    .order_by(Message.timestamp.asc())
                )
                result = await db_session.execute(stmt)
                messages = result.scalars().all()

                message_list = []
                for msg in messages:
                    message_list.append(AMessage.model_validate(msg))

                logger.info(f"📥 加载历史消息: agent_id={agent_id}, 共{len(message_list)}条")
                return message_list
        except Exception as e:
            logger.error(f"❌ 获取历史消息失败: {e}")
            return []


# 全局实例
session_repository = SessionRepository()
