# Agent 类型 — 专用执行 Agent

> 属于 [确定性工作流框架 — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：两个 agent 抽象，在意图分类和状态机路由后执行任务。写操作由确定性状态机处理——不由 agent 处理。

---

## 更新日志

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-18 | 0.2.0 | 移除 WriteAgent——写操作是状态机的领域，而非 agent 的领域 |
| 2026-06-18 | 0.1.0 | 初始 agent 类型规范 — ReadOnlyAgent、WriteAgent、EscalationAgent |

---

## 1. 角色

Layer 1 分类意图、Layer 2 决定下一个状态后，**Layer 3 将执行委托给特定类别意图的专用 agent**。写/事务性操作（报价、理赔、保单变更）由状态机确定性地处理——不委托给 agent。

```
Intent Classification → State Machine → Agent Dispatch
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │                                                   │
              ReadOnlyAgent                                      EscalationAgent
              （闲聊、RAG 问答）                                  （投诉、转人工）
                    │                                                   │
                    └─────────────────────────┬─────────────────────────┘
                                              │
                                     State Machine（写操作）
                                     RAG Pipeline
                                     LLM Gateway
```

### 设计原则

1. **能力边界。** 每个 agent 声明其允许的操作。ReadOnlyAgent 不能写。所有写操作通过状态机。
2. **状态感知。** Agent 接收 `agentState` 上下文——知道用户处于什么阶段，已收集了什么数据。
3. **基于 Protocol。** 与 RAG 接口一样，所有 agent 都是 `Protocol` 类。任何符合约定的实现都可以使用。
4. **单一职责。** Agent 处理一个类别的意图。没有 agent 做所有事情。
5. **写入是确定性的。** 写操作（创建、更新、删除、执行）由状态机通过可审计的转换处理。不允许 LLM 决定写入。

---

## 2. Agent 接口

### 2.1 ReadOnlyAgent

回答问题、检索信息、处理闲聊。**不能修改状态或执行事务。**

```python
from typing import Protocol, Any

class ReadOnlyAgent(Protocol):
    """用于闲聊和基于 RAG 的问答的 Agent。只读——不改变状态。

    仅两个使用场景：
        1. chitchat       — 随意社交对话
        2. ask_question   — 通过 RAG 检索回答的开放式问题

    不属于此 agent（由状态机确定性地处理）：
        - help、repeat、check_coverage、ask_about_claim_status → 确定性查询
    """

    def query(
        self,
        prompt: str,
        intent: str,
        agent_state: dict[str, Any],
        **kwargs: Any,
    ) -> ReadOnlyResult:
        """回答问题或检索信息。

        prompt：       用户的原始消息或重新表述的查询
        intent：       分类后的意图标签（例如 'ask_question'）
        agent_state：  当前 agent 状态（阶段、已收集字段、对话历史）
        kwargs：       Agent 特定参数

        返回包含答案和来源引用的 ReadOnlyResult。
        """
        ...

    def capabilities(self) -> list[str]:
        """返回此 agent 支持的操作列表。
        示例：['search_kb', 'summarize', 'translate', 'faq_lookup']
        """
        ...


@dataclass
class ReadOnlyResult:
    """ReadOnlyAgent 查询结果。"""
    response: str                              # 答案文本
    sources: list[RetrievedDocument] = field(default_factory=list)  # 引用文档
    confidence: float = 1.0                    # agent 对答案的置信度
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 2.2 EscalationAgent

转接给人工操作员。收集上下文、确定紧急程度、启动转接。**本身不解决问题。**

```python
from typing import Protocol, Any, Optional

class EscalationAgent(Protocol):
    """用于人工转接的 Agent。收集上下文并转接——绝不解决。

    分配的意图：
        - escalate
        - complaint

    后端示例：
        - 工单创建（Zendesk、Jira Service Desk、ServiceNow）
        - 在线客服转接（Intercom、LiveChat、自定义）
        - 邮件/短信通知值班团队
    """

    def escalate(
        self,
        intent: str,
        reason: str,
        urgency: str,
        agent_state: dict[str, Any],
        **kwargs: Any,
    ) -> EscalationResult:
        """转接给人工操作员。

        intent：       'escalate' 或 'complaint'
        reason：       用户提供的原因或提取的投诉主题
        urgency：      'low' | 'medium' | 'high' | 'critical'
        agent_state：  完整 agent 状态（阶段、对话历史、已收集数据）
        kwargs：       Agent 特定参数

        返回包含转接状态的 EscalationResult。
        """
        ...

    def capabilities(self) -> list[str]:
        """返回此 agent 支持的操作列表。
        示例：['create_ticket', 'live_transfer', 'schedule_callback', 'notify_team']
        """
        ...


@dataclass
class EscalationResult:
    """EscalationAgent 转接结果。"""
    status: str                                # "transferred" | "ticket_created" | "queued"
    ticket_id: Optional[str] = None             # 转接的参考 ID
    estimated_wait: Optional[str] = None        # 例如 "~5 minutes"
    response: str = ""                         # 等待时的用户提示消息
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 3. Agent 调度

状态机根据意图决定由哪个 agent 处理：

```
def dispatch_agent(intent: str, intent_defs: dict) -> type[Protocol]:
    agent_map = {
        # ReadOnlyAgent 意图（仅 RAG 支持）
        "ask_question":          ReadOnlyAgent,
        "chitchat":              ReadOnlyAgent,

        # EscalationAgent 意图
        "escalate":              EscalationAgent,
        "complaint":             EscalationAgent,
    }
    return agent_map.get(intent)
```

**无专属 agent 的意图**（`start_conversation`、`finish_conversation`、`pause`、`restart`、`confirm`、`decline`、`correction`、`provide_information`、`ambiguous_request`、`out_of_scope`、`unrecognized_intent`，以及所有写意图如 `get_quote`、`file_claim`、`renew_policy`、`update_policy`、`cancel_policy`）由状态机直接处理——它们是对话控制、槽位填充或确定性写操作。

---

## 4. Agent → 工具权限模型

每个 agent 类型有一组有边界的允许操作。工具生态系统强制执行这些边界：

| Agent 类型 | 可读取（RAG） | 可调用 API | 可写 DB | 可转接人工 |
|------------|-------------|-----------|--------|-----------|
| **ReadOnlyAgent** | 是 | 否 | 否 | 否 |
| **EscalationAgent** | 是（上下文） | 否 | 否 | 是 |
| **状态机（写操作）** | 否 | 是 | 是 | 否 |

写操作绝不委托给 agent。它们作为确定性状态机转换执行，具有完整的审计追踪。

---

## 5. 配置

```yaml
# framework.yaml — agent 配置
agents:
  read_only:
    backend: "rag_pipeline"    # rag_pipeline | faq_engine | custom
    rag:
      top_k: 5
      max_context_length: 4000
    fallback_response: "抱歉，我找不到该问题的答案。"

  escalation:
    backend: "ticket"          # ticket | live_chat | custom
    ticket:
      system: "zendesk"        # zendesk | jira | servicenow | custom
      default_priority: "medium"
    live_chat:
      enabled: false
      provider: "intercom"     # intercom | livechat | custom
```

---

## 6. 本规范不涵盖的内容

- **任何 agent 后端的实现。** Agent 被调度到采纳团队配置的后端实现。
- **Agent 间通信。** Agent 从不相互调用。状态机编排所有转换。
- **写操作。** 所有写入（创建、更新、删除、执行）都是确定性状态机转换。没有 agent 执行写入。
- **多 agent 辩论或投票。** 这是一个确定性框架，不是 agent 群体。一个 agent 处理一个意图。
- **Agent 生命周期或内存管理。** Agent 在每次调用中是无状态的。状态存储在 `AgentState` 中。

---

## 参考资料

- [高层设计](./01-deterministic-workflow-framework-design.md) — 父文档
- [意图分类设计](./04-intent-classification-design.md) — intent → agent 映射（§5.2）
- [RAG 接口](./20-rag-interface.md) — ReadOnlyAgent 的主要后端
- [状态机设计](./03-state-machine-design.md) — agent 调度和转换编排
- [工具生态系统](./13-tool-ecosystem.md) — 每个 agent 的工具允许列表
