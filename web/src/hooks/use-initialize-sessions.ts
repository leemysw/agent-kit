import { useEffect, useState } from "react";
import { useSessionStore } from "@/store/session";

interface UseInitializeSessionsOptions {
  loadSessionsFromServer: () => Promise<void>;
  setCurrentSession: (agentId: string) => void;
  autoSelectFirst?: boolean;
  debugName?: string;
}

export const useInitializeSessions = (
  {
    loadSessionsFromServer,
    setCurrentSession,
    autoSelectFirst = true,
    debugName = "useInitializeSessions"
  }: UseInitializeSessionsOptions) => {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // 标记已完成hydration
    setIsHydrated(true);

    // 从服务器加载历史会话（仅当localStorage为空时）
    const currentState = useSessionStore.getState();
    if (currentState.sessions.length > 0) {
      console.debug(`[${debugName}] 本地已有sessions，跳过服务器加载`);
      return;
    }

    // 从服务器加载历史会话
    console.debug(`[${debugName}] 初始化: 开始加载sessions...`);
    loadSessionsFromServer()
      .then(() => {
        // 加载完成后重新获取最新的状态
        const currentState = useSessionStore.getState();
        console.debug(`[${debugName}] Sessions加载完成, 当前sessions数量:`, currentState.sessions.length);
        console.debug(`[${debugName}] 当前选中的agentId:`, currentState.currentAgentId);

        // 如果没有选中的会话,但有历史会话,自动选择第一个
        if (autoSelectFirst && !currentState.currentAgentId && currentState.sessions.length > 0) {
          console.debug(`[${debugName}] 自动选择第一个session:`, currentState.sessions[0].agentId);
          setCurrentSession(currentState.sessions[0].agentId);
        }
      })
      .catch((err) => {
        console.error(`[${debugName}] 加载sessions失败:`, err);
      });
  }, [loadSessionsFromServer, setCurrentSession, autoSelectFirst, debugName]);

  return isHydrated;
};