# WebSocket 会话管理流程设计

## 设计理念

**核心思想**：按需创建（Lazy Loading），消息驱动（Message Driven）

- ✅ 所有会话操作由 `chat` 消息触发
- ✅ 后端自动判断新建/恢复session
- ✅ 单一WebSocket连接处理多个session


## 核心流程

### 1. 整体流程图

```mermaid
flowchart TD
    A[前端发送chat消息] --> B{提取agent_id}
    B --> C[后端_handle_chat_message]
    C --> D{agent_id在session_manager中?}
    
    D -->|存在| E[获取现有SDK client]
    D -->|不存在| F{查询数据库}
    
    F -->|有历史记录| G[创建SDK client 带resume参数]
    F -->|无历史记录| H[创建新SDK client]
    
    G --> I[缓存到session_manager]
    H --> I
    E --> J[执行query操作]
    I --> J
    
    J --> K[流式返回消息]
    K --> L[前端接收显示]
```

### 2. 详细时序图

```mermaid
sequenceDiagram
    participant Frontend as 前端
    participant WebSocket as WebSocketHandler
    participant SessionManager as SessionManager
    participant Database as 数据库
    participant SDK as ClaudeSDKClient

    Frontend->>WebSocket: {type: "chat", agent_id: "xxx", content: "你好"}
    
    WebSocket->>SessionManager: get_or_create_client(agent_id)
    
    alt Session已在内存
        SessionManager-->>WebSocket: 返回现有client
    else Session不在内存
        SessionManager->>Database: 查询session_info(agent_id)
        
        alt 数据库有历史
            Database-->>SessionManager: session_id="abc123"
            SessionManager->>SDK: ClaudeSDKClient(resume="abc123")
        else 数据库无历史
            Database-->>SessionManager: null
            SessionManager->>SDK: ClaudeSDKClient()
        end
        
        SessionManager->>SessionManager: 缓存client
        SessionManager->>Database: 保存/更新session
        SessionManager-->>WebSocket: 返回client
    end
    
    WebSocket->>SDK: client.query(content)
    
    loop 流式消息
        SDK-->>WebSocket: SystemMessage/AssistantMessage/...
        WebSocket->>Frontend: 转发消息（带agent_id）
    end
    
    Note over WebSocket,SessionManager: 如果是首次获取session_id
    WebSocket->>SessionManager: register_sdk_session(agent_id, session_id)
    SessionManager->>Database: 更新session_id
```

### 3. Session切换流程

```mermaid
sequenceDiagram
    participant Frontend as 前端
    participant WebSocket as WebSocketHandler
    participant SessionManager as SessionManager

    Note over Frontend: 用户在Session A
    Frontend->>WebSocket: {type: "chat", agent_id: "A", content: "消息A"}
    WebSocket->>SessionManager: get_or_create_client("A")
    SessionManager-->>WebSocket: client_A
    WebSocket->>Frontend: 返回响应（带agent_id: "A"）

    Note over Frontend: 用户切换到Session B
    Frontend->>WebSocket: {type: "chat", agent_id: "B", content: "消息B"}
    WebSocket->>SessionManager: get_or_create_client("B")
    SessionManager-->>WebSocket: client_B
    WebSocket->>Frontend: 返回响应（带agent_id: "B"）

    Note over Frontend,SessionManager: 同一个WebSocket连接，无需断开重连
```

## 消息协议

### 前端发送消息

```typescript
// Chat消息（唯一的消息类型）
{
    type: "chat",
    agent_id: string,      // 必填
    content: string,      // 必填
    options?: {           // 可选
        model?: string,
        // ... 其他配置
    }
}

// 中断消息
{
    type: "interrupt",
    agent_id: string
}

// 心跳
{
    type: "ping"
}
```

### 后端返回消息

所有消息都包含`agent_id`和`session_id`：

```python
{
    "message_type": "assistant",
    "agent_id": "xxx",           # 前端会话ID
    "session_id": "yyy",        # SDK会话ID
    "message": {...},
    "timestamp": "..."
}
```

## Session生命周期

```mermaid
stateDiagram-v2
    [*] --> Idle: WebSocket连接建立
    
    Idle --> Creating: 首次发送chat消息
    Creating --> Active: Session创建成功
    
    Idle --> Resuming: 发送chat消息（历史session）
    Resuming --> Active: Session恢复成功
    
    Active --> Active: 持续对话
    Active --> Switching: 切换agent_id
    Switching --> Active: 获取另一个session
    
    Active --> Idle: 长时间无活动
    Active --> [*]: WebSocket断开
```
