/**
 * useAgentSession Hook - 主入口
 *
 * 管理Agent会话的WebSocket连接、消息处理和会话状态
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from '@/lib/websocket';
import { useSessionStore } from '@/store/session';
import { AgentId, Message, ToolCall } from '@/types';
import { UseAgentSessionOptions, UseAgentSessionReturn } from './types';
import { convertBackendMessage, extractToolCalls } from './message-converter';
import {
  createClearSession,
  createLoadHistoryMessages,
  createLoadSession,
  createResetSession,
  createStartSession,
} from './session-operations';
import { deleteRound as deleteRoundApi } from '@/lib/agent-api';

// ==================== Hook实现 ====================

export function useAgentSession(options: UseAgentSessionOptions = {}): UseAgentSessionReturn {
  const wsUrl = options.wsUrl || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8010/agent/v1/chat/ws';

  // 状态
  const [messages, setMessages] = useState<Message[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // agentId 初始为 null，只在创建或加载 session 时设置
  const [agentId, setAgentId] = useState<AgentId | null>(null);
  // 权限请求状态
  const [pendingPermission, setPendingPermission] = useState<{
    request_id: string;
    tool_name: string;
    tool_input: Record<string, any>;
  } | null>(null);

  // Store
  const {getSession, updateSession} = useSessionStore();

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * 处理WebSocket消息
   */
  const handleWebSocketMessage = useCallback((backendMsg: any) => {
    // 处理错误
    if (backendMsg.error_type) {
      console.error('[useAgentSession] Error:', backendMsg);
      setError(backendMsg.message || 'Unknown error');
      setIsLoading(false);
      return;
    }

    // 处理普通消息 - 移除agentId依赖，使用消息中的agent_id
    if (backendMsg.message_type) {
      const messageAgentId = backendMsg.agent_id || agentId;
      if (!messageAgentId) {
        console.warn('[useAgentSession] 消息缺少agent_id:', backendMsg);
        return;
      }

      const newMessage = convertBackendMessage(backendMsg);
      const newToolCalls = extractToolCalls(backendMsg);

      if (newMessage) {
        setMessages(prev => {
          // 1. 处理流式消息 (StreamEvent)
          if ('type' in newMessage && !('role' in newMessage)) {
            const event = newMessage as any; // StreamEvent
            // console.debug('[useAgentSession] Processing stream event:', event.type, event);

            if (event.type === 'message_start') {
              // 创建新的 Assistant 消息
              // 从 backendMsg 获取 roundId，确保流式消息正确分组
              const messageRoundId = backendMsg.round_id || '';
              const newMsg: any = {
                messageId: event.messageId,
                agentId: messageAgentId,
                roundId: messageRoundId,
                role: 'assistant',
                content: [],
                timestamp: Date.now(),
                model: event.message?.model,
              };
              console.debug('[useAgentSession] Created new assistant message with roundId:', messageRoundId);
              return [...prev, newMsg];
            }

            const lastMsg = prev[prev.length - 1];
            if (!lastMsg || lastMsg.role !== 'assistant') {
              console.warn('[useAgentSession] No assistant message to update');
              return prev;
            }

            const updatedMsg = {...lastMsg} as any;
            updatedMsg.content = [...updatedMsg.content];

            if (event.type === 'content_block_start') {
              if (event.content_block) {
                updatedMsg.content[event.index] = event.content_block;
                console.debug('[useAgentSession] Started content block:', event.index, event.content_block);
              }
            } else if (event.type === 'content_block_delta') {
              const delta = event.delta;
              const index = event.index;
              const block = updatedMsg.content[index];

              if (block && delta) {
                if (block.type === 'text' && delta.type === 'text_delta') {
                  updatedMsg.content[index] = {
                    ...block,
                    text: block.text + (delta.text || '')
                  };
                } else if (block.type === 'thinking' && delta.type === 'thinking_delta') {
                  updatedMsg.content[index] = {
                    ...block,
                    thinking: block.thinking + (delta.thinking || '')
                  };
                } else if (block.type === 'tool_use' && delta.type === 'input_json_delta') {
                  // 处理 tool_use 的 input 流式更新
                  // delta.partial_json 包含完整的 JSON 字符串
                  try {
                    const parsedInput = JSON.parse(delta.partial_json);
                    updatedMsg.content[index] = {
                      ...block,
                      input: parsedInput
                    };
                    console.debug('[useAgentSession] Updated tool_use input:', block.name);
                  } catch (e) {
                    // JSON 解析失败，可能是部分数据，暂存原始字符串
                    console.debug('[useAgentSession] Partial tool input, waiting for complete JSON');
                  }
                }
              }
            } else if (event.type === 'message_delta') {
              if (event.delta?.stop_reason) {
                updatedMsg.stopReason = event.delta.stop_reason;
              }
              if (event.usage) {
                updatedMsg.usage = event.usage;
              }
            }

            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = updatedMsg;
            return newMessages;
          }

          // 2. 处理普通消息 (Message)
          // 首先检查是否已经存在相同messageId的消息（流式结束后的完整消息）
          console.debug('[useAgentSession] Processing message:', newMessage);
          const existingIndex = prev.findIndex(m => m.messageId === (newMessage as Message).messageId);
          if (existingIndex !== -1 && (newMessage as Message).messageId) {
            // 更新现有消息，保留完整内容
            const newMessages = [...prev];
            newMessages[existingIndex] = newMessage as Message;
            console.debug('[useAgentSession] Updated existing message:', (newMessage as Message).messageId);
            return newMessages;
          }

          // 检查是否是 tool_result 消息
          if (newMessage.role === 'assistant' && (newMessage as any).isToolResult) {
            const toolResultContent = (newMessage as any).content;
            // 确保 content 是数组且包含 tool_result
            if (Array.isArray(toolResultContent) && toolResultContent.length > 0) {
              const toolResultBlock = toolResultContent.find((b: any) => b.type === 'tool_result');

              if (toolResultBlock) {
                const toolUseId = toolResultBlock.tool_use_id;

                // 从后往前查找包含对应 tool_use 的消息
                const targetIndex = [...prev].reverse().findIndex(msg =>
                  msg.role === 'assistant' &&
                  Array.isArray(msg.content) &&
                  msg.content.some((b: any) => b.type === 'tool_use' && b.id === toolUseId)
                );

                if (targetIndex !== -1) {
                  // 找到了，计算实际索引
                  const actualIndex = prev.length - 1 - targetIndex;
                  const newMessages = [...prev];
                  const targetMessage = {...newMessages[actualIndex]} as any;

                  // 合并 content
                  targetMessage.content = [...targetMessage.content, ...toolResultContent];
                  newMessages[actualIndex] = targetMessage;

                  console.debug('[useAgentSession] Merged tool_result into previous message:', toolUseId);
                  return newMessages;
                }
              }
            }
          }

          // 默认行为：追加新消息
          return [...prev, newMessage as Message];
        });
      }

      if (newToolCalls.length > 0) {
        setToolCalls(prev => [...prev, ...newToolCalls]);
      }

      // 如果是stream事件，保持loading状态
      if (backendMsg.message_type === 'stream') {
        setIsLoading(true);
      }

      // 如果是result类型，停止loading
      if (backendMsg.message_type === 'result') {
        setIsLoading(false);
      }
    }

    // 处理事件
    if (backendMsg.event_type) {
      // 处理权限请求事件
      if (backendMsg.event_type === 'permission_request') {
        const data = backendMsg.data || {};
        console.debug('[useAgentSession] Permission request:', data);
        setPendingPermission({
          request_id: data.request_id,
          tool_name: data.tool_name,
          tool_input: data.tool_input || {},
        });
        return;
      }

      if (backendMsg.event_type === 'stream_end') {
        setIsLoading(false);
      }
    }
  }, [agentId]);

  // WebSocket
  const {state: wsState, send: wsSend} = useWebSocket({
    url: wsUrl,
    autoConnect: true,  // 启用自动连接
    reconnect: true,
    heartbeatInterval: 0,
    onMessage: handleWebSocketMessage,
    onError: (event) => {
      const errorMsg = 'WebSocket error occurred';
      console.error('[useAgentSession] WebSocket error:', event);
      setError(errorMsg);
      if (options.onError) {
        options.onError(new Error(errorMsg));
      }
    },
  });

  /**
   * 发送消息
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    if (!agentId) {
      const errorMsg = '请先选择或创建会话';
      console.error('[sendMessage] No agentId available');
      setError(errorMsg);
      return;
    }

    if (wsState !== 'connected') {
      const errorMsg = 'WebSocket未连接,请稍候重试';
      console.error('[sendMessage] WebSocket not connected, state:', wsState);
      setError(errorMsg);
      return;
    }

    console.debug('[sendMessage] 发送消息, agentId:', agentId);

    try {
      // 创建用户消息
      const message_id = crypto.randomUUID();
      const userMessage: Message = {
        messageId: message_id,
        roundId: message_id,
        agentId: agentId,
        role: 'user',
        content,
        timestamp: Date.now(),
      };

      // 先添加到UI
      setMessages(prev => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      // 发送到后端
      wsSend({
        type: 'chat',
        content,
        agent_id: agentId,
      });

      console.debug('[sendMessage] 消息发送成功');
    } catch (err) {
      console.error('[sendMessage] 发送消息失败:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
      setIsLoading(false);
    }
  }, [wsState, agentId, wsSend]);

  /**
   * 停止生成
   */
  const stopGeneration = useCallback(() => {
    console.debug('[useAgentSession] 停止生成被调用:', {
      agentId,
      wsState,
      hasAbortController: !!abortControllerRef.current,
      hasWsSend: !!wsSend
    });

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // 发送到后端
    if (agentId && wsSend) {
      const interruptMsg = {type: 'interrupt', agent_id: agentId};
      console.debug('[useAgentSession] 发送停止消息:', interruptMsg);
      console.debug('[useAgentSession] WebSocket 状态:', wsState);

      try {
        wsSend(interruptMsg);
        console.debug('[useAgentSession] 停止消息已发送');
      } catch (error) {
        console.error('[useAgentSession] 发送停止消息失败:', error);
      }
    } else {
      console.warn('[useAgentSession] 无法发送停止消息:', {
        agentId: !!agentId,
        wsSend: !!wsSend,
        wsState
      });
    }

    setIsLoading(false);

  }, [agentId, wsSend, wsState]);

  /**
   * 发送权限响应
   */
  const sendPermissionResponse = useCallback((decision: 'allow' | 'deny') => {
    if (!pendingPermission) return;

    const response = {
      type: 'permission_response',
      request_id: pendingPermission.request_id,
      agent_id: agentId,
      decision,
      message: decision === 'deny' ? 'User denied permission' : '',
    };

    console.debug('[useAgentSession] Sending permission response:', response);
    wsSend(response);
    setPendingPermission(null);
  }, [pendingPermission, agentId, wsSend]);

  /**
   * 删除一轮对话
   */
  const deleteRound = useCallback(async (roundId: string) => {
    if (!agentId) {
      console.error('[deleteRound] No agentId available');
      return;
    }

    try {
      await deleteRoundApi(agentId, roundId);
      // 从本地消息中移除
      setMessages(prev => prev.filter(m => m.roundId !== roundId));
      console.debug('[deleteRound] 删除成功:', roundId);
    } catch (err) {
      console.error('[deleteRound] 删除失败:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete round');
    }
  }, [agentId]);

  /**
   * 重新生成最后一轮回答
   * 保留用户问题，只删除回答后重新生成
   */
  const regenerate = useCallback(async () => {
    if (!agentId || messages.length === 0) {
      console.error('[regenerate] No agentId or messages');
      return;
    }

    // 找到最后一轮的用户消息
    let lastUserMessage = null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === 'user' && m.messageId === m.roundId) {
        lastUserMessage = m;
        break;
      }
    }
    if (!lastUserMessage) {
      console.error('[regenerate] No user message found');
      return;
    }

    const lastRoundId = lastUserMessage.roundId;
    const lastContent = typeof lastUserMessage.content === 'string' ? lastUserMessage.content : '';

    try {
      // 1. 删除后端的整轮数据
      await deleteRound(lastRoundId);

      // 2. 发送消息
      await sendMessage(lastContent);

      console.debug('[regenerate] 重新生成成功，保留用户问题');
    } catch (err) {
      console.error('[regenerate] 重新生成失败:', err);
      setError(err instanceof Error ? err.message : 'Failed to regenerate');
      setIsLoading(false);
    }
  }, [agentId, messages, wsSend]);

  // 创建操作函数
  const loadHistoryMessages = useCallback(
    createLoadHistoryMessages(setMessages, updateSession, convertBackendMessage),
    [updateSession]
  );

  const startSession = useCallback(
    createStartSession(setAgentId, setMessages, setToolCalls, setError, setIsLoading),
    []
  );

  const loadSession = useCallback(
    createLoadSession(setAgentId, setMessages, setError, convertBackendMessage),
    []
  );

  const clearSession = useCallback(
    createClearSession(setMessages, setToolCalls, setError, setIsLoading, setAgentId, abortControllerRef),
    []
  );

  const resetSession = useCallback(
    createResetSession(startSession),
    [startSession]
  );

  // 清理
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    toolCalls,
    agentId,
    isLoading,
    error,
    sendMessage,
    startSession,
    loadSession,
    clearSession,
    resetSession,
    loadHistoryMessages,
    stopGeneration,
    deleteRound,
    regenerate,
    // 权限相关
    pendingPermission,
    sendPermissionResponse,
  };
}

// 导出类型
export type { UseAgentSessionOptions, UseAgentSessionReturn } from './types';
