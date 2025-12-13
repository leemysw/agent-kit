/**
 * Session Store 类型定义
 */

import { AgentId, CreateSessionParams, Session, UpdateSessionParams, } from '@/types';

// ==================== Store State ====================

export interface SessionStoreState {
  // 数据
  sessions: Session[];
  currentAgentId: AgentId | null;

  // UI状态
  loading: boolean;
  error: string | null;

  // 基础操作
  createSession: (params?: CreateSessionParams) => Promise<AgentId>;
  deleteSession: (id: AgentId) => void;
  updateSession: (id: AgentId, params: UpdateSessionParams) => void;
  setCurrentSession: (id: AgentId | null) => void;

  // 查询和搜索
  getSession: (id: AgentId) => Session | undefined;

  // 服务器同步
  loadSessionsFromServer: () => Promise<void>;

  // 清理
  clearAllSessions: () => void;
}

// ==================== 导出数据类型 ====================

export interface ExportData {
  session: Session;
  messages: any[];
  exportedAt: number;
  version: string;
}
