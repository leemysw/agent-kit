/**
 * 消息转换器 - 将后端消息转换为前端格式
 */

import { AssistantMessage, ContentBlock, Message, ResultMessage, StreamEvent, ToolCall, UserMessage, } from '@/types';

/**
 * 将后端AMessage转换为前端消息格式
 * 后端格式: {agent_id, session_id, message_id, parent_id, message_type, block_type,  message, timestamp}
 */
export function convertBackendMessage(backendMsg: any): Message | StreamEvent | null {
  // 添加详细日志来查看收到的消息格式
  // console.debug('[convertBackendMessage] 收到消息:', JSON.stringify(backendMsg, null, 2));

  // 检查是否是消息格式
  if (!backendMsg.message_type || !backendMsg.message) {
    console.warn('[convertBackendMessage] 不是消息格式,跳过');
    console.warn('[convertBackendMessage] message_type:', backendMsg.message_type);
    console.warn('[convertBackendMessage] message:', backendMsg.message);
    return null;
  }

  const {
    agent_id,
    session_id,
    message_id,
    parent_id,
    round_id,
    message_type,
    block_type,
    message,
    timestamp
  } = backendMsg;


  // 提取content blocks
  let contentBlocks: ContentBlock[] = [];

  if (message.content) {
    if (typeof message.content === 'string') {
      // 字符串转为TextBlock
      contentBlocks = [{type: 'text', text: message.content}];
    } else if (Array.isArray(message.content)) {
      // 处理ContentBlock数组,添加type字段
      contentBlocks = message.content.map((block: any) => {
        // 如果block已经有type字段,直接使用
        if (block.type) {
          return block;
        }
        // 否则使用message的block_type
        return {...block, type: block_type};
      });
    }
  }

  // 根据message_type构造前端消息
  if (message_type === 'assistant') {
    return {
      messageId: message_id,
      agentId: agent_id,
      roundId: round_id,
      sessionId: session_id,
      ParentId: parent_id,
      timestamp: timestamp ? new Date(timestamp).getTime() : Date.now(),
      role: 'assistant',
      content: contentBlocks,
      model: message.model,
      stopReason: message.stop_reason,
      usage: message.usage,
      parentToolUseId: message.parent_tool_use_id || null,
    } as AssistantMessage;
  } else if (message_type === 'user') {

    // user消息有三种情况:
    // 1. 普通用户输入 (block_type: "text")
    // 2. Tool执行结果 (block_type: "tool_result")
    // 3. 子工具的输入（block_type: "text" and message 包含 parent_tool_use_id）


    // 如果是tool_result，应该作为assistant侧的消息显示
    if (block_type === 'tool_result') {
      // 返回一个特殊的assistant消息，包含tool result
      return {
        messageId: message_id,
        agentId: agent_id,
        sessionId: session_id,
        timestamp: timestamp ? new Date(timestamp).getTime() : Date.now(),
        role: 'assistant',
        content: contentBlocks,
        model: undefined,
        isToolResult: true, // 标记这是tool result
      } as AssistantMessage;
    } else if (message.parent_tool_use_id) {
      // 子工具的输入
      const textContent = typeof message.content === 'string'
        ? message.content
        : (contentBlocks[0] && 'text' in contentBlocks[0] ? contentBlocks[0].text : '');

      return {
        messageId: message_id,
        agentId: agent_id,
        roundId: round_id,
        sessionId: session_id,
        ParentId: parent_id,
        timestamp: timestamp ? new Date(timestamp).getTime() : Date.now(),
        role: 'assistant',
        content: textContent,
        parentToolUseId: message.parent_tool_use_id,
      } as AssistantMessage;
    }

    // 普通用户消息
    const textContent = typeof message.content === 'string'
      ? message.content
      : (contentBlocks[0] && 'text' in contentBlocks[0] ? contentBlocks[0].text : '');

    return {
      messageId: message_id,
      agentId: agent_id,
      roundId: round_id,
      sessionId: session_id,
      ParentId: parent_id,
      timestamp: timestamp ? new Date(timestamp).getTime() : Date.now(),
      role: 'user',
      content: textContent,
    } as UserMessage;
  } else if (message_type === 'system') {
    // System消息 - 不在聊天界面显示
    return null;
  } else if (message_type === 'result') {
    // Result消息 - 包含执行统计信息
    return {
      messageId: message_id,
      agentId: agent_id,
      roundId: round_id,
      sessionId: session_id,
      ParentId: parent_id,
      timestamp: timestamp ? new Date(timestamp).getTime() : Date.now(),
      role: 'result',
      subtype: message.subtype || 'success',
      durationMs: message.duration_ms || 0,
      durationApiMs: message.duration_api_ms || 0,
      numTurns: message.num_turns || 0,
      totalCostUsd: message.total_cost_usd,
      usage: message.usage ? {
        inputTokens: message.usage.input_tokens || 0,
        outputTokens: message.usage.output_tokens || 0,
        cacheReadInputTokens: message.usage.cache_read_input_tokens,
        cacheCreationInputTokens: message.usage.cache_creation_input_tokens,
        ...message.usage,
      } : undefined,
      result: message.result,
      isError: message.is_error || false,
    } as ResultMessage;
  } else if (message_type === 'stream') {
    // Stream消息 - SDK的StreamEvent结构: {uuid, event: {type, index, delta, ...}, parent_tool_use_id}
    const eventData = message.event;
    if (!eventData) {
      console.warn('[convertBackendMessage] Stream message missing event data:', message);
      return null;
    }
    // console.debug('[convertBackendMessage] Stream event:', eventData);
    return {
      type: eventData.type,
      index: eventData.index,
      delta: eventData.delta,
      content_block: eventData.content_block,
      message: eventData.message,
      messageId: message_id,
    } as StreamEvent;
  }

  return null;
}

/**
 * 提取工具调用信息
 * 从AMessage的message.content中提取tool_use类型的blocks
 */
export function extractToolCalls(backendMsg: any): ToolCall[] {
  if (!backendMsg.message || !backendMsg.message.content) {
    return [];
  }

  const toolCalls: ToolCall[] = [];
  const content = backendMsg.message.content;

  if (!Array.isArray(content)) {
    return [];
  }

  content.forEach((block: any) => {
    // 根据block_type或block.type判断是否为tool_use
    const isToolUse = backendMsg.block_type === 'tool_use' || block.type === 'tool_use';

    if (isToolUse && block.id && block.name) {
      toolCalls.push({
        id: block.id,
        toolName: block.name,
        input: block.input || {},
        status: 'running',
        startTime: Date.now(),
      });
    }
  });

  return toolCalls;
}
