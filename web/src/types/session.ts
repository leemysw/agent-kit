/**
 * 会话类型定义
 *
 * 统一的会话数据结构，避免重复定义
 */

// ==================== 会话配置 ====================

import { AgentId, SessionId } from "@/types/sdk";

/** 会话配置选项 */
export interface SessionOptions {
  model?: string;
  permissionMode?: string;
  allowedTools?: string[];
  disallowedTools?: string[];
  systemPrompt?: string;
  maxTurns?: number;
  maxThinkingTokens?: number;
  cwd?: string;
  // 流式输出
  includePartialMessages?: boolean;

}

// ==================== 会话数据结构 ====================

/** 标准化的会话数据结构 */
export interface Session {
  /** 客户端会话ID */
  agentId: AgentId;
  /** SDK会话ID（可选） */
  sessionId: SessionId | null;
  /** 会话标题 */
  title: string;
  /** 会话配置选项 */
  options: SessionOptions;
  /** 创建时间（时间戳） */
  createdAt: number;
  /** 最后活动时间（时间戳） */
  lastActivityAt: number;
  /** 是否活跃 */
  isActive?: boolean;
  /** 消息数量 */
  messageCount?: number;
}

// ==================== API 相关类型 ====================

/** API响应中的会话数据（后端格式） */
export interface ApiSession {
  agent_id: string;
  session_id: string | null;
  created_at: string;
  last_activity: string;
  is_active: boolean;
  title: string | null;
  message_count: number;
  options: Record<string, any> | null;
}

// ==================== 操作参数类型 ====================

/** 创建会话参数 */
export interface CreateSessionParams {
  title?: string;
  options?: Partial<SessionOptions>;
}

/** 更新会话参数 */
export interface UpdateSessionParams {
  title?: string;
  options?: Partial<SessionOptions>;
}
