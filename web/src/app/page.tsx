/**
 * 主页面
 *
 * 集成会话管理和聊天界面
 */

"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { ChatInterface } from "@/components/chat-interface";
import { AgentOptions } from "@/components/option/agent-options";
import { useSessionStore } from "@/store";
import { useInitializeSessions } from "@/hooks/use-initialize-sessions";
import { SessionOptions } from "@/types/session";
import { initialOptions } from "@/config/options";

export default function Home() {
  const {
    sessions,
    currentAgentId,
    createSession,
    setCurrentSession,
    deleteSession,
    updateSession,
    loadSessionsFromServer
  } = useSessionStore();

  // 使用自定义hook处理会话初始化
  const isHydrated = useInitializeSessions({
    loadSessionsFromServer,
    setCurrentSession,
    autoSelectFirst: true,
    debugName: "Page"
  });

  // Sidebar collapsed state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Session Options Dialog 状态
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create');
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);

  /**
   * 处理新建会话 - 打开配置对话框
   */
  const handleNewSession = () => {
    setDialogMode('create');
    setEditingAgentId(null);
    setIsDialogOpen(true);
  };

  /**
   * 处理会话配置保存
   */
  const handleSaveSessionOptions = async (title: string, options: SessionOptions) => {
    if (dialogMode === 'create') {
      // 创建新会话
      const id = await createSession({ title, options });
      setCurrentSession(id);
    } else if (dialogMode === 'edit' && editingAgentId) {
      // 更新现有会话
      await updateSession(editingAgentId, { title, options });
    }
  };

  /**
   * 处理会话设置编辑
   */
  const handleEditSession = (agentId: string) => {
    setDialogMode('edit');
    setEditingAgentId(agentId);
    setIsDialogOpen(true);
  };

  /**
   * 处理会话选择
   */
  const handleSessionSelect = (agentId: string) => {
    setCurrentSession(agentId);
  };

  /**
   * 处理会话删除
   */
  const handleDeleteSession = async (agentId: string) => {
    // Store action now handles API call
    await deleteSession(agentId);

    // 如果删除的是当前会话,切换到第一个可用会话
    if (currentAgentId === agentId) {
      const remainingSessions = sessions.filter(s => s.agentId !== agentId);
      if (remainingSessions.length > 0) {
        setCurrentSession(remainingSessions[0].agentId);
      } else {
        setCurrentSession(null);
      }
    }
  };

  /**
   * 处理标题编辑
   */
  const handleEditTitle = (agentId: string, title: string) => {
    updateSession(agentId, { title: title });
  };

  // 在hydration完成前显示加载状态
  if (!isHydrated) {
    return (
      <main className="flex h-screen w-full bg-background text-foreground items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* 侧边栏 - 会话列表 */}
      <Sidebar
        sessions={sessions}
        currentAgentId={currentAgentId}
        onNewSession={handleNewSession}
        onSessionSelect={handleSessionSelect}
        onDeleteSession={handleDeleteSession}
        onEditTitle={handleEditTitle}
        onEditSession={handleEditSession}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* 聊天界面 */}
      <ChatInterface
        agentId={currentAgentId}
        onNewSession={handleNewSession}
      />

      {/* Session Options Dialog */}
      <AgentOptions
        mode={dialogMode}
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSave={handleSaveSessionOptions}
        initialTitle={
          dialogMode === 'edit' && editingAgentId
            ? sessions.find(s => s.agentId === editingAgentId)?.title
            : undefined
        }
        initialOptions={
          dialogMode === 'edit' && editingAgentId
            ? sessions.find(s => s.agentId === editingAgentId)?.options
            : initialOptions
        }
      />
    </main>
  );
}
