/**
 * useAgentSession Hook 类型定义
 */

import { Message, ToolCall, AgentId } from '@/types';

// ==================== Hook 选项 ====================

export interface UseAgentSessionOptions {
    /** WebSocket服务器URL */
    wsUrl?: string;
    /** 错误回调 */
    onError?: (error: Error) => void;
}

// ==================== Hook 返回值 ====================

export interface UseAgentSessionReturn {
    messages: Message[];
    toolCalls: ToolCall[];
    agentId: AgentId | null;
    isLoading: boolean;
    error: string | null;
    sendMessage: (content: string) => Promise<void>;
    startSession: () => void;
    loadSession: (agentId: AgentId) => void;
    clearSession: () => void;
    resetSession: () => void;
    loadHistoryMessages: (agentId: AgentId) => Promise<void>;
    stopGeneration: () => void;
    /** 删除一轮对话 */
    deleteRound: (roundId: string) => Promise<void>;
    /** 重新生成最后一轮回答 */
    regenerate: (roundId: string) => Promise<void>;
    // 权限相关
    pendingPermission: {
        request_id: string;
        tool_name: string;
        tool_input: Record<string, any>;
    } | null;
    sendPermissionResponse: (decision: 'allow' | 'deny') => void;
}
