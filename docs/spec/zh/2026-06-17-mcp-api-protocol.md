# MCP API 协议

> 属于 [确定性工作流框架——高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：MCP（模型上下文协议）服务器接口、工具定义、提供商配置、MCP 与 REST 对比。

---

## Changelog

| Date       | Version | Changes                                                                                                                                 |
|------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 2026-06-17 | 0.1.0   | 初始 MCP API 协议规范：服务器接口、工具定义、提供商配置、MCP 与 REST 对比                                                              |
| 2026-06-18 | 0.1.1   | 为 `type: a2a` 工具类型添加 [Tool Ecosystem §7.5](./13-tool-ecosystem.md) 交叉引用，为 `type: sdk` 工具类型添加 §7.6 交叉引用；同步 Decision 24 |

---

## 1. 角色定位

框架将其 API 以标准 **MCP（模型上下文协议）服务器** 的形式暴露。外部 AI 工具——Claude Desktop、OpenAI、Google AI 以及其他 MCP 兼容客户端——可以像调用任何其他 MCP 工具一样调用该框架。无需自定义 SDK，无需定制 REST 客户端。一套协议，通用访问。

```
┌──────────────────────────────────────────────────────────────┐
│                     MCP 客户端                                 │
├──────────────┬──────────────┬──────────────┬─────────────────┤
│  Claude      │  OpenAI      │  Google AI   │  自定义         │
│  Desktop     │  (MCP SDK)   │  (MCP SDK)   │  MCP 客户端     │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬────────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌──────────────────────────────────────────────────────────────┐
│              MCP 服务器（确定性工作流框架）                      │
│                                                               │
│  工具:  create_conversation, send_message,                    │
│         resume_conversation, get_status                       │
│                                                               │
│  资源:  conversation://{id}/state,                            │
│         conversation://{id}/audit                             │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 MCP 提供的能力

- ✅ **标准化工具发现**——客户端通过 `tools/list` 自动发现可用的工作流端点
- ✅ **流式传输支持**——LLM 响应通过 MCP 逐 token 流式输出
- ✅ **资源访问**——对话状态、审计日志作为 MCP 资源暴露
- ✅ **提供商无关**——一次编写，连接任何 MCP 兼容的 AI 工具
- ✅ **权限模型**——MCP 服务器按客户端实施工具级访问控制

### 1.2 MCP 不替代的功能

- ❌ **非 API 网关**——不替代 Kong、Envoy 或 AWS API Gateway 的路由与限流功能
- ❌ **非 REST 替代品**——REST API 仍然保留供程序化/非 AI 客户端使用
- ❌ **非身份认证层**——认证由框架现有的令牌验证处理（参见 Auth 规范）

---

## 2. MCP 服务器接口

框架自动将工作流端点暴露为 MCP 工具。每个接受外部输入的工作流节点都成为一个 MCP 工具。服务器处理 JSON-RPC 2.0 消息收发、能力协商和传输（stdio 或 HTTP/SSE）。

### 2.1 工作流端点自动暴露

```yaml
# framework.yaml
mcp:
  enabled: true
  transport: sse                           # sse | stdio
  endpoint: /mcp                           # SSE 端点路径
  port: 8000
  tool_discovery: auto                     # auto | manual
  auto_expose:
    source: workflows                      # 暴露所有工作流入口点
    naming: snake_case                     # snake_case | camelCase
    prefix: ""                             # 工具名的可选前缀
```

当 `tool_discovery: auto` 时，框架扫描所有已注册的工作流，并从中生成 MCP 工具定义。

### 2.2 MCP 能力公告

连接时，服务器公告以下能力：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "capabilities": {
      "tools": {
        "listChanged": true
      },
      "resources": {
        "subscribe": true,
        "listChanged": false
      },
      "logging": {}
    },
    "serverInfo": {
      "name": "deterministic-workflow-framework",
      "version": "0.2.0"
    }
  }
}
```

### 2.3 传输方式

| 传输方式           | 协议                        | 使用场景               | 客户端支持                       |
|--------------------|----------------------------|------------------------|----------------------------------|
| **SSE (HTTP)**     | HTTP POST + SSE 流          | 远程部署，多客户端     | Claude Desktop、OpenAI、Google AI |
| **stdio**          | 进程 stdin/stdout           | 本地开发，嵌入式代理   | Claude Desktop、CLI 工具         |
| **WebSocket**      | WS 升级                     | 低延迟流式传输         | 自定义客户端（未来）             |

```yaml
# framework.yaml — 传输配置
mcp:
  transport:
    default: sse
    sse:
      host: "0.0.0.0"
      port: 8000
      path: /mcp
      cors:
        origins: ["*"]
    stdio:
      enabled: false                      # 主要用于本地开发
```

---

## 3. 工具定义

### 3.1 `create_conversation`

在工作流中发起一个新的对话。

```yaml
# MCP 工具: create_conversation
tool:
  name: create_conversation
  description: >
    在确定性工作流框架中创建一个新的对话。
    返回一个 conversation ID，可用于后续的 send_message 调用。
  inputSchema:
    type: object
    properties:
      workflow_id:
        type: string
        description: "要启动的工作流（例如 'home_insurance_quote'）"
      user_id:
        type: string
        description: "发起对话的用户"
      initial_context:
        type: object
        description: "可选的初始上下文，用于设定 agentState"
    required: [workflow_id, user_id]

  # 示例响应
  outputSchema:
    type: object
    properties:
      conversation_id:
        type: string
        description: "UUID v4 对话标识符"
      state:
        type: string
        description: "对话初始状态（始终为 'created'）"
      agent_message:
        type: string
        description: "代理的初始问候或提示语"
    required: [conversation_id, state]
```

### 3.2 `send_message`

向活跃对话发送用户消息，并返回代理的响应。

```yaml
# MCP 工具: send_message
tool:
  name: send_message
  description: >
    向现有对话发送用户消息。
    框架运行完整的三层管道（Extract → Decide → Respond）
    并返回结构化的 JSON 响应。
  inputSchema:
    type: object
    properties:
      conversation_id:
        type: string
        description: "要发送消息的目标对话"
      message:
        type: string
        description: "用户的自然语言消息"
      attachments:
        type: array
        items:
          type: object
          properties:
            type: { type: string }
            url: { type: string }
            metadata: { type: object }
        description: "可选的文件附件"
      metadata:
        type: object
        description: "可选的请求元数据"
    required: [conversation_id, message]

  outputSchema:
    type: object
    properties:
      conversation_id:
        type: string
      agent_message:
        type: string
        description: "代理的文本响应"
      intent:
        type: string
        description: "本轮的意图分类"
      confidence:
        type: number
        description: "意图分类置信度 (0-1)"
      state:
        type: string
        description: "处理后的当前对话状态"
      components:
        type: array
        description: "富 UI 组件（卡片、表单等）"
    required: [conversation_id, agent_message, intent, state]
```

### 3.3 `resume_conversation`

从最后一个检查点恢复一个暂停或中断的对话。

```yaml
# MCP 工具: resume_conversation
tool:
  name: resume_conversation
  description: >
    从最后一个检查点恢复现有对话。
    恢复 agentState、对话历史和执行位置。
  inputSchema:
    type: object
    properties:
      conversation_id:
        type: string
        description: "要恢复的对话"
      user_id:
        type: string
        description: "恢复对话的用户（必须与原始用户一致）"
      resume_from:
        type: string
        description: "可选：覆盖要恢复的检查点。"
        enum: [latest, specific]
      checkpoint_id:
        type: string
        description: "当 resume_from 为 'specific' 时必选"
    required: [conversation_id, user_id]

  outputSchema:
    type: object
    properties:
      conversation_id:
        type: string
      state:
        type: string
        description: "恢复后的当前状态（active）"
      agent_message:
        type: string
        description: "确认恢复或继续的代理消息"
      restored_at:
        type: string
        description: "已恢复检查点的时间戳"
    required: [conversation_id, state]
```

### 3.4 `get_status`

返回对话的当前状态和元数据。

```yaml
# MCP 工具: get_status
tool:
  name: get_status
  description: >
    获取对话的当前状态和元数据。
    不会修改对话。
  inputSchema:
    type: object
    properties:
      conversation_id:
        type: string
        description: "要查询的对话"
    required: [conversation_id]

  outputSchema:
    type: object
    properties:
      conversation_id:
        type: string
      user_id:
        type: string
      workflow_id:
        type: string
      lifecycle_state:
        type: string
        enum: [created, active, paused, completed, abandoned, timeout]
      current_phase:
        type: string
        description: "当前工作流阶段（例如 'collect_property_info'）"
      turn_count:
        type: integer
      created_at:
        type: string
      last_active_at:
        type: string
      checkpoint_count:
        type: integer
    required: [conversation_id, lifecycle_state, turn_count]
```

### 3.5 工具许可名单

通过 YAML 配置实现按客户端的工具访问控制：

```yaml
# framework.yaml
mcp:
  tool_allowlist:
    default: [create_conversation, send_message, resume_conversation, get_status]
    
    # 限制特定客户端
    clients:
      claude_desktop:
        allow: [create_conversation, send_message, resume_conversation, get_status]
      openai:
        allow: [send_message, get_status]             # 主要只读
      internal_agent:
        allow: ["*"]                                   # 完全访问
      read_only_dashboard:
        allow: [get_status]                            # 仪表盘专用
```

---

## 4. MCP 服务器配置的 YAML 配置

框架 `framework.yaml` 中的完整 MCP 服务器配置：

```yaml
# framework.yaml — 完整 MCP 服务器配置
mcp:
  enabled: true
  
  server:
    name: "deterministic-workflow-framework"
    version: "0.2.0"
    description: "确定性 AI 代理工作流的 MCP 服务器"
    transport: sse
    host: "0.0.0.0"
    port: 8000
    path: /mcp
    cors:
      origins: ["*"]

  tools:
    discovery: auto                      # auto | manual
    auto_expose:
      source: workflows
      naming: snake_case
    manual_tools:                        # 仅在 discovery: manual 时相关
      - name: create_conversation
        workflow: home_insurance_quote
        node: entry_point

  resources:
    enabled: true
    expose:
      - pattern: "conversation://{id}/state"
      - pattern: "conversation://{id}/audit"
      - pattern: "workflow://{id}/schema"

  authentication:
    required: true
    method: bearer_token                  # bearer_token | api_key | none
    token_verification:
      provider: auth0                     # 与框架认证配置相同

  rate_limiting:
    enabled: true
    requests_per_minute: 60
    burst: 10

  logging:
    level: info                           # debug | info | warn
    format: json                          # json | text
```

---

## 5. 提供商配置

### 5.1 Claude Desktop

```json
{
  "mcpServers": {
    "deterministic-workflow": {
      "command": "python",
      "args": ["-m", "deterministic_workflow.mcp_server"],
      "env": {
        "FRAMEWORK_CONFIG": "/path/to/framework.yaml",
        "ENV": "prod"
      },
      "transport": "sse",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### 5.2 OpenAI（MCP SDK）

```yaml
# OpenAI MCP 配置（通过 openai-agents SDK）
mcp_servers:
  deterministic_workflow:
    transport: sse
    url: "http://localhost:8000/mcp"
    auth:
      type: bearer
      token: "${FRAMEWORK_API_TOKEN}"
    tool_filter:
      include: [create_conversation, send_message, resume_conversation, get_status]
```

### 5.3 Google AI（MCP SDK）

```yaml
# Google AI MCP 配置
mcp_servers:
  - name: deterministic-workflow
    transport: sse
    endpoint: "http://localhost:8000/mcp"
    headers:
      Authorization: "Bearer ${FRAMEWORK_API_TOKEN}"
    tools:
      - create_conversation
      - send_message
      - resume_conversation
      - get_status
```

### 5.4 通用 MCP 客户端（stdio 传输）

```json
{
  "mcpServers": {
    "deterministic-workflow": {
      "command": "python",
      "args": ["-m", "deterministic_workflow.mcp_server", "--transport", "stdio"],
      "env": {
        "FRAMEWORK_CONFIG": "/path/to/framework.yaml",
        "ENV": "dev"
      }
    }
  }
}
```

---

## 6. MCP 与 REST 对比

### 6.1 为何选择 MCP 而非传统 REST API

| 维度             | MCP（模型上下文协议）                                            | REST API                                                        |
|------------------|----------------------------------------------------------------|-----------------------------------------------------------------|
| **客户端集成**   | AI 工具零代码——通过 `tools/list` 自动发现                       | 每个客户端必须实现 HTTP 调用、解析 JSON、处理错误               |
| **工具发现**     | 内置——客户端向服务器请求可用工具                                | 手动——需要阅读 API 文档或 OpenAPI 规范                          |
| **流式传输**     | 原生 SSE 传输，逐 token 流式输出                                | 需要自定义 SSE 或 WebSocket 实现                                |
| **模式校验**     | 服务器声明 `inputSchema`；客户端在发送前校验                    | 客户端必须手动对照 OpenAPI 规范校验                             |
| **AI 原生**      | 为 LLM → 工具调用而设计；结构化提示作为一等公民                 | 为程序化 → API 调用而设计                                       |
| **状态管理**     | 对话状态作为 MCP 资源暴露（`conversation://{id}/state`）        | 需要自定义端点进行状态查询                                      |
| **错误处理**     | 标准 JSON-RPC 错误码，附带结构化错误数据                        | HTTP 状态码 + 自定义错误体（不一致）                             |
| **客户端生态**   | Claude Desktop、OpenAI、Google AI、LangChain——全部支持 MCP      | 每个 HTTP 客户端都支持 REST                                     |
| **版本控制**     | 服务器在 `initialize` 响应中公告版本                            | API 版本控制需要 URL 路径或请求头                                |
| **多提供商**     | 一个 MCP 服务器 → 所有 AI 提供商                                | REST 通用但不针对 AI 优化                                       |

### 6.2 何时使用 REST

| 场景                                       | 建议                                       |
|--------------------------------------------|--------------------------------------------|
| 非 AI 客户端（移动应用、Web 前端）         | REST——MCP 是 AI 专用的                     |
| 高吞吐量程序化访问                         | REST——MCP 增加了 JSON-RPC 开销             |
| 现有 REST 基础设施（API 网关、限流）       | REST——利用现有工具链                       |
| 对对话进行简单的 CRUD 操作                 | REST——比 MCP 工具调用更简单                |

### 6.3 双协议策略

框架同时支持 MCP 和 REST：

```yaml
# framework.yaml
protocols:
  mcp:
    enabled: true
    transport: sse
    port: 8000
  rest:
    enabled: true
    port: 8001
    openapi_spec: true                 # 从 MCP 工具模式自动生成 OpenAPI
    endpoints:
      # REST 端点与 MCP 工具一一对应
      - POST   /v1/conversations                  → create_conversation
      - POST   /v1/conversations/{id}/messages    → send_message
      - POST   /v1/conversations/{id}/resume      → resume_conversation
      - GET    /v1/conversations/{id}             → get_status
```

---

## 7. 与现有框架组件的集成

### 7.1 通过 MCP 的认证流程

```
MCP 客户端（Claude Desktop）
    │
    │   初始化请求
    ▼
MCP 服务器
    │
    │   验证 MCP 客户端身份（Bearer token）
    ▼
[令牌验证]  ← 与 Auth 规范中使用相同的 Auth0/Okta/Keycloak 管道
    │
    └── 将用户上下文注入 agentState
```

### 7.2 检查点集成

```yaml
# MCP 资源暴露检查点
resources:
  - uri: "conversation://{conversation_id}/state"
    name: "对话状态"
    description: "对话的完整 agentState JSON"
    mimeType: "application/json"
  
  - uri: "conversation://{conversation_id}/checkpoint/{checkpoint_id}"
    name: "检查点快照"
    description: "用于时间旅行调试的特定 LangGraph 检查点"
    mimeType: "application/json"
```

### 7.3 可观测性

MCP 工具调用自动跟踪：

```yaml
observability:
  mcp_metrics:
    enabled: true
    collect:
      - tool_call_count            # 每个工具的调用次数
      - tool_call_latency_ms       # p50、p95、p99
      - tool_error_rate            # 每个工具的错误率
      - active_connections         # 并发 MCP 连接数
    export:
      format: prometheus
      endpoint: /metrics
```

---

## 8. 安全考量

| 关切                               | 缓解措施                                                                    |
|------------------------------------|----------------------------------------------------------------------------|
| **未授权 MCP 客户端**              | 每次 MCP 请求均进行 Bearer token 验证；每个客户端的工具许可名单            |
| **工具滥用（过度调用）**           | 限流（默认 60 次请求/分钟）；每个工具配额                                   |
| **对话数据泄露**                   | `user_id` 作用域隔离——MCP 客户端只能访问自己的对话                          |
| **中间人攻击**                     | 生产环境要求 SSE over HTTPS；stdio 天然安全                                 |
| **通过工具输入的注入攻击**         | 所有 MCP 工具输入均通过相同的 Layer 1 提取/验证管道处理                     |

---

## 9. 待解决问题

| #   | 问题                                                                                                                   | 影响                           |
|-----|------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| 1   | MCP 服务器是否应支持动态工具注册（在运行时添加/移除工具而不重启）？                                                    | 零停机工作流更新               |
| 2   | MCP 应如何处理长时间运行的工具调用（例如，`send_message` 由于 LLM 延迟而超过 30 秒）？是否应使用 MCP 的进度通知？        | 客户端超时处理                 |
| 3   | 框架是否应支持 MCP 资源订阅（状态变更时推送通知），还是仅轮询？                                                        | 实时仪表盘 vs 复杂度           |
| 4   | 对于多租户 SaaS 部署，应为每个租户部署一个 MCP 服务器，还是使用一个带租户路由的服务器？                                  | 可扩展性与隔离性               |
| 5   | MCP 工具响应是否应包含用于调试的 LangSmith 跟踪 URL？                                                                    | 开发者体验 vs 响应大小         |
| 6   | MCP 服务器应如何为不同环境（开发工作流 vs 生产工作流）公告不同的工具集？                                                | 环境一致性                     |

---

## References

- [高层设计](./01-deterministic-workflow-framework-design.md) — §2 核心架构，§4.1 框架原则
- [Auth & Token Verification](./16-auth-token-verification.md) — 令牌验证管道（MCP 复用）
- [Conversation Lifecycle](./07-conversation-lifecycle.md) — 生命周期状态，检查点集成
- [Observability & Monitoring](./15-observability-monitoring.md) — MCP 指标采集
- [Tool Ecosystem](./13-tool-ecosystem.md) — MCP 服务器与现有工具栈的集成
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification) — MCP 官方规范
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — Python 参考实现
