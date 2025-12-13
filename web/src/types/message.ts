/**
 * 消息类型定义
 *
 * 本文件定义前端使用的消息数据结构
 */

import { AgentId, SessionId, ToolInput, ToolOutput } from './sdk';

// ==================== 消息角色 ====================

/** 消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system' | 'result';

// ==================== 内容块类型 ====================

/** 文本内容块 */
export interface TextContent {
  type: 'text';
  text: string;
}

/** 工具使用内容块 */
export interface ToolUseContent {
  type: 'tool_use';
  id: string;
  name: string;
  input: ToolInput;
}

/** 工具结果内容块 */
export interface ToolResultContent {
  type: 'tool_result';
  tool_use_id: string;
  content: string | any[];
  is_error?: boolean;
}

/** 思考内容块 */
export interface ThinkingContent {
  type: 'thinking';
  thinking: string;
}

/** 内容块联合类型 */
export type ContentBlock =
  | TextContent
  | ToolUseContent
  | ToolResultContent
  | ThinkingContent;

// ==================== 消息类型 ====================

/** 基础消息接口 */
export interface BaseMessage {
  messageId: string;
  roundId: string;            // 轮次ID
  agentId: AgentId;           // 前端Chat ID
  sessionId?: SessionId;      // SDK Session ID (可选，由后端返回)
  ParentId?: string;          // 父消息ID (可选，由后端返回)
  role: MessageRole;
  timestamp: number;
}

/** 用户消息 */
export interface UserMessage extends BaseMessage {
  role: 'user';
  content: string;
  parentToolUseId?: string | null;
}

/** 助手消息 */
export interface AssistantMessage extends BaseMessage {
  role: 'assistant';
  content: ContentBlock[];
  stopReason?: 'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use';
  model?: string;
  parentToolUseId?: string | null;
  usage?: {
    inputTokens: number;
    outputTokens: number;
    cacheCreationTokens?: number;
    cacheReadTokens?: number;
  };
  isToolResult?: boolean;
}

/** 系统消息 */
export interface SystemMessage extends BaseMessage {
  role: 'system';
  content: string;
  metadata?: Record<string, any>;
}

/** 执行结果消息 */
export interface ResultMessage extends BaseMessage {
  role: 'result';
  subtype: 'success' | 'error';
  durationMs: number;
  durationApiMs: number;
  numTurns: number;
  totalCostUsd?: number;
  usage?: {
    inputTokens: number;
    outputTokens: number;
    cacheReadInputTokens?: number;
    cacheCreationInputTokens?: number;
    [key: string]: any;
  };
  result?: string;
  isError: boolean;
}

/** 消息联合类型 */
export type Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage;

// ==================== 工具调用类型 ====================

/** 工具调用状态 */
export type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

/** 工具调用记录 */
export interface ToolCall {
  id: string;
  toolName: string;
  input: ToolInput;
  output?: ToolOutput;
  status: ToolCallStatus;
  startTime: number;
  endTime?: number;
  error?: string;
  parentToolUseId?: string | null;
}

// ==================== 消息流事件 ====================

/** 流式消息事件类型 */
export type StreamEventType =
  | 'message_start'
  | 'content_block_start'
  | 'content_block_delta'
  | 'content_block_stop'
  | 'message_delta'
  | 'message_stop';

/** 流式消息事件 */
export interface StreamEvent {
  type: StreamEventType;
  index?: number;
  delta?: any;
  content_block?: ContentBlock;
  message?: Partial<AssistantMessage>;
  messageId?: string;
}

// ==================== 消息统计 ====================

/** 消息统计信息 */
export interface MessageStats {
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  systemMessages: number;
  totalTokens: number;
  totalCost: number;
  averageResponseTime: number;
}

// ==================== 消息过滤和搜索 ====================

/** 消息过滤选项 */
export interface MessageFilter {
  role?: MessageRole;
  startDate?: Date;
  endDate?: Date;
  searchText?: string;
  hasToolUse?: boolean;
}

/** 消息排序选项 */
export type MessageSortBy = 'timestamp' | 'role' | 'tokens';
export type MessageSortOrder = 'asc' | 'desc';

export interface MessageSort {
  by: MessageSortBy;
  order: MessageSortOrder;
}
