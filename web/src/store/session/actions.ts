/**
 * Session Store Actions
 */

import { AgentId, CreateSessionParams, Session, UpdateSessionParams, } from '@/types';
import { SessionStoreState } from './types';
import { createDefaultSession } from './utils';
import { createSession, deleteSession, getSessions, updateSession } from "@/lib/agent-api";

// ==================== 基础操作 ====================

export const createSessionAction = (
  set: (fn: (state: SessionStoreState) => Partial<SessionStoreState>) => void,
  get: () => SessionStoreState
) => async (params?: CreateSessionParams): Promise<AgentId> => {
  // 先在本地创建会话（立即响应UI）
  const newSession = createDefaultSession(params);

  set((state) => ({
    sessions: [newSession, ...state.sessions],
    error: null,
  }));

  // 异步同步到后端
  try {
    await createSession(newSession.agentId, {
      title: params?.title,
      options: params?.options,
    });
    console.debug('[SessionStore] Session created on server:', newSession.agentId);
  } catch (error) {
    console.error('[SessionStore] Failed to sync session to server:', error);
    // 不回滚本地状态，允许离线使用
  }

  return newSession.agentId;
};


export const deleteSessionAction = (
  set: (fn: (state: SessionStoreState) => Partial<SessionStoreState>) => void,
  get: () => SessionStoreState
) => async (id: AgentId): Promise<void> => {
  try {
    // 1. Call API
    await deleteSession(id);

    // 2. Update Store
    set((state) => {
      const newSessions = state.sessions.filter(s => s.agentId !== id);
      const newCurrentId = state.currentAgentId === id
        ? (newSessions[0]?.agentId || null)
        : state.currentAgentId;

      return {
        sessions: newSessions,
        currentAgentId: newCurrentId,
        error: null,
      };
    });
  } catch (error) {
    console.error('[SessionStore] Failed to delete session:', error);
    set(() => ({error: 'Failed to delete session'}));
  }
};

export const updateSessionAction = (
  set: (fn: (state: SessionStoreState) => Partial<SessionStoreState>) => void
) => async (id: AgentId, params: UpdateSessionParams): Promise<void> => {
  try {
    // 调用后端API更新会话（包括title和options）
    await updateSession(id, params);
    console.debug('[SessionStore] Session updated on server:', id);

    // 更新本地Store
    set((state) => ({
      sessions: state.sessions.map(session =>
        session.agentId === id
          ? {
            ...session,
            ...(params.title && {title: params.title}),
            ...(params.options && {options: {...session.options, ...params.options}}),
            lastActivityAt: Date.now(),
          }
          : session
      ),
      error: null,
    }));
  } catch (error) {
    console.error('[SessionStore] Failed to update session:', error);
    set(() => ({error: 'Failed to sync update with server'}));
  }
};

export const setCurrentSessionAction = (
  set: any
) => (id: AgentId | null): void => {
  set({currentAgentId: id, error: null});
};


// ==================== 查询操作 ====================

export const getSessionAction = (get: () => SessionStoreState) => (id: AgentId): Session | undefined => {
  return get().sessions.find(s => s.agentId === id);
};


// ==================== 服务器同步 ====================

export const loadSessionsFromServerAction = (
  set: any,
  get: () => SessionStoreState
) => async (): Promise<void> => {
  try {
    console.debug('[loadSessionsFromServer] 开始从服务器加载sessions...');
    console.debug('[loadSessionsFromServer] 设置前当前状态:', {
      sessionsCount: get().sessions.length,
      currentAgentId: get().currentAgentId
    });

    set({loading: true, error: null});

    const sessions = await getSessions();
    // console.debug('[loadSessionsFromServer] 收到sessions数据:', sessions);

    if (sessions && Array.isArray(sessions)) {
      // 按最后活动时间排序（最新的在前）
      const sortedSessions = [...sessions].sort((a, b) => b.lastActivityAt - a.lastActivityAt);

      console.debug(`[loadSessionsFromServer] 成功加载 ${sortedSessions.length} 个sessions`);
      console.debug('[loadSessionsFromServer] 第一个session的agentId:', sortedSessions[0]?.agentId);

      set({sessions: sortedSessions, loading: false, error: null});

      // 验证设置后的状态
      setTimeout(() => {
        console.debug('[loadSessionsFromServer] 设置后状态:', {
          sessionsCount: get().sessions.length,
          currentAgentId: get().currentAgentId
        });
      }, 0);
    } else {
      console.error('[loadSessionsFromServer] 无效的响应格式:', sessions);
      set({loading: false, error: 'Invalid response format'});
    }
  } catch (err) {
    console.error('[loadSessionsFromServer] 加载sessions失败:', err);
    set({
      loading: false,
      error: err instanceof Error ? err.message : 'Unknown error',
    });
  }
};

// ==================== 清理 ====================

export const clearAllSessionsAction = (
  set: any
) => (): void => {
  set({
    sessions: [],
    currentAgentId: null,
    error: null,
  });
};
