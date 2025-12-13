/**
 * Session Store - 主入口
 *
 * 使用 Zustand 管理会话状态
 */

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { SessionStoreState } from './types';
import * as actions from './actions';

// ==================== Store创建 ====================

export const useSessionStore = create<SessionStoreState>()(
  persist(
    (set, get) => ({
      // 初始状态
      sessions: [],
      currentAgentId: null,
      loading: false,
      error: null,

      // 基础操作
      createSession: actions.createSessionAction(set, get),
      deleteSession: actions.deleteSessionAction(set, get),
      updateSession: actions.updateSessionAction(set),
      setCurrentSession: actions.setCurrentSessionAction(set),

      // 查询操作
      getSession: actions.getSessionAction(get),

      // 服务器同步
      loadSessionsFromServer: actions.loadSessionsFromServerAction(set, get),

      // 清理
      clearAllSessions: actions.clearAllSessionsAction(set),
    }),
    {
      name: 'agent-ui-sessions',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        currentAgentId: state.currentAgentId,
      }),
      onRehydrateStorage: () => (state) => {
        console.debug('[Store] rehydrated from localStorage:', state?.sessions?.length || 0);
        console.debug('[Store] localStorage currentAgentId:', state?.currentAgentId);
      },
    }
  )
);

// ==================== 导出类型 ====================

export type { SessionStoreState } from './types';
export { generateAgentId, createDefaultSession } from './utils';
