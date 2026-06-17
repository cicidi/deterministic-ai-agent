# Chat History Storage Design

**Status:** Draft
**Scope:** Architecture discussion only. No implementation code.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial design: interface, data model, 6 read strategies, framework integration |
| 2026-06-17 | 0.2.0 | Layer 1 reads history for intent classification; write + read happen in parallel at entry |

---

## 1. Problem Statement

Enterprise chatbot conversations need history storage that supports multiple retrieval strategies — full history, sliding windows, time-based filtering, semantic search, and summarization — while keeping PII out of the history store. Storage backend must be abstract (interface-driven) so implementations can swap.

---

## 2. Concept Model

```
                         ┌──────────────────────────────┐
                         │     ChatHistory (Interface)    │
                         │                               │
                         │  write(message)                │
                         │  read(filter) -> [Message]     │
                         │  search(query) -> [Message]    │
                         │  get_summary() -> Summary      │
                         │  regenerate_summary()          │
                         └──────────────┬───────────────┘
                                        │ implements
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              PG 实现            PG+Redis 实现         PG+pgvector 实现
```

**Core principle:** write once (masked), read six ways. A single `HistoryFilter` expresses the retrieval strategy; backends interpret it.

---

## 3. Six Read Strategies

| Strategy | Filter | Use Case |
|----------|--------|----------|
| **Full History** | `HistoryFilter()` — no filter | Audit trail, compliance review |
| **Last N Turns** | `HistoryFilter(last_n_turns=5)` | LLM context window budget |
| **N Day** | `HistoryFilter(last_n_days=7)` | Recent conversation context |
| **Summary** | `get_summary(conv_id)` | Compressed history as system prompt prefix |
| **RAG** | `search(query, top_k=5)` | Semantic retrieval of relevant past exchanges |
| **Raw** | `read()` always returns raw masked messages | Direct message access |

---

## 4. Data Model

### 4.1 ChatMessage

> **PII 原则**: Chat history 只存脱敏内容。原始 PII 永不写入。
> Redaction 流程见 [Redaction Service Design](./2026-06-17-redaction-service-design.md)。

```python
@dataclass
class ChatMessage:
    id: str                          # UUID
    conversation_id: str             # LangGraph thread_id
    role: Literal["user", "assistant", "system", "tool"]
    content: str                     # 已脱敏，PII 替换为 <REDACT_k1>
    redaction_keys: list[str] | None # 关联 redaction vault，审计用
    token_count: int | None
    turn_number: int                 # user+assistant = 1 turn
    meta: dict                       # {"intent": "make_payment", "state": "collect_info", ...}
    created_at: datetime
```

| 字段 | 支持的能力 |
|------|-----------|
| `conversation_id` | Full history 按对话查询 |
| `turn_number` | Last N turns 按轮次过滤 |
| `created_at` | N day 按时间窗口过滤 |
| `content` | Raw 脱敏消息、LLM context、RAG embedding |
| `redaction_keys` | 审计时关联 vault，追溯涉及哪些敏感数据 |
| `token_count` | 上下文窗口预算计算 |
| `meta` | 挂 intent、state、tool_call 等业务标记 |

### 4.2 ConversationSummary

摘要独立存储，有生命周期（新消息到达后旧摘要作废，增量更新）。

```python
@dataclass
class ConversationSummary:
    conversation_id: str
    summary_text: str                # 基于脱敏内容生成
    summarized_until_turn: int
    summarized_until: datetime
    token_count: int
    created_at: datetime
    model: str                       # "gpt-4o" / "claude-3"
```

---

## 5. ChatHistory Interface

```python
class ChatHistory(ABC):
    @abstractmethod
    def write(self, message: ChatMessage) -> None: ...
    
    @abstractmethod
    def read(self, conversation_id: str, filter: HistoryFilter | None = None) -> list[ChatMessage]: ...
    
    @abstractmethod
    def get_summary(self, conversation_id: str) -> ConversationSummary | None: ...
    
    @abstractmethod
    def regenerate_summary(self, conversation_id: str) -> ConversationSummary: ...
    
    @abstractmethod
    def search(self, query: str, conversation_id: str, top_k: int = 5) -> list[ChatMessage]: ...

@dataclass
class HistoryFilter:
    last_n_turns: int | None = None
    last_n_days: int | None = None
    time_range: tuple[datetime, datetime] | None = None
    include_summary: bool = False       # prepend summary as system prompt prefix
```

---

## 6. Framework Integration

### 6.1 Data Flow

```
User Input (raw)
       │
       ▼
┌──────────────────────────────────────────────┐
│ Redaction Service                             │
│ raw → redaction_keys + masked_text            │
└──────────────────┬───────────────────────────┘
                   │ masked_text
       ┌───────────┴───────────────────────┐
       ▼                                   ▼
┌──────────────────────┐          ┌──────────────────┐
│ Layer 1: UNDERSTAND  │          │ ChatHistory      │
│                      │          │ .write(message)   │  ← 新消息同时存入
│ 1. ChatHistory       │◄─────────│                   │
│    .read(last_n_N)   │ 读历史   └──────────────────┘
│                      │
│ 2. Intent classify   │  ← 基于 last N turns 上下文分析 intent
│    + entity extract  │
└──────────┬───────────┘
           │ intent + entities
           ▼
┌──────────────────────┐
│ Layer 2: DECIDE      │
│                      │──── ChatHistory.read(filter)      ← 构建 LLM prompt context
│                      │──── ChatHistory.search(query)     ← RAG 检索相关历史
│                      │──── ChatHistory.get_summary()     ← 摘要注入 system prompt
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Layer 3: RESPOND     │
│                      │──── ChatHistory.write(response)   ← assistant 回复也存
└──────────────────────┘
```

### 6.2 Call Points

| Layer | Timing | Call | Purpose |
|-------|--------|------|---------|
| Entry | Message arrives | `RedactionService.redact(raw)` → `ChatHistory.write(masked)` | Redact PII, store masked message |
| **Layer 1** | **Before intent classify** | **`ChatHistory.read(conv_id, HistoryFilter(last_n_turns=N))`** | **读最近 N 轮历史作为 intent 分类上下文** |
| Layer 1 | After classify | Update `message.meta.intent` | 将分类结果写回消息 meta |
| Layer 2 | LLM node builds prompt | `ChatHistory.read(conv_id, filter)` | 按节点策略构建 context |
| Layer 2 | RAG enhancement | `ChatHistory.search(query, top_k=5)` | 语义检索相关历史 |
| Layer 2 | Summary injection | `ChatHistory.get_summary(conv_id)` | 摘要注入 system prompt |
| Layer 2 | New message triggers re-summary | `ChatHistory.regenerate_summary(conv_id)` | 增量更新摘要 |
| Layer 3 | Response generated | `ChatHistory.write(response)` | Store assistant reply |
| Audit | Compliance review | `ChatHistory.read()` + `RedactionService.reveal()` | Authorized PII reveal |

### 6.3 Layer 1 Intent Analysis Flow

```
User: "再把上次那张卡付了"

Layer 1 处理步骤:
  1. RedactionService.redact("再把上次那张卡付了")
     → masked: "再把上次那张 <REDACT_k1> 付了"

  2. ChatHistory.write(masked_message)     ← 新消息存入

  3. history = ChatHistory.read(            ← 读历史上下文
       conv_id,
       HistoryFilter(last_n_turns=3)
     )
     → [
         {role: "user", content: "查一下我的账单"},
         {role: "assistant", content: "您的账单共 4200 元，尾号 8891 的卡可支付"},
         {role: "user", content: "再把上次那张 <REDACT_k1> 付了"}
       ]

  4. LLM intent classify with history context:
     prompt: "Given conversation history, classify intent"
     result: intent=make_payment, entity={"card_token": "<REDACT_k1>"}
     → 上一轮提到了 "尾号 8891 的卡"，所以 "上次那张卡" = 尾号 8891

  5. message.meta["intent"] = "make_payment"    ← 写回 meta
```

### 6.4 Workflow YAML Extension

Each node declares its history policy in the YAML:

```yaml
states:
  - name: negotiate
    executor: llm
    prompt: "Negotiate payment with customer..."
    history_policy:
      strategy: last_n_turns           # last_n_turns | n_day | full | rag
      max_turns: 5
      include_summary: true
```

---

## 7. Reference Implementations

### 7.1 Summary — Mem0 Pattern

参考 [Mem0](https://github.com/mem0ai/mem0) 的 ADD-only extraction 模式：
- 每条新消息触发一次 LLM 调用，提取关键事实
- 只追加不覆盖，增量累积记忆
- 支持 temporal reasoning（时间感知检索）

### 7.2 RAG — Mem0 三路融合检索

参考 Mem0 的多信号检索：
- **Semantic**: 基于 embedding 向量的余弦相似度
- **BM25 Keyword**: 基于关键词的稀疏检索
- **Entity Matching**: 实体链接和关系匹配
- 三路分数融合后返回 top_k

### 7.3 Storage Backend Candidates

| Backend | Fit |
|---------|-----|
| PostgreSQL + pgvector | Vector search + transactional, same DB |
| PostgreSQL + Redis | Hot cache for context window, PG for persistence |
| PostgreSQL only | Simplest, pgvector for RAG |

---

## 8. Related Design Documents

- [Redaction Service Design](./2026-06-17-redaction-service-design.md) — PII detection and tokenization
- [Deterministic Workflow Framework Design](./2026-06-16-deterministic-workflow-framework-design.md) — Three-layer architecture overview
- [State Machine Design](./2026-06-16-state-machine-design.md) — FSM layer with LangGraph integration

---

## 9. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Summary regeneration trigger — on every message or batch periodically? | Deferred to implementation |
| 2 | Embedding model for RAG — OpenAI `text-embedding-3-small` or self-hosted? | Deferred to implementation |
| 3 | `token_count` estimation — server-side (tiktoken) or client-provided? | Deferred to implementation |
| 4 | History retention policy — configurable TTL per tenant? | Deferred to implementation |

---

## References

- [Mem0](https://github.com/mem0ai/mem0) — Universal memory layer for AI agents
- [LangGraph Checkpointer](https://langchain-ai.github.io/langgraph/how-tos/persistence/) — State persistence
- [pgvector](https://github.com/pgvector/pgvector) — Vector similarity search for PostgreSQL
