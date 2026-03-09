/**
 * Session 操作函数
 */

import { Message } from '@/types';
import { getSessionMessages } from "@/lib/agent-api";

/**
 * 创建新session操作
 */
export function createStartSession(
  setstring: (id: string) => void,
  setMessages: (messages: Message[]) => void,
  setToolCalls: (calls: any[]) => void,
  setError: (error: string | null) => void,
  setIsLoading: (loading: boolean) => void
) {
  return () => {
    const newstring = crypto.randomUUID();
    setstring(newstring);
    setMessages([]);
    setToolCalls([]);
    setError(null);
    setIsLoading(false);
  };
}

/**
 * 加载指定会话
 * 设置sessionKey并从后端加载历史消息
 */
export const createLoadSession = (
  setstring: (id: string) => void,
  setMessages: (messages: Message[]) => void,
  setError: (error: string | null) => void,
) => async (id: string): Promise<void> => {
  try {
    console.debug('[loadSession] 开始加载session:', id);

    // 1. 设置sessionKey
    console.debug('[loadSession] 设置sessionKey:', id);
    setstring(id);

    // 2. 清空当前消息
    setMessages([]);
    setError(null);

    // 3. 加载历史消息
    console.debug('[loadSession] 调用getSessionMessages API');
    const data = await getSessionMessages(id);

    if (data && Array.isArray(data)) {
      setMessages(data);
    } else {
      console.debug(`[loadSession] 没有收到有效消息数据:`, data);
    }
  } catch (err) {
    console.error('[loadSession] 加载session失败:', err);
    setError(err instanceof Error ? err.message : 'Failed to load session');
  }
};

/**
 * 清除session操作
 */
export function createClearSession(
  setMessages: (messages: Message[]) => void,
  setToolCalls: (calls: any[]) => void,
  setError: (error: string | null) => void,
  setIsLoading: (loading: boolean) => void,
  setstring: (id: string | null) => void,
  abortControllerRef: React.RefObject<AbortController | null>
) {
  return () => {
    setMessages([]);
    setToolCalls([]);
    setError(null);
    setIsLoading(false);
    setstring(null);

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };
}

/**
 * 重置session操作（创建新session）
 */
export function createResetSession(startSession: () => void) {
  return () => {
    startSession();
  };
}

/**
 * 加载历史消息
 */
export function createLoadHistoryMessages(
  setMessages: (messages: Message[]) => void,
  updateSession: (id: string, params: any) => void,
) {
  return async (sessionKey: string) => {
    try {
      const messages = await getSessionMessages(sessionKey);
      if (Array.isArray(messages)) {
        console.debug(`[useAgentSession] Loaded ${messages.length} messages`);
        setMessages(messages);

        // 同时更新到session store中缓存
        updateSession(sessionKey, { messages });
      }
    } catch (err) {
      console.error('[useAgentSession] Failed to load history:', err);
    }
  };
}
