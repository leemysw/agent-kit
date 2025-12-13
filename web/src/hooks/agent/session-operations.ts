/**
 * Session 操作函数
 */

import { AgentId, Message, StreamEvent } from '@/types';
import { getSessionMessages } from "@/lib/agent-api";

/**
 * 创建新session操作
 */
export function createStartSession(
  setAgentId: (id: AgentId) => void,
  setMessages: (messages: Message[]) => void,
  setToolCalls: (calls: any[]) => void,
  setError: (error: string | null) => void,
  setIsLoading: (loading: boolean) => void
) {
  return () => {
    const newAgentId = crypto.randomUUID();
    setAgentId(newAgentId);
    setMessages([]);
    setToolCalls([]);
    setError(null);
    setIsLoading(false);
  };
}

/**
 * 合并工具结果消息到对应的工具调用消息中
 */
function mergeToolResultMessages(messages: Message[]): Message[] {
  const mergedMessages: Message[] = [];
  const toolUseMap = new Map<string, number>(); // tool_use_id -> index in mergedMessages

  for (const msg of messages) {
    // 检查是否是 tool_result 消息
    if (msg.role === 'assistant' && (msg as any).isToolResult) {
      const toolResultContent = (msg as any).content;
      if (Array.isArray(toolResultContent) && toolResultContent.length > 0) {
        const toolResultBlock = toolResultContent.find((b: any) => b.type === 'tool_result');
        if (toolResultBlock) {
          const toolUseId = toolResultBlock.tool_use_id;
          const targetIndex = toolUseMap.get(toolUseId);

          if (targetIndex !== undefined) {
            // 合并到目标消息
            const targetMessage = { ...mergedMessages[targetIndex] } as any;
            targetMessage.content = [...targetMessage.content, ...toolResultContent];
            mergedMessages[targetIndex] = targetMessage;
            console.debug('[mergeToolResultMessages] Merged tool_result:', toolUseId);
            continue; // 跳过添加这条 tool_result 消息
          }
        }
      }
    }

    // 记录 tool_use 消息的位置
    if (msg.role === 'assistant' && Array.isArray((msg as any).content)) {
      const content = (msg as any).content;
      for (const block of content) {
        if (block.type === 'tool_use') {
          toolUseMap.set(block.id, mergedMessages.length);
        }
      }
    }

    mergedMessages.push(msg);
  }

  return mergedMessages;
}

/**
 * 检测并标记未完成的工具调用
 * 当页面刷新时，如果有工具调用没有对应的结果，将其标记为中断状态
 * 同时添加虚拟的 ResultMessage 以便 UI 正确显示完成状态
 */
function markInterruptedToolCalls(messages: Message[]): Message[] {
  // 收集所有 tool_use id 和 tool_result 的 tool_use_id
  const toolUseIds = new Set<string>();
  const toolResultIds = new Set<string>();
  // 检查是否已经有 resultMessage
  let hasResultMessage = false;

  for (const msg of messages) {
    if (msg.role === 'result') {
      hasResultMessage = true;
    }
    if (msg.role === 'assistant' && Array.isArray((msg as any).content)) {
      for (const block of (msg as any).content) {
        if (block.type === 'tool_use' && block.id) {
          toolUseIds.add(block.id);
        }
        if (block.type === 'tool_result' && block.tool_use_id) {
          toolResultIds.add(block.tool_use_id);
        }
      }
    }
  }

  // 找出未完成的工具调用
  const incompleteToolIds = [...toolUseIds].filter(id => !toolResultIds.has(id));

  if (incompleteToolIds.length === 0) {
    return messages;
  }

  console.debug('[markInterruptedToolCalls] 发现未完成的工具调用:', incompleteToolIds);

  // 为未完成的工具添加中断状态的 tool_result
  const updatedMessages = messages.map(msg => {
    if (msg.role === 'assistant' && Array.isArray((msg as any).content)) {
      const content = (msg as any).content;
      const hasIncompleteTools = content.some(
        (block: any) => block.type === 'tool_use' && incompleteToolIds.includes(block.id)
      );

      if (hasIncompleteTools) {
        // 为每个未完成的工具添加中断状态的 tool_result
        const additionalResults = content
          .filter((block: any) => block.type === 'tool_use' && incompleteToolIds.includes(block.id))
          .map((block: any) => ({
            type: 'tool_result',
            tool_use_id: block.id,
            content: '任务已中断（页面刷新或连接断开）',
            is_error: true,
          }));

        return {
          ...msg,
          content: [...content, ...additionalResults],
        };
      }
    }
    return msg;
  });

  // 如果没有 resultMessage，添加一个虚拟的中断状态 ResultMessage
  if (!hasResultMessage && updatedMessages.length > 0) {
    // 获取最后一条消息的信息用于构造 ResultMessage
    const lastMessage = updatedMessages[updatedMessages.length - 1];
    const interruptedResultMessage: Message = {
      messageId: `interrupted_result_${Date.now()}`,
      roundId: lastMessage.roundId,
      agentId: lastMessage.agentId,
      sessionId: lastMessage.sessionId,
      role: 'result',
      timestamp: Date.now(),
      subtype: 'error',
      durationMs: 0,
      durationApiMs: 0,
      numTurns: 0,
      result: '任务已中断（页面刷新或连接断开）',
      isError: true,
    } as Message;

    console.debug('[markInterruptedToolCalls] 添加虚拟 ResultMessage:', interruptedResultMessage);
    updatedMessages.push(interruptedResultMessage);
  }

  return updatedMessages;
}

/**
 * 加载指定会话
 * 设置agentId并从后端加载历史消息
 */
export const createLoadSession = (
  setAgentId: (id: AgentId) => void,
  setMessages: (messages: Message[]) => void,
  setError: (error: string | null) => void,
  convertBackendMessage: (msg: any, agentId: AgentId) => Message | StreamEvent | null
) => async (id: AgentId): Promise<void> => {
  try {
    console.debug('[loadSession] 开始加载session:', id);

    // 1. 设置agentId
    console.debug('[loadSession] 设置agentId:', id);
    setAgentId(id);

    // 2. 清空当前消息
    setMessages([]);
    setError(null);

    // 3. 加载历史消息
    console.debug('[loadSession] 调用getSessionMessages API');
    const data = await getSessionMessages(id);

    if (data && Array.isArray(data)) {
      console.debug(`[loadSession] 收到 ${data.length} 条原始消息:`, data);
      const convertedMessages = data
        .map((msg: any) => {
          // console.debug(`[loadSession] 转换消息:`, msg);
          // const converted = convertBackendMessage(msg, id);
          // console.debug(`[loadSession] 转换结果:`, converted);
          return convertBackendMessage(msg, id);
        })
        .filter((msg: Message | StreamEvent | null): msg is Message => {
          return msg !== null && 'role' in msg;
        });

      console.debug(`[loadSession] 成功加载 ${convertedMessages.length} 条消息`);

      // 合并工具结果
      const mergedMessages = mergeToolResultMessages(convertedMessages);
      console.debug(`[loadSession] 合并后消息数量: ${mergedMessages.length}`);

      // 检测并标记未完成的工具调用（页面刷新时中断的任务）
      const finalMessages = markInterruptedToolCalls(mergedMessages);

      setMessages(finalMessages);
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
  setAgentId: (id: AgentId | null) => void,
  abortControllerRef: React.RefObject<AbortController | null>
) {
  return () => {
    setMessages([]);
    setToolCalls([]);
    setError(null);
    setIsLoading(false);
    setAgentId(null);

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
  updateSession: (id: AgentId, params: any) => void,
  convertBackendMessage: (msg: any, agentId: AgentId) => Message | StreamEvent | null
) {
  return async (agentId: AgentId) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010'}/agent/v1/sessions/${agentId}/messages`
      );

      if (!response.ok) {
        throw new Error(`Failed to load history: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.messages && Array.isArray(data.messages)) {
        console.debug(`[useAgentSession] Loaded ${data.messages.length} messages`);

        const convertedMessages = data.messages
          .map((msg: any) => convertBackendMessage(msg, agentId))
          .filter((msg: Message | StreamEvent | null): msg is Message => {
            return msg !== null && 'role' in msg;
          });

        // 合并工具结果
        const mergedMessages = mergeToolResultMessages(convertedMessages);
        console.debug(`[useAgentSession] Merged messages count: ${mergedMessages.length}`);

        setMessages(mergedMessages);

        // 同时更新到session store中缓存
        updateSession(agentId, { messages: mergedMessages });
      }
    } catch (err) {
      console.error('[useAgentSession] Failed to load history:', err);
    }
  };
}
