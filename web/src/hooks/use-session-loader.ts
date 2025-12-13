import { useEffect, useRef } from "react";

export const useSessionLoader = (
  externalAgentId: string | null,
  loadSession: (agentId: string) => void,
  debugName = "useSessionLoader"
) => {
  const prevExternalAgentId = useRef<string | null>(null);

  useEffect(() => {
    console.debug(`[${debugName}] useEffect触发`, {
      prevAgentId: prevExternalAgentId.current,
      newAgentId: externalAgentId,
      loadSession: typeof loadSession
    });

    // 检查外部ID是否真的发生了变化
    if (prevExternalAgentId.current === externalAgentId) {
      console.debug(`[${debugName}] AgentId没有变化，跳过`);
      return; // 没有变化，不处理
    }

    // 更新ref
    prevExternalAgentId.current = externalAgentId;

    if (externalAgentId) {
      // 加载指定会话
      console.debug(`[${debugName}] Loading session:`, externalAgentId);
      loadSession(externalAgentId);
    } else {
      // 外部没有选中任何会话，不自动创建
      // 用户需要点击"New Session"按钮来创建
      console.debug(`[${debugName}] No session selected`);
    }
  }, [externalAgentId, loadSession, debugName]);
};