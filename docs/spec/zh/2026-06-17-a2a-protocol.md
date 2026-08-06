# A2A（Agent-to-Agent）协议

> 隶属于 [确定性工作流框架——高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：子工作流如何演变为 agent-to-agent 通信——A2A 消息格式、发现机制、同步/异步语义、与 MCP 的关系，以及 A2A 运行时协议。

---

## Changelog

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始 A2A 协议规范：消息格式、发现机制、同步/异步、MCP 对比 |
| 2026-06-18 | 0.1.1 | 新增对 [Tool Ecosystem §7.5](./13-tool-ecosystem.md) 的交叉引用，涉及 `type: a2a` 工具集成（将 A2A agent 作为节点级工具，支持多轮对话）；与 Decision 24 同步 |

---

## 1. 角色定位

公司的业务流程都是相互关联的——一个工作流就是另一个工作流的子工作流。其架构本质上是 Agent-to-Agent。

子工作流**不是**简单的函数调用。它们是 agent 对 agent 的交互——每个子工作流本身都是一个完整、自治的 agent，拥有自己的领域模型、权限模型、重试预算和路由逻辑。当父工作流调用一个子工作流时，它是在将目标委托给另一个 agent，而不是调用一个子程序。

```
父工作流（Agent A）
    │
    │  "我需要一个 FAQ 答案来回答这个问题"
    │  A2A: entities + goal → Agent B
    │
    ▼
子工作流（Agent B: rag_faq）
    │
    │  执行: search → generate → return
    │  A2A: results + audit → Agent A
    │
    ▼
父工作流使用 Agent B 的输出继续执行
```

本规范将 **A2A 定义为 agent 之间的运行时通信协议**。子工作流（参见 Routing & Execution 规范 §5）是**定义语言**——它们定义了 agent 的领域模型、状态、转换、权限和重试预算。A2A 是 **agent 在运行时相互通信的方式**。

### 1.1 核心洞察：每个子工作流都是一个 Agent

| 概念 | 子工作流规范 | A2A 协议 |
|---------|-------------------|--------------|
| **角色** | 定义语言——该 agent 能做什么 | 运行时协议——agent 之间如何通信 |
| **产物** | `rag_faq.yaml`——entities、states、transitions、permissions | A2A 消息——线路上传输的 input/output |
| **使用时机** | 设计时（工作流编写） | 运行时（agent 对 agent 的调用） |
| **类比** | 类定义 | 方法调用 |

### 1.2 A2A 不涵盖的内容

- **子工作流定义** → Routing & Execution 规范 §5
- **MCP 工具调用** → Tool Ecosystem 规范 §7
- **OAuth / 用户身份** → Auth Token Verification 规范
- **响应生成** → Response Generation 规范

> **新增（2026-06-18）：** A2A 协议也可作为**工具类型**（`type: a2a`）使用——任何节点都可以将另一个 agent 作为其 `tool_allowlist` 中的工具进行调用，并支持多轮对话。参见 [Tool Ecosystem §7.5](./13-tool-ecosystem.md) 了解 A2A 工具注册、多轮 A2A 对话以及 A2A-tool-vs-sub-workflow 对比矩阵。

---

## 2. A2A 协议契约

### 2.1 核心语义

```
A2A 调用（Agent A → Agent B）:
  Input:   entities + goal + correlation_id
  Output:  results + audit + correlation_id
```

协议是基于意图的，而非基于函数调用的。Agent A 发送它*想要完成什么*（goal + 相关 entities），而不是*如何去做*。Agent B 使用自己的内部工作流来决定如何达成该目标。

### 2.2 A2A 消息格式

每条 A2A 消息都携带一个标准信封：

```yaml
# A2A Request——由调用方 agent 发送给目标 agent
a2a_request:
  # --- 路由 ---
  agent_id: string                   # 目标 agent 标识符（在注册中心中注册）
  correlation_id: string             # UUID——跨异步边界将请求与响应关联

  # --- 上下文 ---
  caller:
    agent_id: string                 # 调用方 agent 标识符
    workflow_id: string              # 哪个工作流实例正在调用

  # --- 载荷 ---
  goal:
    summary: string                  # 调用方希望目标完成什么
    expected_outputs: string[]       # 期望返回哪些输出

  entities:                          # 传递给目标 agent 的相关实体数据
    <entity_name>: <entity_data>

  constraints:
    deadline_ms: integer             # 可选——响应的硬性截止时间
    priority: low | normal | high | critical

  # --- 协议 ---
  mode: sync | async                 # 调用方期望等待还是继续执行
  version: string                    # A2A 协议版本（例如 "1.0.0"）
```

```yaml
# A2A Response——由目标 agent 发送回调用方
a2a_response:
  # --- 路由 ---
  correlation_id: string             # 匹配请求的 correlation_id

  # --- 状态 ---
  status: completed | failed | partial | timeout

  # --- 载荷 ---
  results:                           # 来自目标 agent 的结构化输出
    <output_name>: <output_data>

  # --- 审计 ---
  audit:
    agent_id: string                 # 哪个 agent 产生了此响应
    steps_completed: string[]        # 目标 agent 内部遍历的状态
    duration_ms: integer
    attempts: integer                # 已使用的重试次数（包括 LLM +1）

  # --- 错误（当 status != completed 时） ---
  error:
    category: llm_error | api_error | validation_error | permission_error | business_rule_error
    message: string
    gap_analysis: string             # 哪些目标标准未满足
```

### 2.3 A2A 与 Sub-Workflow Input 映射

A2A 协议是线路格式。子工作流的 `input_mapping`（Routing & Execution 规范 §5.6）定义了父状态如何映射到 A2A 请求字段：

```yaml
# 父工作流 YAML——子工作流调用
states:
  handle_question_in_quote:
    executor: sub_workflow
    sub_workflow: rag_faq
    mode: sync
    input_mapping:                        # 这些映射到 A2A 请求
      goal:
        summary: "回答用户的 FAQ 问题"
        expected_outputs: [answer]
      entities:
        question_input:
          question: "{{state.last_user_message}}"
          conversation_context: "{{state.conversation_history}}"
      constraints:
        deadline_ms: 10000
    on_return: collect_property_info
```

框架根据此映射自动生成 A2A 信封。开发者无需手动编写 A2A 消息。

---

## 3. 框架暴露的两种 API 格式

框架暴露两个协议族。两者均基于 JSON、在传输层无状态，并携带 correlation ID——但服务于不同的用例。

| | MCP | A2A |
|---|-----|-----|
| **角色** | 外部工具调用 | 内部 agent 委托 |
| **消费者** | 外部系统（Claude Desktop、IDE、CLI） | 内部 agent（父工作流） |
| **语义** | 函数调用："用这些参数执行此工具" | 基于意图："用这些实体达成此目标" |
| **状态** | 无状态工具执行 | Agent 拥有自己的状态机、权限、重试机制 |
| **发现** | MCP `list_tools` | Agent Registry `discover` |
| **响应** | ToolResult { success, data } | AgentResult { status, results, audit } |
| **认证** | MCP 服务器级认证 | 继承自调用方的 UserContext |
| **示例** | `calculate_premium(params)` | "为此保单处理理赔 → agent_claims" |

```
┌─────────────────────────────────────────────────────────┐
│                   框架边界                                 │
│                                                           │
│  外部                        内部                          │
│  ┌──────────┐               ┌──────────────────┐         │
│  │  MCP     │──────────────→│  工具执行          │         │
│  │  Client  │  函数调用      │  (无状态)          │         │
│  │ (Claude, │               └──────────────────┘         │
│  │  IDE)    │                                            │
│  └──────────┘               ┌──────────────────┐         │
│                              │  Agent Registry   │         │
│  ┌──────────┐               │       │          │         │
│  │  Agent A │──────────────→│  A2A  │  Agent B │         │
│  │ (父       │  基于意图      │       │  (子      │         │
│  │  工作流) │               │       │  工作流)   │         │
│  └──────────┘               └──────────────────┘         │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 3.1 同一协议族，不同用例

MCP 和 A2A 共享共同的设计理念：
- 两者都携带 `correlation_id` 以实现可追溯性
- 两者都是 JSON 结构化
- 两者都支持同步和异步模式
- 两者都通过注册中心进行注册和发现

它们的不同之处在于**语义层级**：MCP 是工具级（"执行此操作"），A2A 是 agent 级（"达成此目标"）。

```yaml
# framework.yaml——协议配置
protocols:
  mcp:
    enabled: true
    servers:                          # 参见 Tool Ecosystem 规范 §7
      knowledge_base: ...
      claims_gateway: ...

  a2a:
    enabled: true
    version: "1.0.0"
    agents:
      discovery: registry             # registry | static_list
      registry:
        backend: postgresql           # postgresql | file | consul
        connection_string: "${A2A_REGISTRY_DSN}"
```

---

## 4. Agent 发现

### 4.1 Agent Registry

父工作流通过注册中心发现可用的 A2A agent。注册中心回答：*"有哪些 agent 可用，它们能做什么，我如何与它们通信？"*

```yaml
# rag_faq 的 Agent Registry 条目
agent_registry:
  agents:
    - agent_id: rag_faq
      version: "1.0.0"
      description: "使用 RAG 知识库回答用户问题"
      capability: faq_answering
      expected_inputs:
        - question_input                    # 实体: question + conversation context
      expected_outputs:
        - answer_output                     # 实体: answer + sources
      modes: [sync, async]
      max_concurrency: 50
      health_endpoint: "/a2a/health"
      invoke_endpoint: "/a2a/invoke"
      status: active                        # active | degraded | offline
```

### 4.2 发现流程

```
父工作流启动
    │
    ├── 1. 查询注册中心："查找 capability=faq_answering 的 agent"
    │
    ├── 2. 注册中心返回：[rag_faq (active, v1.0.0)]
    │
    ├── 3. 框架验证：
    │       ✓ agent 处于 active 状态
    │       ✓ agent 支持请求的模式（sync/async）
    │       ✓ agent 版本兼容
    │
    └── 4. 框架在工作流持续期间缓存 agent 描述符
```

### 4.3 静态 vs 动态发现

```yaml
# framework.yaml
a2a:
  discovery:
    mode: dynamic                     # dynamic | static
    registry:                         # 当 mode=dynamic 时使用
      backend: consul                 # consul | postgresql | etcd
      endpoint: "${CONSUL_HTTP_ADDR}"
      refresh_interval_sec: 30        # 重新同步 agent 列表的频率
    static_agents:                    # 当 mode=static 时使用
      - agent_id: rag_faq
        endpoint: "http://localhost:8001"
      - agent_id: claims_processor
        endpoint: "http://localhost:8002"
      - agent_id: property_verification
        endpoint: "http://localhost:8003"
```

| 模式 | 用例 | 权衡 |
|------|----------|-----------|
| **Dynamic** | 多服务部署；agent 独立扩缩容 | 需要服务发现基础设施（Consul、etcd） |
| **Static** | 单体/单进程；简单部署 | 无动态扩缩容；需要手动重新配置 |

---

## 5. 同步 vs 异步 A2A

### 5.1 语义

子工作流规范（Routing & Execution §5.4）中定义的同步/异步语义同样适用于 A2A 协议层——但现在具有完整的 agent 语义：

```yaml
# 同步 A2A 调用
states:
  answer_faq_question:
    executor: a2a_invoke
    agent: rag_faq
    mode: sync
    timeout_ms: 10000
    on_return: collect_property_info

# 异步 A2A 调用
states:
  background_verification:
    executor: a2a_invoke
    agent: property_verification
    mode: async
    on_complete: risk_result_received         # 当异步 agent 完成时的回调
    on_timeout: proceed_without_risk_check    # 当异步 agent 无响应时的回退
```

### 5.2 同步流程

```
Agent A                        Agent B
  │                              │
  ├── A2A Request ──────────────→│
  │                              ├── 执行工作流
  │   (阻塞，等待)                │   search → generate → validate
  │                              │
  │←── A2A Response ────────────┤
  │    status: completed          │
  ├── 恢复父工作流执行              │
```

### 5.3 异步流程

```
Agent A                        Agent B
  │                              │
  ├── A2A Request ──────────────→│
  │   mode: async                 ├── 执行工作流
  │                              │   ...
  ├── 继续父工作流执行              │
  │   ...                         │
  │                              ├── A2A Response (回调)
  │   [on_complete 触发] ←──────┤
  ├── 处理结果                     │
```

### 5.4 异步回调模式

```yaml
# framework.yaml——异步 A2A 回调配置
a2a:
  async:
    callback:
      strategy: webhook | polling | message_queue
      webhook:
        endpoint: "/a2a/callback/{correlation_id}"
        retry_on_failure: true
        max_retries: 3
      polling:
        interval_ms: 1000
        max_polls: 30
      message_queue:
        backend: redis           # redis | rabbitmq | kafka
        channel: "a2a.responses"
```

---

## 6. A2A 执行流程

### 6.1 完整生命周期

```
1. 父工作流到达 a2a_invoke 节点
2. 框架解析 agent_id → 查询注册中心 → 获取 agent 描述符
3. 框架验证：
     ✓ Agent 处于 active 状态
     ✓ Agent 支持请求的模式
     ✓ 调用方有权调用此 agent
4. 框架构造 A2A 请求：
     - 通过 input_mapping 将父状态映射到 A2A 请求载荷
     - 生成 correlation_id
     - 根据 constraints 设置截止时间
5a. [Sync] 框架发送 A2A 请求，阻塞，等待响应
5b. [Async] 框架发送 A2A 请求，立即继续父工作流执行
6. 目标 agent 接收 A2A 请求 → 执行自己的状态机
7. 目标 agent 返回 A2A 响应
8a. [Sync] 父工作流接收响应 → 在 on_return 处恢复工作流
8b. [Async] 父工作流的 on_complete 回调触发 → 处理响应
9. 审计：双方使用 correlation_id 记录 A2A 交互日志
```

### 6.2 A2A 权限模型

Agent 可以限制哪些调用方可以调用它们：

```yaml
# 带有调用方白名单的 Agent Registry 条目
agent_registry:
  agents:
    - agent_id: claims_processor
      allowed_callers:
        - home_insurance_quote              # 仅此工作流可以调用
      deny_all_others: true
    - agent_id: rag_faq
      allowed_callers: ["*"]                # 任何 agent 都可以调用
```

### 6.3 A2A 错误处理

当 A2A 调用失败时，错误将路由到 `errorNode`，遵循与所有其他错误相同的模式（Routing & Execution 规范 §6）：

```yaml
# 每个节点的 A2A 错误配置
states:
  handle_claim:
    executor: a2a_invoke
    agent: claims_processor
    mode: sync
    on_error:
      route_to: errorNode
      fallback_on_timeout: queue_for_retry
      max_retries: 2
```

| A2A 错误 | 处理方式 |
|-----------|----------|
| Agent 不可达（网络） | 带退避的重试 → errorNode |
| Agent 超时 | errorNode（fallback_value 或 escalate） |
| Agent 返回 `status: failed` | errorNode 附带 agent 的 gap_analysis |
| Agent 返回 `status: partial` | 决策：接受部分结果或触发 errorNode |
| 权限拒绝（调用方不被允许） | 立即 errorNode——不重试 |

---

## 7. 对比：MCP vs A2A

### 7.1 并排对比

| 维度 | MCP | A2A |
|-----------|-----|-----|
| **语义层级** | 工具（"执行操作"） | Agent（"达成目标"） |
| **状态** | 无状态 | 有状态（agent 拥有自己的 FSM） |
| **输入** | 工具名称 + 参数 | Entities + goal + constraints |
| **输出** | ToolResult { success, data } | AgentResult { status, results, audit } |
| **发现** | 通过 MCP 握手的 `list_tools` | Agent Registry 查询 |
| **重试** | 简单：重试工具调用 | 复杂：在其自身预算内的 agent 级重试 |
| **权限** | 工具级 access_level | Agent 级 + 继承的 UserContext |
| **审计** | 记录工具调用 | 记录完整子工作流追踪 |
| **协议版本** | MCP 规范版本 | A2A 规范版本 |
| **消费者** | 外部客户端 | 内部工作流 |
| **示例** | `search_documents(query)` | "回答此 FAQ 问题 → rag_faq agent" |

### 7.2 何时使用哪种

```
决策树：

消费者是外部系统（IDE、Claude Desktop、CLI）吗？
  └─ 是 → MCP
  └─ 否 → 继续

任务是否需要自己的状态机、权限和重试机制？
  └─ 是 → A2A（它是一个 agent）
  └─ 否 → 继续

任务是具有明确输入/输出的单一操作吗？
  └─ 是 → MCP 工具（更简单）
  └─ 否 → A2A（需要 agent 级自主性）
```

### 7.3 共存

一个 agent 可以同时暴露 MCP 工具和 A2A 端点：

```yaml
# rag_faq agent——双重协议暴露
rag_faq:
  a2a:
    endpoint: "/a2a/invoke"
    capability: faq_answering
  mcp:
    tools:
      - search_knowledge_base
      - get_document
```

这意味着：
- **父工作流**通过 A2A 调用 `rag_faq`（委托完整的 FAQ 工作流）
- **外部工具（如 Claude Desktop）**也可以通过 MCP 调用 `rag_faq.search_knowledge_base`（使用其单独的能力）

---

## 8. 子工作流规范交叉引用更新

A2A 协议对现有子工作流规范（Routing & Execution §5）的补充如下：

| 子工作流规范 § | A2A 关系 |
|---------------------|------------------|
| §5.1 概念——"完整、独立的工作流" | A2A 将其形式化为 agent 独立性 |
| §5.2 完整工作流结构——domain model、entities、states | 这些是 agent 的内部定义（不通过 A2A 暴露） |
| §5.3 节点编排——serial、parallel、DAG | 内部执行——对调用方不可见 |
| §5.4 同步 vs 异步 | A2A 协议将其作为 `mode` 字段携带 |
| §5.5 子工作流嵌套 | 递归 A2A：Agent A → Agent B → Agent C |
| §5.6 从父工作流调用——input_mapping | Input_mapping 生成 A2A 请求载荷 |

**新增：A2A 对子工作流规范的补充：**
- 线路格式（A2A 请求/响应信封）
- Agent registry + 发现
- 调用方权限模型
- 异步回调机制
- 跨 agent 边界的 Correlation ID

---

## 9. 待解决问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | A2A 是否应支持流式响应（agent 在产生结果的过程中流式传输部分结果），还是仅支持完整响应？ | 长时间运行的 agent 用户体验 |
| 2 | Agent registry 是否应支持版本协商（调用方请求 agent v1.2，注册中心返回最新的兼容版本）？ | Agent 演进 |
| 3 | 对于异步 A2A：如果父工作流在异步 agent 响应之前终止，correlation 会发生什么？ | 资源清理 |
| 4 | A2A 是否应支持双向通信（agent B 可以在执行过程中向 agent A 请求澄清）？ | 复杂 agent 交互 |
| 5 | Agent registry 应如何处理 agent 健康状态（心跳、降级状态传播）？ | 生产环境弹性 |
| 6 | A2A 消息是否应持久化到事件日志中以供重放/调试（事件溯源模式）？ | 审计和调试 |
| 7 | A2A agent 是否可以部署为独立的服务（微服务），如果可以，服务网格集成接口是什么？ | 部署架构 |
| 8 | A2A 是否应支持"对话"模式，即 agent 在完成之前交换多条消息（不仅仅是 request/response）？ | 复杂多步委托 |

---

## References

- [High-Level Design](./01-deterministic-workflow-framework-design.md)——框架架构、权限模型
- [Routing & Execution Layer](./06-routing-execution-layer-design.md)——子工作流规范（§5）、重试（§6）、权限（§7）
- [Tool Ecosystem](./13-tool-ecosystem.md)——MCP 服务器集成（§7）、工具注册
- [Auth Token Verification](./16-auth-token-verification.md)——UserContext 注入
- [Google A2A Protocol](https://github.com/google/A2A)——Google 的 Agent-to-Agent 协议（概念参考）
