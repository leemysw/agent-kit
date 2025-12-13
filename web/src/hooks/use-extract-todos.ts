import { useEffect, useRef, useState } from "react";
import { TodoItem } from "@/components/todo/agent-task-widget";
import { Message } from "@/types/message";

export const useExtractTodos = (
  messages: Message[],
  externalAgentId: string | null
) => {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const prevSessionRef = useRef<string | null>(null);

  // Extract todos from messages (reset on session change)
  useEffect(() => {
    // Session changed - reset todos immediately
    if (prevSessionRef.current !== externalAgentId) {
      setTodos([]);
      prevSessionRef.current = externalAgentId;
    }

    // No session - don't extract
    if (!externalAgentId || messages.length === 0) {
      return;
    }

    let latestTodos: TodoItem[] = [];
    let found = false;

    // Iterate backwards to find the latest TodoWrite tool use
    // Only consider messages from current session
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];

      // Skip messages that don't belong to current session
      if (msg.agentId && msg.agentId !== externalAgentId) {
        continue;
      }

      if (msg.role === "assistant" && Array.isArray(msg.content)) {
        for (const block of msg.content) {
          if (block.type === "tool_use" && block.name === "TodoWrite") {
            if (block.input && Array.isArray(block.input.todos)) {
              latestTodos = block.input.todos;
              found = true;
            }
          }
        }
      }
      if (found) break;
    }

    setTodos(found ? latestTodos : []);
  }, [messages, externalAgentId]);

  return todos;
};