# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：session_repository
# @Date   ：2025/8/30 14:40
# @Author ：leemysw
#
# 2025/8/30 14:40   Create
# 2026/2/25          重构：session_key 路由
# =====================================================

"""
会话数据仓库

[INPUT]: 依赖 sqlalchemy，依赖 db/models 的 Session/Message
[OUTPUT]: 对外提供 SessionRepository（会话 CRUD + 消息 CRUD）
[POS]: db 模块的数据访问层，被 session_store 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

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

    # =====================================================
    # Session CRUD — 以 session_key 为主键
    # =====================================================

    async def create_session(
            self,
            session_key: str,
            channel_type: str = "websocket",
            chat_type: str = "dm",
            agent_id: str = "main",
            session_id: Optional[str] = None,
            title: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """创建新会话"""
        try:
            new_session = Session(
                session_key=session_key,
                agent_id=agent_id,
                session_id=session_id,
                channel_type=channel_type,
                chat_type=chat_type,
                title=title or "New Chat",
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                options=options,
            )

            async with db.session() as db_session:
                db_session.add(new_session)
                await db_session.commit()
                logger.info(f"✅ 创建会话: key={session_key}")
                return True

        except Exception as e:
            logger.error(f"❌ 创建会话失败: {e}")
            return False

    async def get_session(self, session_key: str) -> Optional[ASession]:
        """按 session_key 获取会话"""
        try:
            async with db.session() as db_session:
                stmt = select(Session).where(Session.session_key == session_key)
                result = await db_session.execute(stmt)
                session_obj = result.scalar_one_or_none()

                if session_obj:
                    return ASession(
                        session_key=session_obj.session_key,
                        agent_id=session_obj.agent_id,
                        session_id=session_obj.session_id,
                        channel_type=session_obj.channel_type,
                        chat_type=session_obj.chat_type,
                        status=session_obj.status,
                        title=session_obj.title,
                        created_at=session_obj.created_at,
                        last_activity=session_obj.last_activity,
                        options=session_obj.options,
                        message_count=0,
                    )
                return None
        except Exception as e:
            logger.error(f"❌ 获取会话失败: {e}", exc_info=True)
            return None

    async def update_session(
            self,
            session_key: str,
            session_id: Optional[str] = None,
            title: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
            status: Optional[str] = None,
    ) -> bool:
        """更新会话信息"""
        try:
            async with db.session() as db_session:
                update_data: Dict[str, Any] = {}
                if session_id is not None:
                    update_data["session_id"] = session_id
                if title is not None:
                    update_data["title"] = title
                if options is not None:
                    update_data["options"] = options
                if status is not None:
                    update_data["status"] = status
                update_data["last_activity"] = datetime.now(timezone.utc)

                stmt = (
                    update(Session)
                    .where(Session.session_key == session_key)
                    .values(**update_data)
                )
                await db_session.execute(stmt)
                await db_session.commit()
                logger.info(f"🔄 更新会话: key={session_key}")
                return True
        except Exception as e:
            logger.error(f"❌ 更新会话失败: {e}")
            return False

    async def get_all_sessions(self) -> List[ASession]:
        """获取所有会话（按最后活动时间降序）"""
        try:
            async with db.session() as db_session:
                stmt = (
                    select(
                        Session.session_key,
                        Session.agent_id,
                        Session.session_id,
                        Session.channel_type,
                        Session.chat_type,
                        Session.status,
                        Session.created_at,
                        Session.last_activity,
                        Session.title,
                        Session.options,
                        func.count(Message.message_id).label("message_count"),
                    )
                    .outerjoin(Message, Session.session_key == Message.session_key)
                    .group_by(
                        Session.session_key, Session.agent_id, Session.session_id,
                        Session.channel_type, Session.chat_type, Session.status,
                        Session.created_at, Session.last_activity, Session.title, Session.options,
                    )
                    .order_by(Session.last_activity.desc())
                )
                result = await db_session.execute(stmt)
                rows = result.fetchall()

                sessions = []
                for row in rows:
                    sessions.append(ASession(
                        session_key=row.session_key,
                        agent_id=row.agent_id,
                        session_id=row.session_id,
                        channel_type=row.channel_type,
                        chat_type=row.chat_type,
                        status=row.status,
                        title=row.title,
                        created_at=row.created_at,
                        last_activity=row.last_activity,
                        options=row.options,
                        message_count=row.message_count,
                    ))

                logger.info(f"📋 获取会话列表: 共{len(sessions)}个")
                return sessions
        except Exception as e:
            logger.error(f"❌ 获取会话列表失败: {e}")
            return []

    async def delete_session(self, session_key: str) -> bool:
        """删除会话及其所有消息"""
        try:
            async with db.session() as db_session:
                stmt_message = delete(Message).where(Message.session_key == session_key)
                await db_session.execute(stmt_message)

                stmt_session = delete(Session).where(Session.session_key == session_key)
                await db_session.execute(stmt_session)

                await db_session.commit()
                logger.info(f"🗑️ 删除会话: key={session_key}")
                return True
        except Exception as e:
            logger.error(f"❌ 删除会话失败: {e}")
            return False

    async def delete_round(self, session_key: str, round_id: str) -> int:
        """删除一轮对话"""
        try:
            async with db.session() as db_session:
                stmt = (
                    delete(Message)
                    .where(Message.session_key == session_key)
                    .where(Message.round_id == round_id)
                )
                result = await db_session.execute(stmt)
                deleted_count = result.rowcount

                await db_session.commit()
                logger.info(f"🗑️ 删除轮次: key={session_key}, round={round_id}, 共{deleted_count}条")
                return deleted_count
        except Exception as e:
            logger.error(f"❌ 删除轮次失败: {e}")
            return -1

    async def get_latest_round_id(self, session_key: str) -> Optional[str]:
        """获取最新 round_id"""
        try:
            async with db.session() as db_session:
                stmt = (
                    select(Message.round_id)
                    .where(Message.session_key == session_key)
                    .order_by(Message.timestamp.desc())
                    .limit(1)
                )
                result = await db_session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ 获取最新 round_id 失败: {e}")
            return None

    # =====================================================
    # Message CRUD
    # =====================================================

    async def create_message(self, message: AMessage) -> bool:
        """保存消息（upsert）"""
        try:
            async with db.session() as db_session:
                existing = await db_session.get(Message, message.message_id)

                if existing:
                    existing.message = asdict(message.message)
                    existing.block_type = message.block_type
                    existing.timestamp = message.timestamp or datetime.now(timezone.utc)
                    logger.debug(f"📝 更新消息: {message.message_id}")
                else:
                    new_message = Message(
                        message_id=message.message_id,
                        session_key=message.session_key,
                        agent_id=message.agent_id,
                        round_id=message.round_id,
                        session_id=message.session_id,
                        message_type=message.message_type,
                        block_type=message.block_type,
                        message=asdict(message.message),
                        parent_id=message.parent_id,
                        timestamp=message.timestamp or datetime.now(timezone.utc),
                    )
                    db_session.add(new_message)
                    logger.debug(f"💾 保存消息: {message.message_id}")

                # 更新会话最后活动时间
                await db_session.execute(
                    update(Session)
                    .where(Session.session_key == message.session_key)
                    .values(last_activity=datetime.now(timezone.utc))
                )

                await db_session.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}")
            return False

    async def get_session_messages(self, session_key: str) -> List[AMessage]:
        """获取会话的所有历史消息"""
        try:
            async with db.session() as db_session:
                stmt = (
                    select(Message)
                    .where(Message.session_key == session_key)
                    .order_by(Message.timestamp.asc())
                )
                result = await db_session.execute(stmt)
                messages = result.scalars().all()

                message_list = [AMessage.model_validate(msg) for msg in messages]
                logger.info(f"📥 加载历史消息: key={session_key}, 共{len(message_list)}条")
                return message_list
        except Exception as e:
            logger.error(f"❌ 获取历史消息失败: {e}")
            return []


# 全局实例
session_repository = SessionRepository()
