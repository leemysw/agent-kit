/**
 * Session Store 辅助函数
 */

import { AgentId, CreateSessionParams, Session } from '@/types';

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
