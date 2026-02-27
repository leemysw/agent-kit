"""session_key 路由重构

Revision ID: 2a3b4c5d6e7f
Revises: ba05b8423844
Create Date: 2026-02-26 09:00:00.000000

Session 表: agent_id PK → session_key PK + channel_type/chat_type/status
Message 表: 新增 session_key/agent_id 字段
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = 'ba05b8423844'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """重建 Session 和 Message 表以适配 session_key 路由"""

    # =====================================================
    # SQLite 不支持 ALTER TABLE 改主键，需要重建表
    # =====================================================

    # --- 重建 sessions 表 ---
    op.rename_table("sessions", "_sessions_old")

    op.create_table(
        "sessions",
        sa.Column("session_key", sa.String(256), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False, server_default="main"),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("channel_type", sa.String(32), nullable=False, server_default="websocket"),
        sa.Column("chat_type", sa.String(16), nullable=False, server_default="dm"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("last_activity", sa.DateTime, nullable=True),
    )

    # 迁移旧数据: agent_id → session_key = "agent:main:ws:dm:{agent_id}"
    op.execute("""
        INSERT INTO sessions (session_key, agent_id, session_id, channel_type, chat_type, status, title, options, created_at, last_activity)
        SELECT 'agent:main:ws:dm:' || agent_id, 'main', session_id, 'websocket', 'dm', 'active', title, options, created_at, last_activity
        FROM _sessions_old
    """)

    op.drop_table("_sessions_old")

    # 创建索引
    op.create_index("ix_sessions_agent_id", "sessions", ["agent_id"])

    # --- 重建 messages 表 ---
    op.rename_table("messages", "_messages_old")

    op.create_table(
        "messages",
        sa.Column("message_id", sa.String(64), primary_key=True),
        sa.Column("parent_id", sa.String(64), nullable=True),
        sa.Column("session_key", sa.String(256), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False, server_default="main"),
        sa.Column("round_id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=True),
        sa.Column("message", sa.JSON, nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=True),
    )

    # 迁移旧数据
    op.execute("""
        INSERT INTO messages (message_id, parent_id, session_key, agent_id, round_id, session_id, message_type, block_type, message, timestamp)
        SELECT message_id, parent_id, 'agent:main:ws:dm:' || agent_id, 'main', round_id, session_id, message_type, block_type, message, timestamp
        FROM _messages_old
    """)

    op.drop_table("_messages_old")

    # 创建索引
    op.create_index("ix_messages_session_key", "messages", ["session_key"])
    op.create_index("ix_messages_agent_id", "messages", ["agent_id"])
    op.create_index("ix_messages_parent_id", "messages", ["parent_id"])
    op.create_index("ix_messages_round_id", "messages", ["round_id"])
    op.create_index("ix_messages_session_id", "messages", ["session_id"])


def downgrade() -> None:
    """回滚到 agent_id PK 结构"""

    # --- 回滚 sessions ---
    op.rename_table("sessions", "_sessions_new")

    op.create_table(
        "sessions",
        sa.Column("agent_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("last_activity", sa.DateTime, nullable=True),
    )

    # 从 session_key 提取 agent_id (去掉 "agent:main:ws:dm:" 前缀)
    op.execute("""
        INSERT INTO sessions (agent_id, session_id, title, options, created_at, last_activity)
        SELECT REPLACE(session_key, 'agent:main:ws:dm:', ''), session_id, title, options, created_at, last_activity
        FROM _sessions_new
        WHERE channel_type = 'websocket'
    """)

    op.drop_table("_sessions_new")

    # --- 回滚 messages ---
    op.rename_table("messages", "_messages_new")

    op.create_table(
        "messages",
        sa.Column("message_id", sa.String(64), primary_key=True),
        sa.Column("parent_id", sa.String(64), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("round_id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=True),
        sa.Column("message", sa.JSON, nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=True),
    )

    op.execute("""
        INSERT INTO messages (message_id, parent_id, agent_id, round_id, session_id, message_type, block_type, message, timestamp)
        SELECT message_id, parent_id, REPLACE(session_key, 'agent:main:ws:dm:', ''), round_id, session_id, message_type, block_type, message, timestamp
        FROM _messages_new
        WHERE agent_id = 'main'
    """)

    op.drop_table("_messages_new")

    op.create_index("ix_messages_parent_id", "messages", ["parent_id"])
    op.create_index("ix_messages_agent_id", "messages", ["agent_id"])
    op.create_index("ix_messages_round_id", "messages", ["round_id"])
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
