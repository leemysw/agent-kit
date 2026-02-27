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

import json
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

    @staticmethod
    def _to_message_dict(message_obj: Any) -> Dict[str, Any]:
        """将消息对象转换为可序列化字典。"""
        if message_obj is None:
            return {}
        if isinstance(message_obj, dict):
            return dict(message_obj)
        if isinstance(message_obj, str):
            # 文本消息兜底包装，避免 asdict 对字符串报错
            return {"content": message_obj}
        return asdict(message_obj)

    @staticmethod
    def _coerce_payload_dict(message_type: str, payload: Any) -> Dict[str, Any]:
        """将数据库中的任意 payload 尽可能转换为字典。"""
        if isinstance(payload, dict):
            return dict(payload)

        if payload is None:
            return {}

        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            # 历史脏数据兜底
            if message_type in ("assistant", "user"):
                return {"content": payload}
            if message_type == "system":
                return {"subtype": "info", "data": {"raw": payload}}
            if message_type == "result":
                return {"subtype": "error", "result": payload, "is_error": True}
            return {}

        try:
            return SessionRepository._to_message_dict(payload)
        except Exception:
            return {}

    @staticmethod
    def _normalize_message_payload(message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """规范化历史消息结构，兼容旧脏数据。"""
        normalized = dict(payload or {})

        if message_type == "user":
            tool_use_result = normalized.get("tool_use_result")
            # 兼容历史脏数据：tool_use_result 被写成了字符串
            if isinstance(tool_use_result, str):
                normalized["tool_use_result"] = {"error": tool_use_result}
            elif tool_use_result is not None and not isinstance(tool_use_result, dict):
                normalized["tool_use_result"] = {"value": tool_use_result}
            return normalized

        if message_type == "assistant":
            # 某些历史数据缺 model，补默认值避免联合类型校验失败
            normalized.setdefault("model", "")
            return normalized

        if message_type == "system":
            normalized.setdefault("subtype", "info")
            normalized.setdefault("data", {})
            return normalized

        if message_type == "result":
            normalized.setdefault("subtype", "error" if normalized.get("is_error") else "success")
            normalized.setdefault("duration_ms", 0)
            normalized.setdefault("duration_api_ms", 0)
            normalized.setdefault("num_turns", 0)
            normalized.setdefault("session_id", "")
            normalized.setdefault("is_error", False)
            return normalized

        return normalized

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

    async def has_round_result(self, session_key: str, round_id: str) -> bool:
        """检查指定轮次是否已有 result 消息。"""
        try:
            async with db.session() as db_session:
                stmt = (
                    select(func.count(Message.message_id))
                    .where(
                        Message.session_key == session_key,
                        Message.round_id == round_id,
                        Message.message_type == "result",
                    )
                )
                result = await db_session.execute(stmt)
                count = result.scalar_one() or 0
                return count > 0
        except Exception as e:
            logger.error(f"❌ 检查轮次 result 失败: key={session_key}, round={round_id}, error={e}")
            return False

    # =====================================================
    # Message CRUD
    # =====================================================

    async def create_message(self, message: AMessage) -> bool:
        """保存消息（upsert）"""
        try:
            async with db.session() as db_session:
                existing = await db_session.get(Message, message.message_id)
                message_payload = self._normalize_message_payload(
                    message.message_type,
                    self._to_message_dict(message.message),
                )

                if existing:
                    existing.message = message_payload
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
                        message=message_payload,
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
                message_list: List[AMessage] = []
                for msg in messages:
                    try:
                        normalized_payload = self._normalize_message_payload(
                            msg.message_type,
                            self._coerce_payload_dict(msg.message_type, msg.message),
                        )
                        a_message = AMessage(
                            session_key=msg.session_key,
                            agent_id=msg.agent_id,
                            round_id=msg.round_id,
                            session_id=msg.session_id,
                            message_id=msg.message_id,
                            message=normalized_payload,
                            message_type=msg.message_type,
                            block_type=msg.block_type,
                            parent_id=msg.parent_id,
                            timestamp=msg.timestamp,
                        )
                        message_list.append(a_message)
                    except Exception as e:
                        logger.warning(f"⚠️ 跳过脏消息: id={msg.message_id}, type={msg.message_type}, error={e}")
                logger.info(f"📥 加载历史消息: key={session_key}, 共{len(message_list)}条")
                return message_list
        except Exception as e:
            logger.error(f"❌ 获取历史消息失败: {e}")
            return []


# 全局实例
session_repository = SessionRepository()
