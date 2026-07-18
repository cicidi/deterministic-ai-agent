# 提取层规范

> 隶属于 [确定性工作流框架 — 高层设计](./01-deterministic-workflow-framework-design.md)
> 覆盖范围：Layer 1（UNDERSTAND）中的实体提取、校验和转换。
> **本规范定义接口和替代实现策略 — 而非单一方案。**

---

## 变更日志

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始提取层规范：提取/校验/转换管线 |
| 2026-06-17 | 0.2.0 | 重构为接口优先：每个接口提供 2+ 种实现选项 |
| 2026-06-17 | 0.3.0 | 将 Python 代码块替换为 YAML schemas；在第 2.2 和 2.3 节添加 errorNode 交叉引用；在第 3.2 节添加 LLM JSON 守卫备注；在第 3.3 节 StateContext 中添加 agentState.phase |
| 2026-06-17 | 0.4.0 | 第 2.3 节：为提取/转换节点添加显式 LLM +1 额外重试规则；修复第 35 行的中文文本；第 4.2 节 Option B：将 Python 表达式替换为声明式谓词描述 |
| 2026-06-18 | 0.6.0 | 新增 §2.6 按状态限定提取范围：并行双 LLM 提取（LLM 1：当前 state scope；LLM 2：完整 OpenAPI schema），均在最后 3+3 消息窗口上运行；跨状态字段恢复需用户确认；冲突解决使用置信度矩阵 | |

---

## 1. 角色定位

Extraction answers: *"What specific data does the user provide?"*

Intent classification determines *what the user wants to do* (e.g., `get_quote`). Extraction pulls the structured data from the utterance — property type, address, coverage amount — and validates it before handing it to Layer 2 (DECIDE).

Extraction is the second half of Layer 1 (UNDERSTAND):

```
User Input
   |
   v
+------------------------------------+
| Layer 1: UNDERSTAND                |
|                                    |
|  Intent Classification (already designed) |
|       ↓                            |
|  Entity Extraction (this document)  |
|       Extract → Validate ← Transform|
+------------------------------------+
            |
            v
      Layer 2: DECIDE
```

## 2. 核心管线

### 2.1 三个接口

The extraction pipeline consists of three node interfaces. Each interface defines a contract; the implementation is chosen per deployment.

| 接口 | 职责 |
|-----------|----------------|
| **提取（Extract）** | 通过两个并行 LLM 调用（窄范围 + 宽范围）从用户话语中拉取原始实体，然后合并与冲突解决 |
| **校验（Validate）** | 按规则检查实体；生成通过/失败 + 错误信息 |
| **转换（Transform）** | 类型强制转换、规范化、数据补全/修正 |

### 2.2 流程

```
User Input ──→ [Extract] ──────────→ entities_raw
                  │                      │
                  ├─ LLM 1: 窄范围       │
                  │  (当前 state scope)   │  合并
                  │                      ├─→ 冲突解决
                  └─ LLM 2: 宽范围       │  (置信度矩阵)
                     (完整 schema)       │
                                         ↓
                                    [Validate] ──(全部通过)──→ 输出结果到 Layer 2
                                         │
                                      (失败)
                                         │
                                         ↓
                                    [Transform] ──(成功)──→ 回到 [Validate]
                                         │
                                      (失败: 重试耗尽或不可恢复错误)
                                         │
                                         ↓
                                    on_transform_failure node → 最终路由到 errorNode（见 Routing & Execution spec Section 6）
```

### 2.3 重试门控

每个提取节点声明 `max_transform_attempts`（默认：2）。Validate→Transform→Validate 循环最多运行该次数。**Extract 节点的两个并行 LLM 调用各自获得 +1 额外重试**（以补偿 LLM 的非确定性），与框架层面的"所有 LLM 节点 +1 重试"规则一致。非 LLM 节点严格重试 `max_transform_attempts` 次。最终一次尝试若 Validate 仍失败，管线路由到配置的 `on_transform_failure` 节点，最终进入 `errorNode`（见 Routing & Execution spec Section 6）。

### 2.4 图拓扑

三个接口在 LangGraph 中是**独立节点**——不是隐藏的宏节点。Extract 节点内部编排两个并行 LLM 调用，然后再输出到 Validate。

```yaml
nodes:
  - {step}_extract:
      sub_nodes:
        - {step}_extract_narrow   # LLM 1：当前 state scope
        - {step}_extract_broad     # LLM 2：完整 OpenAPI schema
      strategy: parallel           # 两者并发运行
      merge: confidence_based      # 按置信度矩阵解决冲突
  - {step}_validate
  - {step}_transform
  - {next_step}
  - {on_failure}

edges:
  {step}_extract    → {step}_validate
  {step}_validate   → {next_step}              (所有规则通过)
  {step}_validate   → {step}_transform         (任一规则失败)
  {step}_transform  → {step}_validate           (转换成功)
  {step}_transform  → {on_failure}              (转换失败)
```

### 2.5 按状态限定提取范围

The Extract node operates on a **per-state scope** — not the full domain model. The framework constructs the extraction scope from the domain model's `x-state-bindings`:

**Scope resolution:**

```
agentState.phase = "collect_property_address"
       │
       ▼
x-state-bindings[collect_property_address]:
  entity: HomeInsurance
  fields: [home_address]                     ← only this sub-schema
       │
       ▼
framework resolves $ref:
  home_address → #/components/schemas/Address
       │
       ▼
LLM 1 只接收 Address schema：
  { street, city, province, postal_code, country }
  5 个字段，而非 30+
```

**为什么不给 LLM 1 完整的 HomeInsurance schema（30+ 个字段）：**

| 方案 | Token 数 | 准确率 | 风险 |
|----------|--------|----------|------|
| 完整 schema（所有实体） | 高 | 低 | LLM 把 "Toronto" 映射到 email，把 phone 映射到 postal_code |
| 按状态限定范围（只给 address 字段） | 低 | 高 | LLM 明确知道只需提取 5 个字段，不会混淆 |

**并行双 LLM 提取算法：**

每个用户回话触发两个 LLM 调用，共享相同的输入窗口，使用不同的目标 schema：

```
User Input + 最近 3 个用户消息 + 最近 3 个 Agent 消息
    │
    ├──→ LLM 1：窄范围提取（并行）
    │      目标 schema：当前 state 的 x-state-bindings 字段
    │      目的：高精度提取当前步骤的字段
    │
    └──→ LLM 2：宽范围扫描（并行）
           目标 schema：完整 OpenAPI components/schemas/（所有实体、所有字段）
           目的：捕捞用户在对话中任何阶段提到的任何字段
```

```
Pass 1 (LLM 1)：聚焦提取 — 当前 state scope
  输入：最近 3 user + 3 agent 消息 + 当前 state 的 scope schema
  目标：当前 phase 的 x-state-bindings 字段
  输出：{ 匹配当前 scope 的已提取字段 }
  策略：LLM 只提取 scope 内的字段；忽略其他所有内容

Pass 1 (LLM 2)：宽范围扫描 — 全领域 scope（与 LLM 1 并行运行）
  输入：最近 3 user + 3 agent 消息 + 完整 OpenAPI components/schemas/
  目标：整个领域模型中所有实体的所有字段
  输出：{ candidate_fields } — 在最近窗口中找到的任何字段
  策略：LLM 以宽松 schema 扫描，接受部分/模糊匹配；
        捕获用户在错误顺序或当前阶段之前提到的字段

Pass 2：合并与冲突解决
  合并：LLM 1 输出 ∪ LLM 2 candidate_fields，按字段名去重
  
  冲突解决（同一个字段被两个 LLM 提取时）：
    每个字段携带对应 LLM 的置信度分数。
    
    ┌─ LLM 1 置信度 ≥ 0.7 且 LLM 1 置信度 ≥ LLM 2 置信度？
    │      → 采用 LLM 1 的值（窄范围更可靠）
    │
    ├─ LLM 1 置信度 < 0.7 且 LLM 2 置信度 > 0.7？
    │      → 采用 LLM 2 的值（宽范围捕获更好）
    │
    └─ 其他情况（两者都 < 0.7，或都 < 阈值）？
           → 标记为 UNRESOLVED，路由到 errorNode
    
    冲突解决矩阵：
    ┌─────────────────┬──────────────────────┬──────────────────────┐
    │                 │ LLM 2 ≥ 0.7           │ LLM 2 < 0.7          │
    ├─────────────────┼──────────────────────┼──────────────────────┤
    │ LLM 1 ≥ 0.7     │ 用 LLM 1（若 conf1   │ 用 LLM 1            │
    │                 │  ≥ conf2）或 LLM 2   │                      │
    ├─────────────────┼──────────────────────┼──────────────────────┤
    │ LLM 1 < 0.7     │ 用 LLM 2            │ UNRESOLVED → error   │
    └─────────────────┴──────────────────────┴──────────────────────┘
  
  确认（仅 LLM 2 独有字段）：
    仅被 LLM 2 发现（不在 LLM 1 输出中）的字段需要用户确认：
      "我注意到你之前提到你的手机号是 647-555-1234。这对吗？"
    → 用户确认 → 框架合并到 collectedFields
    → 用户纠正 → 框架以纠正值重新提取
  
  仅被 LLM 1 发现的字段（不在 LLM 2 输出中）直接接受
  — 在当前 state scope 中提取的字段无需确认。
```

**设计决策：**

| 决策 | 理由 |
|----------|-----------|
| LLM 1 仅使用当前 state scope | 防止跨字段混淆；最小化 token；高精度 |
| LLM 2 使用完整 OpenAPI schema | 捕获用户乱序提到的字段；从任何实体恢复数据 |
| 两个 LLM 并行运行 | 不增加延迟 — LLM 2 并发执行，非顺序等待 |
| 输入窗口：最近 3+3 消息 | 控制 token 成本；避免扫描完整历史 |
| LLM 2 使用宽松匹配 | 接受部分/模糊匹配；用户可能表达方式不同 |
| 冲突：两者高置信度时优先 LLM 1 | 窄范围更可靠；LLM 1 的聚焦 prompt 产生更优结果 |
| 冲突：LLM 1 不确定时回退到 LLM 2 | LLM 2 的宽扫描可能捕获 LLM 1 窄镜头遗漏的内容 |
| 两者低置信度 → errorNode | 绝不静默接受不确定数据；确定性安全 |
| LLM 1 独有字段直接接受无需确认 | 当前 state scope 内的字段是有目的地提取的——信任它们 |
| LLM 2 独有字段需用户确认 | 脱离上下文发现的字段可能被错误关联——与用户核实 |

因此，Extract 节点不是单一的 LLM 调用——它是由 domain model 的 `x-state-bindings` 驱动的**并行双 LLM 编排**，之后是合并、解决与确认步骤。

---

## 3. 提取（Extract）接口

Extract 节点**并行运行两个 LLM 调用**，然后通过基于置信度的冲突解决合并结果。

### 3.1 契约

```
Extract Narrow（LLM 1）：
  输入：
    user_input:           string              // 原始用户话语
    conversation_context: ContextWindow        // 最近 3 user + 3 agent 消息
    intent_payloads:      ClassifiedIntent[]    // 来自意图分类
    extraction_rules:     ExtractionRuleSchema[] // 仅当前 state 的 x-state-bindings 字段
    state_context:        StateContext          // FSM 状态名称 + 提示

  输出：
    result: ExtractionResult  // 窄范围提取的字段，带置信度分数

Extract Broad（LLM 2）— 并行运行：
  输入：
    user_input:           string              // 原始用户话语
    conversation_context: ContextWindow        // 同样的最近 3+3 窗口
    full_schema:          OpenAPISchema        // 所有实体的完整 components/schemas/
    state_context:        StateContext          // FSM 状态名称（用于上下文，不限定范围）

  输出：
    result: ExtractionResult  // 宽范围候选字段，带置信度分数

合并：
  两组结果的并集，按字段级别的置信度矩阵解决冲突（见 §2.5）
  → 包含合并后 payloads 的 ExtractionResult
```

```
ExtractionResult {
  msg_id:   string                      // 每条消息的唯一 ID（接收时自动生成）
  payloads: ExtractedIntentPayload[]    // 从 Narrow + Broad 合并而来，按置信度解决冲突
}
```

Extract 节点接收来自分类器的 `ClassifiedIntent[]`，并行运行两个 LLM，合并结果，生成类型化的 `ExtractedIntentPayload` 子类。每个 intent 通过 `INTENT_PAYLOAD_MAP` 映射到对应的 payload 类（见 Section 3.7）。

### 3.2 实现方案

#### Option A：LLM 结构化输出（推荐）

每次提取并行运行两个 LLM 调用——一个窄范围（当前 state 字段），一个宽范围（完整领域 schema）。结果通过基于置信度的冲突解决合并。

| 维度 | 详情 |
|--------|--------|
| 优势 | 处理多种表达方式；理解隐式引用；多轮感知；并行执行隐藏 LLM 2 延迟 |
| 劣势 | 每轮 2 倍 LLM 成本；非确定性；可能产生幻觉值 |
| 最佳场景 | 开放式表单、自由文本字段、模糊输入 |
| 依赖 | LLM 服务商（OpenAI、Anthropic、本地） |
| 回退 | LLM 失败时 → 返回低置信度的部分结果；合并仍以可用结果继续 |

**Prompt 构建：**
- LLM 1 系统 prompt：`extraction_rules` 描述 + `state_context.state_hint`（窄范围）
- LLM 2 系统 prompt：完整 OpenAPI `components/schemas/` + 宽松匹配指令（宽范围）
- 上下文：最近 3 user + 3 agent 消息（两者相同）
- 输出格式：JSON，每个字段格式为 `{ field_name: { value, confidence } }`
- Temperature：0
- **守卫机制**：所有基于 LLM 的提取输出均为 JSON。框架在结果进入提取管线之前强制执行输出验证守卫（schema 检查、字段存在性、类型强制转换）。

### 3.3 状态感知提示词

Regardless of implementation option, the Extract node receives `StateContext`:

```
StateContext {
  state_name:        string    // e.g., "collect_property_info"
  state_description: string    // what this state expects
  state_hint:        string    // disambiguation instruction from node metadata
  required_fields:   string[]  // list of field names
  phase:             string    // current agentState.phase (e.g., "collecting", "validating", "confirming")
}
```

Options B and C use state context to scope the fallback rules. Option A injects it into the LLM prompt.

### 3.4 Comparison Matrix

| Dimension | Option A (LLM-Primary) | Option B (Deterministic) | Option C (Hybrid) |
|-----------|----------------------|--------------------------|-------------------|
| Cost | $$$ (per-call LLM) | $ (free) | $$ (LLM + compute) |
| Latency | ~1-3s | <1ms | ~1-3s |
| Determinism | Low | High | Medium |
| Accuracy on free text | High | Low | High |
| Accuracy on structured fields | Medium | High | High |
| Maintenance | Prompt tuning | Regex maintenance | Both |
| Auditability | Partial (LLM reasoning) | Full | Partial |
| Deployment complexity | Low (LLM SDK) | Minimal (stdlib) | Medium |

### 3.5 ExtractedIntentPayload Schema

Every extract call produces an `ExtractionResult` containing typed `ExtractedIntentPayload` objects. Each intent maps to a subclass.

**Base class (Python dataclass):**

```python
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass
class ExtractedIntentPayload:
    msg_id: str = field(default_factory=lambda: uuid4().hex)
    intent: str = ""
    confidence: float = 0.0
```

**Payload subclasses:**

```python
@dataclass
class ConfirmIntentPayload(ExtractedIntentPayload):
    fields: dict[str, bool] = field(default_factory=dict)

@dataclass
class DeclineIntentPayload(ExtractedIntentPayload):
    fields: dict[str, bool] = field(default_factory=dict)

@dataclass
class ProvideInformationIntentPayload(ExtractedIntentPayload):
    field_values: dict[str, Any] = field(default_factory=dict)

@dataclass
class GetQuoteIntentPayload(ExtractedIntentPayload):
    field_values: dict[str, Any] = field(default_factory=dict)

@dataclass
class FileClaimIntentPayload(ExtractedIntentPayload):
    field_values: dict[str, Any] = field(default_factory=dict)
```

**ExtractionResult wrapper:**

```python
@dataclass
class ExtractionResult:
    msg_id: str
    payloads: list[ExtractedIntentPayload]
```

| Payload Class | Intent | Data Shape |
|--------------|--------|------------|
| `ConfirmIntentPayload` | `confirm` | `fields: dict[str, bool]` |
| `DeclineIntentPayload` | `decline` | `fields: dict[str, bool]` |
| `ProvideInformationIntentPayload` | `provide_information` | `field_values: dict[str, Any]` |
| `GetQuoteIntentPayload` | `get_quote` | `field_values: dict[str, Any]` |
| `FileClaimIntentPayload` | `file_claim` | `field_values: dict[str, Any]` |

Intents `ask_question` and `unrecognized_intent` skip extraction entirely and route directly to their respective Layer 3 nodes.

### 3.6 Payload Guardrail Validation

After the Extract node produces payloads, a guardrail validates each `field_values` or `fields` entry before handing off to the Validate node:

1. **Field name existence check** — every key must map to an actual field in the `AgentState` dataclass. This is analogous to Jackson `ObjectMapper` validating JSON keys against a POJO. The validation uses a whitelist derived from `AgentState.__dataclass_fields__`:

```python
VALID_AGENT_FIELDS: set[str] = {
    "policy_type", "property_type", "address", "postal_code",
    "building_age", "floor_area", "coverage_amount", "phone",
    "claim_type", "claim_description", ...
}

def validate_payload_fields(payload: ExtractedIntentPayload):
    data = getattr(payload, "fields", None) or getattr(payload, "field_values", {})
    for field_name, value in data.items():
        if field_name not in VALID_AGENT_FIELDS:
            raise GuardrailError(f"Unknown field '{field_name}' — not found in AgentState")
        if value is None or value == "":
            raise GuardrailError(f"Empty value for field '{field_name}'")
```

2. **Non-empty value check** — no field value may be `None`, `""`, or for boolean payloads, `False` is also treated as empty.

### 3.7 Intent → Payload Factory

The framework uses a dispatch map to instantiate the correct payload class for each intent:

```python
INTENT_PAYLOAD_MAP = {
    "confirm":              ConfirmIntentPayload,
    "decline":              DeclineIntentPayload,
    "provide_information":  ProvideInformationIntentPayload,
    "get_quote":            GetQuoteIntentPayload,
    "file_claim":           FileClaimIntentPayload,
}

def build_extraction_result(msg_id: str, intent_payloads: list) -> ExtractionResult:
    payloads = []
    for ip in intent_payloads:
        cls = INTENT_PAYLOAD_MAP.get(ip.intent)
        if cls is None:
            continue  # skip intents with no extraction (ask_question, unrecognized)
        payload = cls(msg_id=msg_id, intent=ip.intent, confidence=ip.confidence)
        payloads.append(payload)
    return ExtractionResult(msg_id=msg_id, payloads=payloads)
```

The LLM prompt must guide extraction so that:
1. Each intent in the input produces one `ExtractedIntentPayload`
2. Data fields belonging to different intents are placed in separate payloads
3. Multi-intent messages produce multiple payloads in a single `ExtractionResult`

**Multi-intent example:**

> User: "I want to file a claim, my phone is 123-456-7890"

```json
{
  "msg_id": "a1b2c3d4",
  "payloads": [
    {
      "intent": "file_claim",
      "confidence": 0.95,
      "field_values": {}
    },
    {
      "intent": "provide_information",
      "confidence": 0.88,
      "field_values": {"phone": "123-456-7890"}
    }
  ]
}
```

**Intent combination validation** (cross-reference): Before extraction proceeds, the intent classifier validates that incompatible complex intents are not combined in a single message (see Intent Classification spec Section 4.3).

---

## 4. 校验（Validate）接口

### 4.1 契约

```
Input:
  entities:         Map<string, any>     // values from Extract (strings) or Transform (typed)
  validation_rules: ValidationRuleSchema[] // per-field rules from node metadata

Output:
  passed:       boolean       // true if ALL rules pass
  field_errors: FieldError[]  // list of failures
```

```
FieldError {
  field:   string    // which field failed
  rule:    string    // which rule failed (e.g., "required", "type", "regex")
  message: string    // human-readable error
  value:   any       // the value that failed (for audit)
}
```

### 4.2 Rule Types (Declarative Schema)

These rule types are defined in the YAML declaration (Section 6) and are engine-agnostic. Each implementation option interprets the same schema.

| Rule | Signature | Description |
|------|-----------|-------------|
| `required` | `{ required: true }` | Field must be non-null and non-empty |
| `type` | `{ type: "int" \| "float" \| "string" \| "date" \| "boolean" \| "enum" }` | Value must match the given type |
| `enum` | `{ enum: [val1, val2, ...] }` | Value must be one of the listed options |
| `range` | `{ range: { min?: number, max?: number } }` | Numeric value within range |
| `regex` | `{ regex: "pattern" }` | String value must match pattern |
| `length` | `{ length: { min?: int, max?: int } }` | String length bounds |
| `custom` | `{ custom: "function_name" }` | User-provided validation function |

### 4.3 Implementation Options

#### Option A: Rule Engine — Forward Chaining (durable_rules / business-rules / pyknow)

Compile declarative YAML rules into a rule engine's native format. Execute as a forward-chaining ruleset against entity facts.

| Engine | Package | Best for |
|--------|---------|----------|
| `durable_rules` | `pip install durable-rules` | Forward-chaining, cross-field rules, when/then inference |
| `business_rules` | `pip install business-rules` | Lightweight, JSON/YAML-native, simple per-field rules |
| `pyknow` | `pip install pyknow` | Expert system with Fact/KnowledgeEngine model |

| Aspect | Detail |
|--------|--------|
| Strengths | Cross-field rules; state-dependent rules; rule composition |
| Weaknesses | Additional dependency; learning curve |
| Best for | Complex validation with field interdependencies |
| Configuration | `rule_engine: durable_rules` in node metadata |

### 4.4 Comparison Matrix

| Dimension | Option A (Rule Engine) | Option B (Predicate) | Option C (Pydantic) |
|-----------|----------------------|---------------------|---------------------|
| Cross-field rules | Yes (when/then) | No (manual) | Yes (root_validator) |
| State-dependent rules | Yes | No | No |
| External deps | 1 pip package | 0 | 1 pip package |
| Schema in YAML | Yes | Yes | No (code-only) |
| Dynamic schemas | Yes | Yes | Limited |
| Learning curve | Medium | Low | Low |
| Inference speed | Medium | Fast | Fast |

---

## 5. 转换（Transform）接口

### 5.1 契约

```
Input:
  entities:          Map<string, string>  // raw values from Extract
  validation_errors: FieldError[]         // which fields failed validation
  transform_rules:   TransformRuleSchema[] // per-field transform rules

Output:
  entities:         Map<string, any>     // transformed values
  success:          boolean              // false if any field is unrecoverable
  transform_errors: TransformError[]     // unrecoverable errors
```

### 5.2 转换操作类型

| Operation | Description | Example |
|-----------|-------------|---------|
| `cast` | Type coercion | `"12/27" → Date(2027-12-01)` |
| `normalize` | String cleaning | `trim`, `lowercase`, `strip_symbols` |
| `parse` | Named parser | `parse_date`, `parse_currency`, `parse_phone` |
| `lookup` | Value mapping | `"BJ" → "Beijing"` |
| `default` | Fallback value when null | `null → 0.0` |
| `llm_correct` | LLM-assisted correction of near-valid values | `"Nisaan" → "Nissan"` |
| `llm_complete` | LLM-assisted inference of missing fields | infer postal code from address |
| `external` | Call external API/service | postal code → city lookup |

### 5.3 实现方案

#### Option A: Declarative Rule Pipeline

Transform rules execute as an ordered pipeline per field. Purely deterministic (no LLM). Operations `cast`, `normalize`, `parse`, `lookup`, `default`, `external`.

| Aspect | Detail |
|--------|--------|
| Strengths | Deterministic; auditable; no LLM cost |
| Weaknesses | Cannot handle ambiguous or implicit data |
| Best for | Type coercion, normalization, lookup tables |
| Dependencies | None (or external API for `external` operations) |

---

## 6. 节点元数据 Schema

Each extraction node in the YAML carries its own `extraction_rules`, `validation_rules`, and `transform_rules`. These schemas are the **interface contract** consumed by all implementation options.

### 6.1 提取规则 Schema

```
ExtractionRuleSchema {
  field:              string              // field name
  description:        string              // guides LLM extraction
  type:               string              // expected type after transform
  required:           boolean             // triggers validation if null
  fallback_pattern?:  string              // regex for deterministic fallback
  fallback_keywords?: string[]            // keyword-triggered fallback
  examples?:          string[]            // few-shot examples for LLM prompt
}
```

### 6.2 校验规则 Schema

```
ValidationRuleSchema {
  field:     string                // field name
  required?: boolean
  type?:     "int" | "float" | "string" | "date" | "boolean" | "enum"
  enum?:     string[]
  range?:    { min?: number, max?: number }
  regex?:    string
  length?:   { min?: int, max?: int }
  custom?:   string                // registered function name
}
```

### 6.3 转换规则 Schema

```
TransformRuleSchema {
  field:  string              // field name
  rules:  TransformOperation[] // ordered list of operations
}

TransformOperation {
  type:   "cast" | "normalize" | "parse" | "lookup" | "default" | "llm_correct" | "llm_complete" | "external"
  config: Record<string, any>  // type-specific configuration
}
```

### 6.4 Full Node Example (YAML)

```yaml
extraction_nodes:
  collect_property_info_extract:
    extract_strategy: hybrid      # Option A: llm_primary | Option B: deterministic | Option C: hybrid
    validate_strategy: durable_rules  # Option A: durable_rules | business_rules | pyknow
                                      # Option B: native | Option C: pydantic
    transform_strategy: hybrid    # Option A: deterministic | Option B: llm_assisted | Option C: hybrid
    state_hint: >
      The user is providing property information for a home insurance quote.
      Address may include street, city, province, postal code.
      Building age is in years.
    context_window_size: 6
    max_transform_attempts: 2
    on_transform_failure: ask_missing_property_info

    extraction_rules:
      - field: property_type
        description: "Type of property (apartment, house, villa)"
        type: enum
        required: true
        fallback_keywords: [apartment, house, villa, condo, flat]
        examples: ["I live in a house", "a 3-bedroom apartment"]
      - field: postal_code
        description: "6-digit postal code"
        type: string
        required: true
        fallback_pattern: "\\b[0-9]{6}\\b"
      - field: building_age
        description: "Age of the building in years"
        type: int
        required: true
        examples: ["built in 2010", "15 years old"]
      - field: floor_area
        description: "Floor area in square meters"
        type: float
        required: false
        fallback_pattern: "\\b([0-9]+(?:\\.[0-9]+)?)\\s*(?:sqm|m2|square\\s*meters?)"

    validation_rules:
      property_type:
        required: true
        enum: [apartment, house, villa]
      postal_code:
        required: true
        regex: "^[0-9]{6}$"
      building_age:
        required: true
        type: int
        range: { min: 0, max: 200 }
      floor_area:
        type: float
        range: { min: 1, max: 100000 }

    transform_rules:
      property_type:
        - type: normalize
          config: { op: lowercase }
        - type: lookup
          config:
            mapping:
              condo: apartment
              flat: apartment
              "single family": house
      building_age:
        - type: cast
          config: { to: int }
        - type: llm_correct
          config:
            prompt: >
              Convert building age to integer years. "built in 2010" → current_year - 2010.
              "new" → 0. Current value: {value}
      floor_area:
        - type: cast
          config: { to: float }
```

### 6.5 Strategy Configuration Reference

```yaml
# Node-level strategy selection
extract_strategy:    llm_primary | deterministic | hybrid
validate_strategy:   durable_rules | business_rules | pyknow | native | pydantic
transform_strategy:  deterministic | llm_assisted | hybrid

# If rule engine selected, which one
rule_engine:   durable_rules | business_rules | pyknow   # only when validate_strategy = one of these

# Custom implementation
custom_engine:   my_package.MyEngine                      # user-provided RuleEngine implementation
```

---

## 7. 与意图分类集成

### 7.1 Layer 1 Data Flow

```
User Input
   |
   v
[Intent Classification]  →  ClassificationResult { intents: ClassifiedIntent[] }
   |
   v
[Intent Combination Validate]  →  rejects multiple complex intents (see Intent spec 4.3)
   |
   v
[State Machine]           →  determines which extraction node to activate
   |
   v
[Extract]                 →  ExtractionResult { msg_id, payloads: ExtractedIntentPayload[] }
   |                          (each intent → typed payload via INTENT_PAYLOAD_MAP)
   v
[Payload Guardrail]       →  fieldName existence check + non-empty check (Section 3.6)
   |
   v
[Validate]                →  entities_validated OR field_errors
   |
   v
[Transform] (conditional) →  entities_transformed (loop back to Validate)
   |
   v
Layer 2: DECIDE
```

### 7.2 Intent → Extraction Routing

1. **Intent gates the extraction node**: The state machine uses the primary intent label to select which extraction node to activate. `get_quote` routes to `collect_property_info_extract`; `file_claim` routes to `file_claim_extract`.

2. **Intent may skip extraction**: If the intent is `unrecognized_intent` or `ask_question`, extraction skips entirely and routes directly to a clarification or Q&A node.

3. **Multi-intent per message**: A single user message may carry multiple intents (e.g., `file_claim` + `provide_information`). The Extract node produces one `ExtractedIntentPayload` per intent. Simple intents (non-`complex`) may be combined freely; multiple complex intents in one message are rejected by the combination validator before extraction begins.

### 7.3 Design Decision: Why Separate Classify and Extract

**Decision:** Intent classification and entity extraction are separate nodes (two-stage), not a single combined LLM call.

**Rationale — accuracy over latency:**

| Metric | Two-Stage (separate) | Single-Stage (combined) |
|--------|---------------------|------------------------|
| **Accuracy** | High — each extract prompt only contains the schema for the matched intent(s) | Low — single prompt must include ALL intents' ALL field schemas, leading to cross-schema field confusion |
| **Cost** | 2x LLM calls | 1x LLM call |
| **Latency** | ~2x of single call | ~1x |

**Why accuracy wins:**

The extraction prompt must include field descriptions, validation rules, and few-shot examples for every field. In a combined call, the LLM faces the union of all schemas:

- `get_quote` has fields `{property_type, address, postal_code, building_age, floor_area}`
- `file_claim` has fields `{claim_type, damage_description, incident_date, incident_location}`
- `update_policy` has fields `{policy_number, coverage_amount, effective_date}`

A combined prompt containing all 3 schemas (~12+ fields) causes the LLM to:
1. Confuse field boundaries — extract `damage_description` into a `get_quote` payload
2. Miss narrow-schema fields amidst the noise
3. Produce ambiguous output for overlapping concept names ("address" could be property or incident)

Two stages eliminate this: classify first to scope the schema, extract with only that schema. Accuracy is the non-negotiable dimension — one wrong field can route the entire Layer 2 workflow incorrectly. The cost of an extra LLM call is negligible compared to the cost of a business-logic error.

**Future:** For small deployments with <5 intents and few fields, a `classify_and_extract_combined: true` configuration option may be added, but it is not the default.

---

## 8. 模式：两阶段提取（类型优先）

For scenarios where the extraction schema depends on a prior decision (e.g., auto vs home insurance):

```
Stage 1:
  [Extract(type_classifier)] → [Validate] → state_machine selects extraction schema

Stage 2:
  [Extract(type_specific_fields)] → [Validate] → [Transform] → [Validate]
```

This mirrors the zelkim two-phase dynamic schema pattern. Stage 1 uses a minimal extraction schema (type only). Stage 2 uses the schema scoped to the classified type.

Each stage is an independent extract/validate/transform pipeline with its own strategy configuration.

---

## 9. 边界情况

### 9.1 Partial Extraction

Extract returns some but not all required fields → Validate catches missing fields → Transform's `llm_complete` (Option B/C) may infer them. If unrecoverable → `on_transform_failure`.

### 9.2 Extraneous Information

User provides information for fields the current node does not request. Extract may still capture them. The framework stores extra data in the state graph for potential use by downstream nodes.

### 9.3 Field Value Correction Mid-Workflow

User corrects a previously filled field ("Wait, the address is not X, it's Y"). Conversation context in Extract captures the new value. The accumulated `collectedFields` is overwritten.

### 9.4 Ambiguous Values

When a raw value could map to multiple valid options (e.g., "basic" = `coverage_level` or `deductible`), the `state_hint` disambiguates. If ambiguity persists, Validate reports error → Transform corrects or fail node clarifies.

---

## 10. 待决问题

| # | Question | Impact |
|---|----------|--------|
| 1 | Should Transform maintain its own retry budget separate from `max_transform_attempts` for LLM-based operations? | Cost control |
| 2 | Should extraction results be cached per conversation turn to avoid re-extraction on replay/recovery? | Determinism, cost |
| 3 | For `llm_complete`, what's the acceptable inference boundary? Should it call external APIs to fill gaps? | Data accuracy, latency |
| 4 | Cross-field validation (e.g., `end_date > start_date`) — expressed in YAML schema or only via rule engine? | Rule expressiveness |
| 5 | Should the extracted + validated entities be persisted before Layer 2 consumes them? | Auditability, replay |
| 6 | LLM provider unavailable mid-extraction — fall back to Option B (deterministic) or queue? | Availability |
| 7 | Should the `ExtractionFactory` support fallback chains? (e.g., try Option C → if LLM timeout, fall back to Option B) | Resilience |

---

## 11. LLM 审计记录

Every LLM call within the extraction pipeline (and across the framework) produces an audit record. These records serve two purposes: (a) operational traceability — the raw input/output of every LLM interaction is persisted for debugging and compliance; (b) training data — accumulated records form a dataset for fine-tuning or eval improvement.

### 11.1 Audit Record Schema

```python
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class LLMAuditRecord:
    msg_id: str                  # from ExtractionResult.msg_id
    intent: str                  # which intent triggered this LLM call
    node: str                    # node name: extract / validate_llm / transform_llm / classify
    raw_input: str               # raw user message or serialized input payload
    llm_output: str              # raw JSON string returned by LLM
    parsed_result: dict          # JSON-parsed structured output
    timestamp: str               # ISO 8601 UTC
    model: str                   # e.g., "gpt-4o", "claude-sonnet-4"
    tokens_used: int             # total tokens consumed
```

### 11.2 Audit Flow

```
User Message
    │
    ├── msg_id generated (uuid4().hex)
    │
    ▼
[Intent Classification] ──(LLM call)──→ record to llm_audit
    │
    ▼
[Extract] ──(LLM call, per payload)──→ record to llm_audit
    │
    ▼
[Transform llm_correct/llm_complete] ──(LLM call)──→ record to llm_audit
```

Each LLM interaction is audited independently — one classification call + one extraction call per payload + any transform LLM calls all produce separate audit records under the same `msg_id`.

### 11.3 Storage

Audit records are persisted to the `llm_audit` table (or equivalent collection). The table is append-only and indexed by `msg_id` and `timestamp`.

| Field | Indexed | Purpose |
|-------|---------|---------|
| `msg_id` | Yes | Trace all LLM calls for a message |
| `timestamp` | Yes | Time-range queries |
| `intent` | Yes | Filter by intent type |
| `node` | Yes | Filter by pipeline stage |
| `raw_input` | No (blob) | Debugging, training data |
| `llm_output` | No (blob) | Debugging, training data |

### 11.4 Training Data Generation

The accumulated audit records serve as a labeled dataset:
- `raw_input` → user utterance
- `llm_output` → expected structured output (validated through guardrails)
- `intent` + `node` → task label

Periodic exports from `llm_audit` can feed into model fine-tuning pipelines or eval suite construction.

---

## 参考文献

- [高层设计](./01-deterministic-workflow-framework-design.md) — parent architecture document
- [Intent Classification Design](./04-intent-classification-design.md) — Layer 1 intent classification
- [State Machine Design](./03-state-machine-design.md) — state context injection, intent+state resolution
- [Home Insurance Workflow](../../examples/home-insurance/workflow.yaml) — reference extraction rules
- zelkim/langgraph-insurance-chatbot — two-phase dynamic schema + LLM-structured-output pattern
- Prodigal Payment Collection Agent — hybrid LLM + per-slot regex fallback pattern
