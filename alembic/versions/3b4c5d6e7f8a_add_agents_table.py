"""新增 agents 表

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-03-04 15:09:00.000000

新增 agents 表，存储 Agent 配置和 workspace 信息。
sessions 表已有 agent_id 字段（默认 "main"），无需修改。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8a'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 agents 表 + 插入默认 Agent"""

    # 1. 创建 agents 表
    op.create_table(
        "agents",
        sa.Column("agent_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("workspace_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # 2. 插入默认 "main" Agent（兼容现有 sessions 的 agent_id="main"）
    op.execute("""
        INSERT INTO agents (agent_id, name, workspace_path, status, created_at)
        VALUES ('main', '主助手', '', 'active', datetime('now'))
    """)


def downgrade() -> None:
    """删除 agents 表"""
    op.drop_table("agents")
