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