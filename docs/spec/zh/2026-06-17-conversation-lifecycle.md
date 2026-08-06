# 对话生命周期

> 属于[确定性工作流框架——高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：完整的对话生命周期状态、检查点策略、超时策略、恢复流程、审计追踪、多设备支持。

---

## Changelog

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始对话生命周期规范：状态、trace_id = user_id、检查点、超时、恢复、审计、多设备 |

---

## 1. 角色

框架中的每个对话都遵循从创建到归档的明确定义的生命周期。对话是交互、追踪和恢复的基本单元。每个对话由 `conversation_id` 标识，并通过 `trace_id = user_id` 跨系统追踪。

```
┌──────────────────────────────────────────────────────────┐
│                  对话生命周期                               │
│                                                           │
│   created ──→ active ──→ completed                        │
│                │  ↑                                       │
│                │  │ resume                                │
│                ▼  │                                      │
│              paused ──→ abandoned                         │
│                │                                          │
│                ▼                                          │
│             timeout ──→ archived                          │
└──────────────────────────────────────────────────────────┘
```

### 1.1 生命周期涵盖范围

- ✅ **状态转换** — 生命周期状态之间的每条有效路径
- ✅ **检查点策略** — 何时保存，何时恢复
- ✅ **超时策略** — 空闲检测与自动状态转换
- ✅ **恢复流程** — 从冷存储恢复对话
- ✅ **审计追踪** — 记录每次转换以满足合规要求
- ✅ **多设备** — 同一用户，多个并发对话

### 1.2 生命周期不涵盖范围

- ❌ **工作流状态（FSM）** — 这是状态机管理的内部业务状态，而非生命周期
- ❌ **会话管理** — 登录/登出、令牌刷新（参见 Auth 规范）
- ❌ **消息历史存储** — 由 LangGraph 检查点处理
- ❌ **用户身份管理** — 参见 Auth 规范

---

## 2. 生命周期状态

### 2.1 状态定义

| 状态 | 描述 | 可转换至 | 检查点 |
|-------|-------------|----------------|------------|
| **created（已创建）** | 对话记录已创建，尚未发送任何消息 | active, abandoned | 无 |
| **active（活跃）** | 用户正在活跃交互；完整的三层流水线运行 | paused, completed, abandoned, timeout | 每次用户回合 |
| **paused（已暂停）** | 对话被有意暂停（用户或系统发起）；状态冻结 | active, abandoned, timeout | 暂停时 |
| **completed（已完成）** | 目标达成；成功对话的终止状态 | （终止状态） | 完成时 |
| **abandoned（已放弃）** | 用户明确结束对话或目标无法达成；终止状态 | （终止状态） | 放弃时 |
| **timeout（已超时）** | 系统触发的空闲超时；可恢复 | active, archived | 超时时 |
| **archived（已归档）** | 超长超时（24小时以上）后的冷存储；只读 | （终止状态，只读） | 归档快照 |

### 2.2 状态转换规则

```yaml
lifecycle:
  states:
    created:
      on:
        first_message: active
        abandon: abandoned
    
    active:
      on:
        pause: paused
        complete: completed
        abandon: abandoned
        idle_30min: timeout
    
    paused:
      on:
        resume: active
        idle_24h: archived
        abandon: abandoned
    
    timeout:
      on:
        resume: active
        idle_24h: archived
    
    completed:
      terminal: true
      archive_after_days: 90
    
    abandoned:
      terminal: true
      archive_after_days: 30
    
    archived:
      terminal: true
      read_only: true
```

### 2.3 生命周期状态机（YAML 视图）

```yaml
# lifecycle_fsm.yaml — 有效转换
lifecycle_state_machine:
  initial: created
  
  transitions:
    - from: created
      to: active
      trigger: first_message
      guard: user_id == conversation.user_id
    
    - from: created
      to: abandoned
      trigger: user_abandon
      guard: no_messages_sent
    
    - from: active
      to: paused
      trigger: user_pause | system_pause
      before: save_checkpoint
    
    - from: active
      to: completed
      trigger: goal_met
      before: save_final_checkpoint
      after: log_completion_audit
    
    - from: active
      to: abandoned
      trigger: user_abandon | goal_unachievable
      before: save_final_checkpoint
    
    - from: active
      to: timeout
      trigger: idle_timer_expired
      guard: idle_duration >= 30min
      before: save_checkpoint
    
    - from: paused
      to: active
      trigger: user_resume
      after: restore_checkpoint | hydrate_context
    
    - from: paused
      to: archived
      trigger: idle_24h_timer
      before: archive_conversation
    
    - from: timeout
      to: active
      trigger: user_resume
      after: restore_checkpoint | hydrate_context
    
    - from: timeout
      to: archived
      trigger: idle_24h_timer
      before: archive_conversation
```

---

## 3. 追踪模型：`trace_id = user_id`

### 3.1 为什么使用 `user_id` 作为追踪 ID

```
trace_id = user_id
```

每个用户拥有一个跨越其所有对话的 `trace_id`。这使得：

- **跨对话追踪** — 用户跨多个对话的所有交互形成一条单一追踪链
- **合规关联** — 单个用户的所有审计追踪可通过一个 ID 查询
- **系统间交接** — 当对话升级至人工客服时，`user_id` 追踪链延续到 CRM 中
- **简单集成** — 外部系统（CRM、计费、客服台）已使用 `user_id` 作为键值

### 3.2 追踪层级

```
user_id (trace_id)
  ├── conversation_1
  │     ├── turn_1  → 第1层 → 第2层 → 第3层
  │     ├── turn_2  → 第1层 → 第2层 → 第3层
  │     └── turn_n
  ├── conversation_2
  │     ├── turn_1
  │     └── turn_2
  └── conversation_n
```

### 3.3 追踪配置

```yaml
tracing:
  model: user_id_as_trace      # user_id_as_trace | conversation_as_trace
  
  # 当 trace_id = user_id 时，每个对话是用户追踪链下的一个 span
  span_hierarchy:
    root: "user:{user_id}"
    child: "conversation:{conversation_id}"
    grandchild: "turn:{turn_number}"
  
  propagation:
    # 追踪上下文通过 HTTP 头传播到外部系统
    headers:
      - "X-Trace-ID: {user_id}"
      - "X-Conversation-ID: {conversation_id}"
      - "X-Turn-ID: {turn_number}"
```

---

## 4. 检查点策略

### 4.1 何时设置检查点

| 生命周期事件 | 检查点动作 | 存储后端 |
|-----------------|-------------------|-----------------|
| **每次用户回合** | 第3层响应后自动保存 | 内存（开发）/ PostgreSQL（生产） |
| **暂停时** | 完整状态快照 | PostgreSQL / Redis |
| **完成时** | 最终快照 + 归档 | PostgreSQL |
| **超时时** | 转换前快照 | PostgreSQL |
| **放弃时** | 最终快照 | PostgreSQL |
| **归档时** | 只读归档副本 | 对象存储（S3/GCS） |

### 4.2 检查点内容

```yaml
checkpoint:
  schema:
    metadata:
      checkpoint_id: string           # UUID
      conversation_id: string
      user_id: string                 # trace_id
      lifecycle_state: string
      created_at: datetime
      turn_number: integer
    
    workflow_state:
      current_phase: string           # 例如，"collect_property_info"
      phase_stack: array              # 嵌套阶段的返回栈
      agent_state_snapshot: object    # AgentState 完整副本
    
    context:
      extraction_result: object       # 上次第1层输出
      routing_decision: object        # 上次第2层输出
      response_data: object           # 上次第3层输出
    
    messages:
      history: array                  # 最近 N 条消息（可配置窗口大小）
      window_size: 6                  # 匹配 CONTEXT_WINDOW_SIZE
    
    audit:
      state_transitions: array        # 自创建以来所有生命周期转换
      llm_calls: array                # 来自 LLM 网关的 LLM 调用记录
      tool_calls: array               # 工具调用记录
```

### 4.3 按环境的检查点后端

```yaml
# checkpoint 配置 — 引用环境配置规范 §3
checkpoint:
  dev:
    backend: in_memory
    # 进程重启时数据丢失 — 开发环境可接受
  
  e2e:
    backend: sqlite                  # 测试运行间持久化
    path: /tmp/e2e_checkpoints.db
  
  prod:
    backend: postgresql
    dsn: "${POSTGRES_DSN}"
    schema: checkpoint_store
    connection_pool:
      min_size: 5
      max_size: 20
    # 可选：为活跃对话配备 Redis 写穿缓存
    cache:
      backend: redis
      dsn: "${REDIS_DSN}"
      ttl_seconds: 1800              # 活跃对话 30 分钟缓存
```

---

## 5. 超时策略

### 5.1 空闲超时层级

| 层级 | 空闲时长 | 动作 | 结果状态 |
|------|--------------|--------|-----------------|
| **警告** | 15 分钟 | 发送"您还在吗？"提示 | active（不变） |
| **软超时** | 30 分钟 | 暂停对话，保存检查点 | paused |
| **硬超时** | 24 小时 | 归档对话 | archived |

### 5.2 YAML 配置

```yaml
lifecycle:
  timeout:
    warning:
      idle_seconds: 900              # 15 分钟
      action: send_warning_prompt    # send_warning_prompt | none
      message: "我有一段时间没收到您的回复了。您还需要帮助吗？"
    
    soft_timeout:
      idle_seconds: 1800             # 30 分钟
      action: pause                  # pause | abandon | none
      before_transition:
        - save_checkpoint
        - log_timeout_audit
    
    hard_timeout:
      idle_seconds: 86400            # 24 小时
      action: archive                # archive | abandon
      before_transition:
        - save_final_checkpoint
        - archive_messages
      archive_storage: s3            # s3 | gcs | local
    
    timer_implementation:
      strategy: scheduled_poll       # scheduled_poll | event_driven
      poll_interval_seconds: 60
      # 事件驱动替代方案（未来）：
      # strategy: event_driven
      # trigger: message_queue
```

### 5.3 计时器重置规则

```yaml
lifecycle:
  timer_reset:
    triggers:
      - user_message_sent          # 每次用户消息时重置
      - agent_message_delivered    # 代理响应后重置
      - user_resume                # 明确恢复时重置
    excludes:
      - system_message             # 内部系统消息不重置计时器
      - heartbeat                  # 保活心跳不重置计时器
```

---

## 6. 恢复流程

### 6.1 恢复序列

```
用户："resume_conversation(conversation_id)"
    │
    ▼
第1步：验证生命周期状态
    │
    ├── 状态为 active → 返回"already active"
    ├── 状态为 completed/abandoned → 返回错误
    ├── 状态为 archived → 返回"conversation expired"
    │
    └── 状态为 paused/timeout → 继续
              │
              ▼
第2步：加载检查点
    │
    ├── 从 PostgreSQL / Redis 加载
    │
    └── 验证检查点完整性（哈希校验）
              │
              ▼
第3步：填充上下文
    │
    ├── 从检查点恢复 agentState
    ├── 恢复对话历史（最近 N 条消息）
    ├── 恢复执行位置（当前阶段，phase_stack）
    │
    └── 可选：对过期的外部数据重新运行上下文填充
              │
              ▼
第4步：转换状态
    │
    └── paused/timeout → active
              │
              ▼
第5步：通知用户
    │
    └── "欢迎回来！您之前正在进行[当前阶段描述]。"
              │
              ▼
准备接收下一条 send_message
```

### 6.2 YAML 配置

```yaml
lifecycle:
  resume:
    allowed_from:
      - paused
      - timeout
    
    validation:
      verify_user_id: true          # 必须匹配原始 user_id
      verify_not_archived: true
      max_resume_count: 10          # 防止滥用
    
    context_hydration:
      rehydrate: true               # 重新运行上下文填充层
      stale_threshold_seconds: 300  # 如果检查点超过 5 分钟则重新填充
      rehydrate_strategy: selective # selective | full
    
    post_resume:
      send_welcome_back: true
      summarize_state: true         # 简要总结离开时的状态
      auto_continue: false          # 等待用户消息后再处理
```

---

## 7. 审计追踪

### 7.1 记录内容

每次生命周期转换记录一条审计条目：

```
LifecycleAuditEntry {
  timestamp:          datetime
  conversation_id:    string
  user_id:            string           // trace_id
  previous_state:     string
  new_state:          string
  trigger:            string           // first_message | user_pause | idle_timeout | ...
  metadata: {
    turn_number:      integer
    checkpoint_id?:   string
    error?:           string
  }
}
```

### 7.2 审计条目示例

```json
// 对话创建
{
  "timestamp": "2026-06-17T10:00:00Z",
  "conversation_id": "conv_abc123",
  "user_id": "user_456",
  "previous_state": null,
  "new_state": "created",
  "trigger": "create_conversation",
  "metadata": {
    "turn_number": 0,
    "workflow_id": "home_insurance_quote"
  }
}

// 对话因空闲暂停
{
  "timestamp": "2026-06-17T10:30:00Z",
  "conversation_id": "conv_abc123",
  "user_id": "user_456",
  "previous_state": "active",
  "new_state": "paused",
  "trigger": "idle_timeout",
  "metadata": {
    "turn_number": 12,
    "checkpoint_id": "ckpt_789",
    "idle_duration_seconds": 1800
  }
}

// 对话完成
{
  "timestamp": "2026-06-17T10:45:00Z",
  "conversation_id": "conv_def456",
  "user_id": "user_789",
  "previous_state": "active",
  "new_state": "completed",
  "trigger": "goal_met",
  "metadata": {
    "turn_number": 24,
    "checkpoint_id": "ckpt_final_012",
    "total_duration_seconds": 2700
  }
}
```

### 7.3 审计配置

```yaml
lifecycle:
  audit:
    enabled: true
    log_transitions: true
    log_checkpoints: true
    
    storage:
      backend: postgresql
      table: lifecycle_audit_log
    
    retention:
      active: 365 days               # 生产环境保留
      archived: 7 years              # 合规归档
    
    query_api:
      enabled: true
      filters:
        - by_user_id
        - by_conversation_id
        - by_date_range
        - by_lifecycle_state
```

---

## 8. 多设备支持

### 8.1 一个用户，多个对话

```
user_id: "user_456"
  ├── conversation_1 (home_insurance_quote)  → 状态：active
  ├── conversation_2 (home_insurance_claim)  → 状态：paused
  └── conversation_3 (claim_filing)          → 状态：completed
```

单个 `user_id` 可以跨不同工作流拥有多个并发对话。每个对话有自己的 `conversation_id`、生命周期状态和检查点——但都共享同一个 `trace_id = user_id`。

### 8.2 设备感知

```yaml
lifecycle:
  multi_device:
    enabled: true
    strategy: independent_conversations   # independent_conversations | single_conversation
    
    # independent_conversations：
    #   每个设备拥有自己的对话。
    #   用户可以同时进行多个活跃对话。
    #   最适合：多任务用户，不同设备上不同工作流。
    
    # single_conversation（未来）：
    #   所有设备共享同一对话。
    #   需要分布式锁和消息排序。
    #   最适合：单一用途助手、自助终端模式。
    
    device_tracking:
      enabled: true
      fields:
        - device_id: string
        - platform: string              # ios | android | web | cli
        - user_agent: string
```

### 8.3 对话隔离

```yaml
# 启用 multi_device 时，每个对话完全隔离：
# - 独立的 LangGraph 状态
# - 独立的检查点
# - 独立的消息历史
# - 共享：user_id（trace_id）、用户上下文（来自 Auth 规范）

lifecycle:
  conversation_per_device:
    naming_convention: "{workflow_id}_{device_id}_{timestamp}"
    max_active_per_user: 10             # 防止滥用
    cleanup:
      complete_older_than_days: 30
```

---

## 9. 集成点

### 9.1 与 Auth 规范集成

```yaml
# 生命周期根据 Auth 规范的 UserContext 验证 user_id
lifecycle:
  user_identity:
    source: agentState.user.user_id    # 来自 Auth 规范 §2.3 UserContext
    validation: verify_token           # 在敏感转换（恢复、放弃）时重新验证
```

### 9.2 与 LangGraph 检查点集成

```yaml
# 生命周期检查点使用 LangGraph 内置检查点机制
checkpoint:
  langgraph:
    # LangGraph 在每个节点执行后自动保存
    # 生命周期为每个检查点添加生命周期特定元数据
    enrichment:
      add_lifecycle_state: true
      add_timeout_timestamp: true
      add_turn_number: true
```

### 9.3 与可观测性集成

```yaml
# 生命周期转换发出指标
observability:
  lifecycle_metrics:
    - conversations_created_total
    - conversations_active_gauge
    - conversations_paused_gauge
    - conversations_completed_total
    - conversations_abandoned_total
    - conversations_timed_out_total
    - avg_conversation_duration_seconds
    - avg_turns_per_conversation
```

---

## 10. 开放问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | 框架是否应支持对话合并（用户从网页开始，在手机上作为同一对话继续）还是仅支持并行独立对话？ | 多设备架构复杂性 |
| 2 | 已归档对话是否应可恢复（法律保留、审计审查）还是永久只读？ | 受监管行业的合规要求 |
| 3 | 超时策略应如何处理用户正在输入但尚未发送的连接（例如，长消息编辑中）？ | 误报超时 |
| 4 | 框架是否应支持用户间的对话交接（例如，用户致电客服，代理接管同一对话）？ | B2B 和客服升级场景 |
| 5 | 强制归档前的最大对话时长是多少——30 天、90 天，还是可按工作流配置？ | 存储成本 vs 合规需求 |
| 6 | 检查点快照是否应包含完整的 LLM 响应原始数据（用于重放/调试）还是仅结构化输出以减少存储？ | 可调试性 vs 存储成本 |

---

## References

- [高层设计](./01-deterministic-workflow-framework-design.md) — §2 上下文填充 + 三层体系，§4.1 框架原则
- [Auth 与令牌验证](./16-auth-token-verification.md) — §2.3 UserContext 模式，user_id 来源
- [路由与执行层](./06-routing-execution-layer-design.md) — §1.2 AgentState 并发，检查点交互
- [领域模型设计](./02-domain-model-design.md) — 工作流 FSM 状态（区别于生命周期状态）
- [环境配置](./18-environment-config.md) — 按环境的检查点后端
- [可观测性与监控](./15-observability-monitoring.md) — Grafana 仪表板中的生命周期指标
- [状态机设计](./03-state-machine-design.md) — 业务状态转换（区别于生命周期）
