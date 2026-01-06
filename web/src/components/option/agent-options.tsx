// !/usr/bin/env python
// -*- coding: utf-8 -*-
// =====================================================
// @File   :session-options-dialog.tsx
// @Date   :2025-12-01 22:56
// @Author :leemysw
// 2025-12-01 22:56   Create
// =====================================================

/**
 * Session Options Dialog Component
 *
 * 用于创建和编辑会话配置的对话框组件，支持多标签页配置界面
 */

"use client";

import { useState } from "react";
import { MessageSquare, Settings, Sparkles, Wrench, X, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { SessionOptions } from "@/types/session";

// ==================== 类型定义 ====================

interface AgentOptionsProps {
  /** 对话框模式：create 或 edit */
  mode: 'create' | 'edit';
  /** 是否打开对话框 */
  isOpen: boolean;
  /** 关闭对话框回调 */
  onClose: () => void;
  /** 保存配置回调 */
  onSave: (title: string, options: SessionOptions) => void;
  /** 初始标题（编辑模式） */
  initialTitle?: string;
  /** 初始配置（编辑模式） */
  initialOptions?: Partial<SessionOptions>;
}

type TabKey = 'basic' | 'prompt' | 'tools' | 'skills' | 'advanced';

// 预定义的模型列表
const AVAILABLE_MODELS = [
  {value: 'deepseek-chat', label: 'DeepSeek Chat | 深度求索'},
  {value: 'glm-4.7', label: 'GLM 4.6'},
  {value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet'},
  {value: 'claude-3-opus', label: 'Claude 3 Opus'},
  {value: 'claude-3-haiku', label: 'Claude 3 Haiku'},
];

// 权限模式选项
const PERMISSION_MODES = [
  {value: 'default', label: '默认（继续前询问）', description: '只读工具会自动预先授权，其它操作仍需权限。'},
  {value: 'planning', label: '规划模式', description: '继承默认的只读工具集，并会在执行行为前呈现计划。'},
  {value: 'auto_edit', label: '自动授权文件编辑', description: '默认的只读工具会自动预先授权，但执行仍被禁用。'},
  {value: 'skip_all', label: '跳过所有权限检查', description: '所有工具都会在无审批情况下执行。'},
] as const;

// 常用工具列表（硬编码，后续可从API获取）
const AVAILABLE_TOOLS = [
  {name: 'Bash', description: 'Executes shell commands in your environment'},
  {name: 'Write', description: 'Creates or overwrites files'},
  {name: 'WebSearch', description: 'Performs web searches with domain filtering'},
  {name: 'Edit', description: 'Edits files'},
  {name: 'Read', description: 'Reads files'},
  {name: 'List', description: 'Lists directory contents'},
];

// ==================== 主组件 ====================

export function AgentOptions(
  {
    mode,
    isOpen,
    onClose,
    onSave,
    initialTitle = '',
    initialOptions = {},
  }: AgentOptionsProps) {
  // 状态管理
  const [activeTab, setActiveTab] = useState<TabKey>('basic');
  const [title, setTitle] = useState(initialTitle || 'Agent');
  const [model, setModel] = useState(initialOptions.model || 'deepseek-chat');
  const [permissionMode, setPermissionMode] = useState(initialOptions.permissionMode || 'default');
  const [allowedTools, setAllowedTools] = useState<string[]>(initialOptions.allowedTools || []);
  const [disallowedTools, setDisallowedTools] = useState<string[]>(initialOptions.disallowedTools || []);
  const [systemPrompt, setSystemPrompt] = useState(initialOptions.systemPrompt || '');
  const [maxTurns, setMaxTurns] = useState(initialOptions.maxTurns?.toString() || '');
  const [includePartialMessages, setIncludePartialMessages] = useState(initialOptions.includePartialMessages ?? true);
  // 工作目录状态
  const [workingDirectory, setWorkingDirectory] = useState(initialOptions.cwd || '～/.agent');
  // 技能配置状态
  const [skillsEnabled, setSkillsEnabled] = useState(initialOptions.skillsEnabled ?? false);
  const [settingSources, setSettingSources] = useState<('user' | 'project')[]>(
    initialOptions.settingSources || ['user', 'project']
  );

  // 切换技能来源
  const toggleSettingSource = (source: 'user' | 'project') => {
    setSettingSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  // 标签页配置
  const tabs = [
    {key: 'basic' as TabKey, label: '基础设置', icon: Settings},
    {key: 'prompt' as TabKey, label: '提示词设置', icon: MessageSquare},
    {key: 'tools' as TabKey, label: '工具与权限', icon: Wrench},
    {key: 'skills' as TabKey, label: 'SKILLS 配置', icon: Sparkles},
    {key: 'advanced' as TabKey, label: '高级设置', icon: Zap},
  ];

  // 处理工具选择
  const toggleTool = (toolName: string, type: 'allowed' | 'disallowed') => {
    if (type === 'allowed') {
      setAllowedTools(prev =>
        prev.includes(toolName)
          ? prev.filter(t => t !== toolName)
          : [...prev, toolName]
      );
    } else {
      setDisallowedTools(prev =>
        prev.includes(toolName)
          ? prev.filter(t => t !== toolName)
          : [...prev, toolName]
      );
    }
  };

  // 处理保存
  const handleSave = () => {
    // 如果启用技能，自动添加 "Skill" 到 allowedTools
    let finalAllowedTools = [...allowedTools];
    if (skillsEnabled && !finalAllowedTools.includes('Skill')) {
      finalAllowedTools.push('Skill');
    }

    const options: SessionOptions = {
      model,
      permissionMode,
      allowedTools: finalAllowedTools,
      disallowedTools,
      systemPrompt: systemPrompt || undefined,
      maxTurns: maxTurns ? parseInt(maxTurns) : undefined,
      cwd: workingDirectory || undefined,
      includePartialMessages,
      // Skills 配置
      skillsEnabled,
      settingSources: skillsEnabled ? settingSources : undefined,
    };
    onSave(title, options);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="bg-background border border-border w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl rounded-xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Settings className="w-4 h-4"/>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground tracking-tight">
                {mode === 'create' ? '创建新会话' : '会话设置'}
              </h2>
              <p className="text-xs text-muted-foreground">
                {mode === 'create' ? '配置您的 AI 助手环境与能力' : `正在编辑: ${title}`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5"/>
          </button>
        </div>

        {/* 主体：左侧标签 + 右侧内容 */}
        <div className="flex flex-1 overflow-hidden">
          {/* 左侧标签页 */}
          <div className="w-56 bg-muted/10 border-r border-border flex flex-col p-3 gap-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 text-sm rounded-lg transition-all duration-200",
                    isActive
                      ? "bg-primary/10 text-primary font-medium shadow-sm"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <Icon className={cn("w-4 h-4", isActive ? "text-primary" : "opacity-70")}/>
                  <span>{tab.label}</span>
                  {isActive && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary"/>
                  )}
                </button>
              );
            })}
          </div>

          {/* 右侧内容区 */}
          <div className="flex-1 overflow-y-auto p-8 bg-background">
            {/* 基础设置 */}
            {activeTab === 'basic' && (
              <div className="space-y-8 max-w-2xl animate-in slide-in-from-right-4 duration-300">
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">基本信息</h3>

                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      会话名称 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all"
                      placeholder="给这个任务起个名字..."
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">
                      模型选择 <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <select
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none transition-all"
                      >
                        {AVAILABLE_MODELS.map(m => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                      <div
                        className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
                        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
                                strokeLinejoin="round"/>
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">环境配置</h3>

                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">工作目录</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={workingDirectory}
                        onChange={(e) => setWorkingDirectory(e.target.value)}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono transition-all"
                        placeholder="/path/to/project"
                      />
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Agent 将在此目录下执行文件操作和命令。
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">描述</label>
                    <textarea
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y transition-all"
                      rows={3}
                      placeholder="描述此会话的目标或背景信息..."
                    />
                  </div>
                </div>
              </div>
            )}

            {/* 提示词设置 */}
            {activeTab === 'prompt' && (
              <div className="space-y-6 h-full flex flex-col animate-in slide-in-from-right-4 duration-300">
                <div className="flex flex-col h-full space-y-2">
                  <label className="text-sm font-medium leading-none flex items-center justify-between">
                    <span>系统提示词 (System Prompt)</span>
                    <span className="text-xs font-normal text-muted-foreground">支持 Markdown</span>
                  </label>
                  <div className="flex-1 relative">
                    <textarea
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                      className="absolute inset-0 w-full h-full rounded-md border border-input bg-background px-4 py-3 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none leading-relaxed"
                      placeholder="在此输入自定义系统提示词，它将决定 Agent 的行为模式、角色设定和限制条件..."
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    💡 提示：自定义系统提示词将覆盖默认的 Agent 设定。
                  </p>
                </div>
              </div>
            )}

            {/* 工具与权限 */}
            {activeTab === 'tools' && (
              <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                {/* 权限模式 */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">权限控制</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {PERMISSION_MODES.map(pm => (
                      <button
                        key={pm.value}
                        onClick={() => setPermissionMode(pm.value)}
                        className={cn(
                          "relative p-4 border rounded-xl text-left transition-all duration-200 hover:shadow-md",
                          permissionMode === pm.value
                            ? "bg-primary/5 border-primary ring-1 ring-primary"
                            : "bg-card border-border hover:border-primary/50"
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-sm">{pm.label}</span>
                          {permissionMode === pm.value && (
                            <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                              <svg width="10" height="8" viewBox="0 0 10 8" fill="none"
                                   xmlns="http://www.w3.org/2000/svg">
                                <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round"
                                      strokeLinejoin="round"/>
                              </svg>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{pm.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 预先授权工具 */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">工具授权</h3>
                    <span className="text-xs text-muted-foreground">
                      已启用 {allowedTools.length} 个工具
                    </span>
                  </div>

                  <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 flex gap-3">
                    <div className="text-orange-600 mt-0.5">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                           strokeLinecap="round" strokeLinejoin="round">
                        <path
                          d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-orange-700">安全提示</p>
                      <p className="text-xs text-orange-600/90 mt-1 leading-relaxed">
                        被选中的工具将被"预先授权"，Agent 调用这些工具时将不会请求您的确认。请仅为您完全信任的工具开启此选项。
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {AVAILABLE_TOOLS.map(tool => {
                      const isChecked = allowedTools.includes(tool.name);
                      return (
                        <div
                          key={tool.name}
                          className={cn(
                            "flex items-center justify-between p-4 border rounded-lg transition-all duration-200",
                            isChecked
                              ? "bg-primary/5 border-primary/30"
                              : "bg-card border-border hover:border-primary/20"
                          )}
                        >
                          <div className="flex-1 mr-4">
                            <div className="font-medium text-sm flex items-center gap-2">
                              {tool.name}
                              {isChecked && <span
                                className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">已授权</span>}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">{tool.description}</div>
                          </div>

                          {/* 自定义 Switch 样式 */}
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => toggleTool(tool.name, 'allowed')}
                              className="sr-only peer"
                            />
                            <div
                              className="w-11 h-6 bg-muted rounded-full peer peer-focus:ring-2 peer-focus:ring-primary/20 dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                          </label>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* 技能配置 */}
            {activeTab === 'skills' && (
              <div className="space-y-8 max-w-2xl animate-in slide-in-from-right-4 duration-300">
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Agent Skills</h3>

                  {/* 技能启用开关 */}
                  <div
                    className="flex items-center justify-between p-4 border rounded-lg bg-card hover:border-primary/20 transition-all">
                    <div className="flex-1">
                      <label className="text-sm font-medium leading-none flex items-center gap-2">
                        启用技能系统
                        {skillsEnabled && <span
                          className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-600 rounded font-medium">已启用</span>}
                      </label>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        技能是可重用的专业能力模块，Claude 会根据任务上下文自动调用相关技能。
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer ml-4">
                      <input
                        type="checkbox"
                        checked={skillsEnabled}
                        onChange={(e) => setSkillsEnabled(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div
                        className="w-11 h-6 bg-muted rounded-full peer peer-focus:ring-2 peer-focus:ring-primary/20 dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                    </label>
                  </div>
                </div>

                {/* 技能来源选择 */}
                {skillsEnabled && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">技能加载来源</h3>

                    <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 flex gap-3">
                      <div className="text-orange-600 mt-0.5">
                        <Sparkles className="w-4 h-4"/>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-orange-700">关于技能来源</p>
                        <p className="text-xs text-orange-600/90 mt-1 leading-relaxed">
                          技能从 SKILL.md 文件中加载。用户技能保存在 ~/.claude/skills/，项目技能保存在工作目录下的
                          .claude/skills/。
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-3">
                      {/* 用户技能 */}
                      <div
                        className={cn(
                          "flex items-center justify-between p-4 border rounded-lg transition-all duration-200",
                          settingSources.includes('user')
                            ? "bg-primary/5 border-primary/30"
                            : "bg-card border-border hover:border-primary/20"
                        )}
                      >
                        <div className="flex-1 mr-4">
                          <div className="font-medium text-sm flex items-center gap-2">
                            用户技能
                            {settingSources.includes('user') && <span
                              className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">已启用</span>}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            从 ~/.claude/skills/ 加载个人技能，跨所有项目可用
                          </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={settingSources.includes('user')}
                            onChange={() => toggleSettingSource('user')}
                            className="sr-only peer"
                          />
                          <div
                            className="w-11 h-6 bg-muted rounded-full peer peer-focus:ring-2 peer-focus:ring-primary/20 dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                      </div>

                      {/* 项目技能 */}
                      <div
                        className={cn(
                          "flex items-center justify-between p-4 border rounded-lg transition-all duration-200",
                          settingSources.includes('project')
                            ? "bg-primary/5 border-primary/30"
                            : "bg-card border-border hover:border-primary/20"
                        )}
                      >
                        <div className="flex-1 mr-4">
                          <div className="font-medium text-sm flex items-center gap-2">
                            项目技能
                            {settingSources.includes('project') && <span
                              className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">已启用</span>}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            从 .claude/skills/ 加载工作目录下的项目技能，可通过 Git 共享
                          </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={settingSources.includes('project')}
                            onChange={() => toggleSettingSource('project')}
                            className="sr-only peer"
                          />
                          <div
                            className="w-11 h-6 bg-muted rounded-full peer peer-focus:ring-2 peer-focus:ring-primary/20 dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground">
                      💡 提示：至少需要启用一个技能来源，Claude 才能发现和使用技能。
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 高级设置 */}
            {activeTab === 'advanced' && (
              <div className="space-y-8 max-w-2xl animate-in slide-in-from-right-4 duration-300">
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">流式输出配置</h3>

                  <div
                    className="flex items-center justify-between p-4 border rounded-lg bg-card hover:border-primary/20 transition-all">
                    <div className="flex-1">
                      <label className="text-sm font-medium leading-none flex items-center gap-2">
                        启用流式输出
                        {includePartialMessages && <span
                          className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-600 rounded font-medium">已启用</span>}
                      </label>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        启用后将实时显示 Agent 的输出内容，提供更流畅的交互体验。关闭后将等待完整响应后一次性显示。
                      </p>
                    </div>

                    {/* 自定义 Switch 样式 */}
                    <label className="relative inline-flex items-center cursor-pointer ml-4">
                      <input
                        type="checkbox"
                        checked={includePartialMessages}
                        onChange={(e) => setIncludePartialMessages(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div
                        className="w-11 h-6 bg-muted rounded-full peer peer-focus:ring-2 peer-focus:ring-primary/20 dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                    </label>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">限制与配额</h3>

                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">最大对话轮次</label>
                    <input
                      type="number"
                      value={maxTurns}
                      onChange={(e) => setMaxTurns(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="例如: 50"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      达到此限制后，Agent 将停止响应。留空表示无限制。
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors text-sm font-medium shadow-sm"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm font-medium shadow-sm"
          >
            {mode === 'create' ? '创建 Agent' : '保存更改'}
          </button>
        </div>
      </div>
    </div>
  );
}
