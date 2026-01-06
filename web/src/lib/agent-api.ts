/**
 * Agent API 服务模块
 * 处理与 Agent 后端的通信
 *
 * [INPUT]: 依赖 @/types/session 的会话类型定义
 * [OUTPUT]: 对外提供 getSessions、createSession、updateSession、deleteSession 等 API 函数
 * [POS]: lib 模块的 API 层，负责驼峰→下划线命名转换（如 settingSources → setting_sources）
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

import { ApiSession, CreateSessionParams, Session, UpdateSessionParams } from '@/types/session';

const AGENT_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010/agent/v1';

// ==================== API 响应类型 ====================

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
}

// message_type: assistant, user, system, result, stream
// block_type: text、thinking、tool_result、tool_use
export interface Message {
  message_type: string;
  block_type?: string;
  message: Record<string, any>;
  timestamp: string;
  message_id: string;
  agent_id: string;
  session_id: string;
  parent_id: string;
}

// ==================== 类型转换函数 ====================

/** 将API响应转换为前端标准格式 */
export function transformApiSession(apiSession: ApiSession): Session {
  return {
    agentId: apiSession.agent_id,
    sessionId: apiSession.session_id,
    title: apiSession.title || '未命名会话',
    options: apiSession.options || {},
    createdAt: new Date(apiSession.created_at).getTime(),
    lastActivityAt: new Date(apiSession.last_activity).getTime(),
    isActive: apiSession.is_active,
    messageCount: apiSession.message_count,
  };
}

// ==================== 会话 API ====================

/**
 * 获取所有会话列表（返回标准化的Session数组）
 */
export const getSessions = async (): Promise<Session[]> => {
  const response = await fetch(`${AGENT_API_BASE_URL}/sessions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`获取会话列表失败: ${response.statusText}`);
  }

  const result: ApiResponse<ApiSession[]> = await response.json();
  return result.data.map(transformApiSession);
};

/**
 * 获取指定会话的所有消息
 */
export const getSessionMessages = async (agentId: string): Promise<Message[]> => {
  console.debug(`[getSessionMessages] 开始获取session ${agentId} 的消息`);
  const response = await fetch(`${AGENT_API_BASE_URL}/sessions/${agentId}/messages`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  console.debug(`[getSessionMessages] API响应状态: ${response.status} ${response.statusText}`);

  if (!response.ok) {
    console.error(`[getSessionMessages] API调用失败: ${response.status} ${response.statusText}`);
    throw new Error(`获取会话消息失败: ${response.statusText}`);
  }

  const result: ApiResponse<Message[]> = await response.json();
  return result.data;
};

/**
 * 删除会话
 */
export const deleteSession = async (agentId: string): Promise<{ success: boolean }> => {
  const response = await fetch(`${AGENT_API_BASE_URL}/sessions/${agentId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`删除会话失败: ${response.statusText}`);
  }

  const result: ApiResponse<{ success: boolean }> = await response.json();
  return result.data;
};

/**
 * 删除一轮对话（包含用户问题和所有回答）
 */
export const deleteRound = async (agentId: string, roundId: string): Promise<{ success: boolean; deleted_count: number }> => {
  const response = await fetch(`${AGENT_API_BASE_URL}/sessions/${agentId}/rounds/${roundId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`删除轮次失败: ${response.statusText}`);
  }

  const result: ApiResponse<{ success: boolean; deleted_count: number }> = await response.json();
  return result.data;
};

/**
 * 创建会话
 */
export const createSession = async (agentId: string, params: CreateSessionParams): Promise<Session> => {

  const options_obj = {
    allowed_tools: params.options?.allowedTools,
    system_prompt: params.options?.systemPrompt,
    model: params.options?.model,
    permission_mode: params.options?.permissionMode,
    max_turns: params.options?.maxTurns,
    disallowed_tools: params.options?.disallowedTools,
    cwd: params.options?.cwd,
    include_partial_messages: params.options?.includePartialMessages,
    // Skills 配置
    setting_sources: params.options?.settingSources,
  }

  const response = await fetch(`${AGENT_API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_id: agentId,
      title: params.title,
      options: options_obj,
    }),
  });

  if (!response.ok) {
    throw new Error(`创建会话失败: ${response.statusText}`);
  }

  const result: ApiResponse<ApiSession> = await response.json();
  return transformApiSession(result.data);
};

/**
 * 更新会话
 */
export const updateSession = async (agentId: string, params: UpdateSessionParams): Promise<Session> => {

  const options_obj = {
    allowed_tools: params.options?.allowedTools,
    system_prompt: params.options?.systemPrompt,
    model: params.options?.model,
    permission_mode: params.options?.permissionMode,
    max_turns: params.options?.maxTurns,
    disallowed_tools: params.options?.disallowedTools,
    cwd: params.options?.cwd,
    include_partial_messages: params.options?.includePartialMessages,
    // Skills 配置
    setting_sources: params.options?.settingSources,
  }

  const response = await fetch(`${AGENT_API_BASE_URL}/sessions/${agentId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: params.title,
      options: options_obj,
    }),
  });

  if (!response.ok) {
    throw new Error(`更新会话失败: ${response.statusText}`);
  }

  const result: ApiResponse<ApiSession> = await response.json();
  return transformApiSession(result.data);
};