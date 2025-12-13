/**
 * Claude Agent SDK 类型定义
 *
 * 本文件包含所有与Claude Agent SDK相关的TypeScript类型定义
 * 参考: @anthropic-ai/claude-agent-sdk
 */

// ==================== 基础类型 ====================

/** UUID类型 */
export type UUID = string;

/** 前端Chat ID类型 - 用于标识前端对话 */
export type AgentId = string;

/** SDK Session ID类型 - Claude SDK生成的session标识 */
export type SessionId = string;

/** 工具输入参数类型 */
export type ToolInput = Record<string, any>;

/** 工具输出结果类型 */
export type ToolOutput = Record<string, any>;

// ==================== 权限相关类型 ====================

/** 权限模式 */
export type PermissionMode =
  | 'default'           // 标准权限行为
  | 'acceptEdits'       // 自动接受文件编辑
  | 'bypassPermissions' // 绕过所有权限检查
  | 'plan';             // 计划模式 - 不执行

/** 权限结果 */
export type PermissionResult =
  | {
  behavior: 'allow';
  updatedInput: ToolInput;
  updatedPermissions?: PermissionUpdate[];
}
  | {
  behavior: 'deny';
  message: string;
  interrupt?: boolean;
};

/** 权限更新 */
export interface PermissionUpdate {
  type: 'allow' | 'deny' | 'ask';
  toolName?: string;
  pattern?: string;
}

/** canUseTool回调函数类型 */
export type CanUseTool = (
  toolName: string,
  input: ToolInput,
  options: {
    signal: AbortSignal;
    suggestions?: PermissionUpdate[];
  }
) => Promise<PermissionResult>;

// ==================== 消息类型 ====================

/** SDK消息基础类型 */
export interface BaseSDKMessage {
  uuid: UUID;
  session_id: SessionId;
}

/** 系统初始化消息 */
export interface SDKSystemMessage extends BaseSDKMessage {
  type: 'system';
  subtype: 'init';
  apiKeySource: string;
  cwd: string;
  tools: string[];
  mcp_servers: {
    name: string;
    status: string;
  }[];
  model: string;
  permissionMode: PermissionMode;
  slash_commands: string[];
  output_style: string;
}

/** 用户消息 */
export interface SDKUserMessage extends BaseSDKMessage {
  type: 'user';
  message: {
    role: 'user';
    content: string | any[];
  };
  parent_tool_use_id: string | null;
}

/** 助手消息 */
export interface SDKAssistantMessage extends BaseSDKMessage {
  type: 'assistant';
  message: {
    role: 'assistant';
    content: any[];
    stop_reason?: string;
    stop_sequence?: string | null;
  };
  parent_tool_use_id: string | null;
}

/** 结果消息 - 成功 */
export interface SDKResultSuccessMessage extends BaseSDKMessage {
  type: 'result';
  subtype: 'success';
  duration_ms: number;
  duration_api_ms: number;
  is_error: boolean;
  num_turns: number;
  result: string;
  total_cost_usd: number;
  usage: {
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens?: number;
    cache_read_input_tokens?: number;
  };
  permission_denials: {
    tool_name: string;
    tool_use_id: string;
    tool_input: ToolInput;
  }[];
}

/** 结果消息 - 错误 */
export interface SDKResultErrorMessage extends BaseSDKMessage {
  type: 'result';
  subtype: 'error_max_turns' | 'error_during_execution';
  duration_ms: number;
  duration_api_ms: number;
  is_error: boolean;
  num_turns: number;
  total_cost_usd: number;
  usage: {
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens?: number;
    cache_read_input_tokens?: number;
  };
  permission_denials: any[];
}

/** 流式事件消息 */
export interface SDKPartialAssistantMessage extends BaseSDKMessage {
  type: 'stream_event';
  event: any; // RawMessageStreamEvent from Anthropic SDK
  parent_tool_use_id: string | null;
}

/** 压缩边界消息 */
export interface SDKCompactBoundaryMessage extends BaseSDKMessage {
  type: 'system';
  subtype: 'compact_boundary';
  compact_metadata: {
    trigger: 'manual' | 'auto';
    pre_tokens: number;
  };
}

/** SDK消息联合类型 */
export type SDKMessage =
  | SDKSystemMessage
  | SDKUserMessage
  | SDKAssistantMessage
  | SDKResultSuccessMessage
  | SDKResultErrorMessage
  | SDKPartialAssistantMessage
  | SDKCompactBoundaryMessage;

// ==================== Agent配置类型 ====================

/** Subagent定义 */
export interface AgentDefinition {
  description: string;
  tools?: string[];
  prompt: string;
  model?: 'sonnet' | 'opus' | 'haiku' | 'inherit';
}

/** 设置来源 */
export type SettingSource = 'user' | 'project' | 'local';

// ==================== MCP相关类型 ====================

/** MCP服务器配置 - stdio */
export interface McpStdioServerConfig {
  type?: 'stdio';
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

/** MCP服务器配置 - SSE */
export interface McpSSEServerConfig {
  type: 'sse';
  url: string;
  headers?: Record<string, string>;
}

/** MCP服务器配置 - HTTP */
export interface McpHttpServerConfig {
  type: 'http';
  url: string;
  headers?: Record<string, string>;
}

/** MCP服务器配置 - SDK */
export interface McpSdkServerConfig {
  type: 'sdk';
  name: string;
  instance: any; // McpServer instance
}

/** MCP服务器配置联合类型 */
export type McpServerConfig =
  | McpStdioServerConfig
  | McpSSEServerConfig
  | McpHttpServerConfig
  | McpSdkServerConfig;

// ==================== Hooks相关类型 ====================

/** Hook事件类型 */
export type HookEvent =
  | 'PreToolUse'
  | 'PostToolUse'
  | 'Notification'
  | 'UserPromptSubmit'
  | 'SessionStart'
  | 'SessionEnd'
  | 'Stop'
  | 'SubagentStop'
  | 'PreCompact';


/** Hook回调函数类型 */
export type HookCallback = (
  input: any,
  toolUseID: string | undefined,
  options: { signal: AbortSignal }
) => Promise<any>;

/** Hook配置 */
export interface HookCallbackMatcher {
  matcher?: string;
  hooks: HookCallback[];
}

