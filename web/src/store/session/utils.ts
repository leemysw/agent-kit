/**
 * Session Store 辅助函数
 */

import { AgentId, CreateSessionParams, Session } from '@/types';

import { ApiSession } from '@/types/session';

// ==================== ID生成 ====================

/** 生成新的Chat ID */
export const generateAgentId = (): AgentId => {
  return crypto.randomUUID();
};

// ==================== 默认值创建 ====================

/** 创建默认会话 */
export const createDefaultSession = (params?: CreateSessionParams): Session => {
  const now = Date.now();
  return {
    agentId: generateAgentId(),
    sessionId: null,
    title: params?.title || 'New Chat',
    options: params?.options || {},
    createdAt: now,
    lastActivityAt: now,
  };
};

// ==================== 数据转换 ====================

/**
 * 将服务器返回的session数据转换为前端Session格式
 * 注意：不包含agentId，由调用方处理以确保唯一性
 */
export const convertServerSession = (serverSession: ApiSession): Omit<Session, 'agentId'> => {
  return {
    sessionId: serverSession.session_id,
    title: serverSession.title || 'Untitled Chat',
    options: serverSession.options || {},
    createdAt: new Date(serverSession.created_at).getTime(),
    lastActivityAt: new Date(serverSession.last_activity).getTime(),
    isActive: serverSession.is_active,
    messageCount: serverSession.message_count,
  };
};
