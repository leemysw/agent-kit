/**
 * 配置类型定义
 *
 * 本文件定义应用配置相关的数据结构
 */

import { AgentDefinition, HookEvent, McpServerConfig, PermissionMode, SettingSource } from './sdk';

// ==================== MCP配置 ====================

/** MCP服务器状态 */
export type MCPServerStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

/** MCP服务器信息 */
export interface MCPServerInfo {
  name: string;
  config: McpServerConfig;
  status: MCPServerStatus;
  tools: string[];
  resources: string[];
  error?: string;
  connectedAt?: number;
  lastActivityAt?: number;
}

/** MCP配置 */
export interface MCPConfig {
  servers: Record<string, McpServerConfig>;
  strictValidation: boolean;
  autoReconnect: boolean;
  reconnectInterval: number; // 毫秒
}

// ==================== Agent配置 ====================

/** Agent配置 */
export interface AgentConfig {
  agents: Record<string, AgentDefinition>;
  defaultAgent?: string;
  enableAutoSelection: boolean;
}

/** Skill配置 */
export interface SkillConfig {
  enabled: boolean;
  sources: SettingSource[];
  autoLoad: boolean;
  customSkillsPath?: string;
}

// ==================== 权限配置 ====================

/** 权限规则类型 */
export type PermissionRuleType = 'allow' | 'deny' | 'ask';

/** 权限规则 */
export interface PermissionRule {
  id: string;
  type: PermissionRuleType;
  toolName?: string;
  pattern?: string;
  description?: string;
  enabled: boolean;
}

/** 权限配置 */
export interface PermissionConfig {
  mode: PermissionMode;
  rules: PermissionRule[];
  enableInteractiveApproval: boolean;
  autoApproveReadOnly: boolean;
  logDenials: boolean;
}

// ==================== Hooks配置 ====================

/** Hook配置项 */
export interface HookConfig {
  id: string;
  event: HookEvent;
  matcher?: string;
  enabled: boolean;
  code: string;
  description?: string;
}

/** Hooks配置 */
export interface HooksConfig {
  hooks: HookConfig[];
  enabled: boolean;
}

// ==================== 插件配置 ====================

/** 插件信息 */
export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  description?: string;
  path: string;
  enabled: boolean;
  author?: string;
  homepage?: string;
}

/** 插件配置 */
export interface PluginConfig {
  plugins: PluginInfo[];
  autoLoad: boolean;
  customPluginsPath?: string;
}

// ==================== 模型配置 ====================

/** 模型提供商 */
export type ModelProvider = 'anthropic' | 'bedrock' | 'vertex';

/** 模型配置 */
export interface ModelConfig {
  provider: ModelProvider;
  defaultModel: string;
  availableModels: string[];
  apiKey?: string;
  apiEndpoint?: string;
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  topK?: number;
}

// ==================== 系统配置 ====================

/** 日志级别 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/** 系统配置 */
export interface SystemConfig {
  logLevel: LogLevel;
  enableTelemetry: boolean;
  enableCrashReporting: boolean;
  autoUpdate: boolean;
  dataDirectory?: string;
  cacheDirectory?: string;
}

// ==================== UI配置 ====================

/** 主题模式 */
export type ThemeMode = 'light' | 'dark' | 'auto';

/** 语言 */
export type Language = 'zh-CN' | 'en-US';

/** UI配置 */
export interface UIConfig {
  theme: ThemeMode;
  language: Language;
  fontSize: number;
  fontFamily: string;
  compactMode: boolean;
  showLineNumbers: boolean;
  enableAnimations: boolean;
  sidebarWidth: number;
  messageMaxWidth: number;
}

// ==================== 应用配置 ====================

/** 应用完整配置 */
export interface AppConfig {
  version: string;
  mcp: MCPConfig;
  agent: AgentConfig;
  skill: SkillConfig;
  permission: PermissionConfig;
  hooks: HooksConfig;
  plugin: PluginConfig;
  model: ModelConfig;
  system: SystemConfig;
  ui: UIConfig;
}

/** 配置更新事件 */
export interface ConfigUpdateEvent {
  section: keyof AppConfig;
  oldValue: any;
  newValue: any;
  timestamp: number;
}

// ==================== 配置导入导出 ====================

/** 配置导出选项 */
export interface ConfigExportOptions {
  includeSensitive?: boolean; // 是否包含API密钥等敏感信息
  sections?: (keyof AppConfig)[]; // 要导出的配置部分
  format?: 'json' | 'yaml';
}

/** 配置导入选项 */
export interface ConfigImportOptions {
  merge?: boolean; // 是否合并现有配置
  validate?: boolean; // 是否验证配置
  backup?: boolean; // 是否备份现有配置
}
