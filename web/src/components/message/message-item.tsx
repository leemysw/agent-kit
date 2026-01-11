/**
 * Message Component
 *
 *
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Copy, Edit2, Terminal, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { ContentBlock, Message, ResultMessage } from "@/types/message";
import { UserQuestionAnswer } from "@/types/ask-user-question";
import { ContentRenderer } from "./content-renderer";
import { MessageStats } from "@/components/header/message-stats";

interface MessageItemProps {
  roundId: string;
  messages: Message[];
  isLastRound?: boolean;
  isLoading?: boolean;
  pendingPermission?: {
    request_id: string;
    tool_name: string;
    tool_input: Record<string, any>;
  } | null;
  /** 权限响应回调（也用于 AskUserQuestion） */
  onPermissionResponse?: (decision: 'allow' | 'deny', userAnswers?: UserQuestionAnswer[]) => void;
  hiddenToolNames?: string[];
  onDelete?: (roundId: string) => Promise<void>;
  onRegenerate?: (roundId: string) => Promise<void>;
  onEditUserMessage?: (messageId: string, newContent: string) => void;
  className?: string;
}

export function MessageItem(
  {
    roundId,
    messages,
    isLastRound,
    isLoading,
    pendingPermission,
    onPermissionResponse,
    hiddenToolNames = ['TodoWrite'],
    onDelete,
    onRegenerate,
    onEditUserMessage,
    className,
  }: MessageItemProps) {
  const roundRef = useRef<HTMLDivElement>(null);
  const [copiedUser, setCopiedUser] = useState(false);
  const [copiedAssistant, setCopiedAssistant] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // 分离消息
  const { userMessage, assistantMessages, resultMessage } = useMemo(() => {
    const user = messages.find(m => m.role === 'user');
    const result = messages.find(m => m.role === 'result') as ResultMessage | undefined;
    const assistant = messages.filter(m => m.role === 'assistant');
    return { userMessage: user, assistantMessages: assistant, resultMessage: result };
  }, [messages]);

  // 合并并去重 assistant 内容
  const mergedContent = useMemo(() => {
    const allBlocks: ContentBlock[] = [];
    const seenToolIds = new Set<string>();

    for (const msg of assistantMessages) {
      if (!Array.isArray(msg.content)) continue;
      for (const block of msg.content) {
        if (!block) {
          console.debug('[assistantMessages] block is null or undefined')
          continue;
        }
        if (block.type === 'tool_use' && block.id) {
          if (seenToolIds.has(block.id)) continue;
          seenToolIds.add(block.id);
        }
        if (block.type === 'tool_result' && block.tool_use_id) {
          if (seenToolIds.has(`result_${block.tool_use_id}`)) continue;
          seenToolIds.add(`result_${block.tool_use_id}`);
        }
        allBlocks.push(block);
      }
    }
    return allBlocks;
  }, [assistantMessages]);

  // 获取纯文本内容用于复制
  const assistantTextContent = useMemo(() => {
    const texts: string[] = [];
    for (const block of mergedContent) {
      if (block.type === 'text' && block.text) {
        texts.push(block.text);
      }
    }
    // 如果有最终回答，也加入
    if (resultMessage?.result) {
      texts.push(resultMessage.result);
    }
    return texts.join('\n\n');
  }, [mergedContent, resultMessage]);

  // 元数据
  const firstAssistant = assistantMessages[0];
  const model = firstAssistant && 'model' in firstAssistant ? firstAssistant.model : undefined;
  const timestamp = firstAssistant?.timestamp || resultMessage?.timestamp;

  // 统计信息
  const stats = useMemo(() => {
    if (!resultMessage) return null;
    const cacheHit = resultMessage.usage?.cacheReadInputTokens;
    return {
      duration: resultMessage.durationMs >= 1000
        ? `${(resultMessage.durationMs / 1000).toFixed(1)}s`
        : `${resultMessage.durationMs}ms`,
      tokens: resultMessage.usage
        ? `↑ ${resultMessage.usage.inputTokens} ↓ ${resultMessage.usage.outputTokens}`
        : null,
      cost: resultMessage.totalCostUsd !== undefined
        ? `$ ${resultMessage.totalCostUsd ? resultMessage.totalCostUsd.toFixed(4) : null}`
        : null,
      cacheHit: cacheHit && cacheHit > 0 ? `💾 ${cacheHit}` : null,
    };
  }, [resultMessage]);

  // 状态
  const hasFinalAnswer = !!resultMessage;
  const userContent = useMemo(() => {
    if (!userMessage) return '';
    return typeof userMessage.content === 'string' ? userMessage.content : '';
  }, [userMessage]);

  const shouldHideAssistantContent = useMemo(() => {
    if (mergedContent.length === 0) return true;
    return mergedContent.every(block => {
      if (block.type === 'text') return !block.text?.trim();
      if (block.type === 'tool_use') return hiddenToolNames.includes(block.name);
      return block.type === 'tool_result';
    });
  }, [mergedContent, hiddenToolNames]);

  // 滚动
  useEffect(() => {
    if (isLastRound && roundRef.current) {
      roundRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [isLastRound]);

  // 操作
  const handleCopyUser = useCallback(async () => {
    if (!userContent) return;
    try {
      await navigator.clipboard.writeText(userContent);
      setCopiedUser(true);
      setTimeout(() => setCopiedUser(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [userContent]);

  const handleCopyAssistant = useCallback(async () => {
    if (!assistantTextContent) return;
    try {
      await navigator.clipboard.writeText(assistantTextContent);
      setCopiedAssistant(true);
      setTimeout(() => setCopiedAssistant(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [assistantTextContent]);

  const handleDelete = useCallback(async () => {
    if (!onDelete || isDeleting) return;
    setIsDeleting(true);
    try {
      await onDelete(roundId);
    } finally {
      setIsDeleting(false);
    }
  }, [onDelete, roundId, isDeleting]);

  const handleRegenerate = useCallback(async () => {
    if (!onRegenerate || isRegenerating) return;
    setIsRegenerating(true);
    try {
      await onRegenerate(roundId);
    } finally {
      setIsRegenerating(false);
    }
  }, [onRegenerate, roundId, isRegenerating]);

  const showCursor = isLastRound && isLoading && assistantMessages.length > 0;
  const isCompleted = hasFinalAnswer && !isLoading;

  // 格式化时间
  const formatTime = (ts: number) => {
    const date = new Date(ts);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div ref={roundRef}
      className={cn("w-full space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300", className)}>

      {/* ═══════════════════════ 用户消息 ═══════════════════════ */}
      {userMessage && (
        <div className="w-full px-4">
          <div className="max-w-4xl mx-auto">
            <div className="group flex items-end gap-3 ">

              <div className={cn(
                "flex-1 relative border rounded-lg overflow-hidden transition-all duration-300",
                "border-accent/30 bg-gradient-to-br from-accent/5 to-transparent hover:border-accent/50"
              )}>
                {/* Decorative Corners */}
                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-accent/50" />
                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-accent/50" />
                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-accent/50" />
                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-accent/50" />

                {/* 头部 */}
                <div className="h-7 px-3 flex items-center gap-2 border-b border-accent/10">
                  <div className="flex-1" />

                  {/* 操作按钮 */}
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={handleCopyUser}
                      className={cn(
                        "p-1 rounded transition-colors",
                        copiedUser ? "text-green-500" : "text-muted-foreground/50 hover:text-foreground"
                      )}
                      title="复制"
                    >
                      {copiedUser ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </button>
                    {onEditUserMessage && (
                      <button
                        onClick={() => {
                          const newContent = prompt('编辑消息:', userContent);
                          if (newContent && newContent !== userContent) {
                            onEditUserMessage(userMessage.messageId, newContent);
                          }
                        }}
                        className="p-1 rounded text-muted-foreground/50 hover:text-foreground transition-colors"
                        title="编辑"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {/* 时间 */}
                  <span className="text-[10px] font-mono text-muted-foreground/50">
                    {userMessage.timestamp ? formatTime(userMessage.timestamp) : '--:--'}
                  </span>

                  {/* 头像在右边 */}
                  <span className="text-[10px] font-medium text-accent/70">You</span>
                  <User className="w-3 h-3 text-accent/70" />
                </div>

                {/* 内容 */}
                <div className="px-4 py-3">
                  <p className="text-sm text-foreground leading-relaxed text-right">{userContent}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════ 助手消息 ═══════════════════════ */}
      {!shouldHideAssistantContent && (
        <div className="w-full px-4">
          <div className="max-w-4xl mx-auto">
            <div className="group flex items-start gap-3">

              <div className={cn(
                "flex-1 relative border rounded-lg overflow-hidden transition-all duration-500",
                "border-primary/20 bg-gradient-to-br from-primary/5 to-transparent",
                showCursor && "border-primary/40 shadow-[0_0_15px_rgba(0,240,255,0.08)]",
                isCompleted && "border-green-500/20"
              )}>
                {/* Decorative Corners */}
                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-primary/50" />
                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-primary/50" />
                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-primary/50" />
                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-primary/50" />

                {/* 扫描线效果 */}
                {showCursor && (
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    <div className="absolute inset-0 animate-scan" />
                  </div>
                )}

                {/* 优雅的头部栏 */}
                <div className="h-7 px-3 flex items-center gap-2 border-b border-primary/10">
                  <Terminal className="w-3 h-3 text-primary/70" />
                  <span className="text-[10px] font-medium text-primary/70">Assistant</span>

                  {/* 时间 */}
                  <span className="text-[10px] font-mono text-muted-foreground/50">
                    {timestamp ? formatTime(timestamp) : '--:--'}
                  </span>

                  {/* 模型 */}
                  {model && (
                    <span className="text-[10px] text-muted-foreground/40">{model}</span>
                  )}

                </div>

                {/* 内容区 */}
                <div className={cn(
                  "p-4 text-sm leading-relaxed",
                  showCursor && "min-h-[60px]"
                )}>

                  <ContentRenderer
                    content={mergedContent}
                    isStreaming={showCursor}
                    pendingPermission={pendingPermission}
                    onPermissionResponse={onPermissionResponse}
                    hiddenToolNames={hiddenToolNames}
                  />

                  {/* 打字光标 */}
                  {showCursor && (
                    <span className="inline-block w-2 h-4 ml-0.5 bg-primary/80 animate-pulse" />
                  )}
                </div>

                {/* 底部统计栏（完成后显示） */}
                {isCompleted && stats && (
                  <MessageStats
                    stats={stats}
                    showCursor={showCursor}
                    copiedAssistant={copiedAssistant}
                    isRegenerating={isRegenerating}
                    isDeleting={isDeleting}
                    onCopyAssistant={handleCopyAssistant}
                    onRegenerate={onRegenerate && isCompleted ? handleRegenerate : undefined}
                    onDelete={onDelete ? handleDelete : undefined}
                  />
                )}

                {/* 底部进度条（流式时） */}
                {showCursor && (
                  <div className="h-0.5 animate-progress-bar" />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageItem;
