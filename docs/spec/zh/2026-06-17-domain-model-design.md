# Domain Model Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./01-deterministic-workflow-framework-design.md)
> Covers: Domain model as the single source of truth for entities, states, and transitions.
> **This spec defines schemas and interfaces — not a single solution.**

---

## 变更日志

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial domain model spec: Entity + State + Transition schema |
| 2026-06-17 | 0.2.0 | Add implementation options (flat vs nested vs code-first); agentState.phase mapping; errorNode as standard transition target |
| 2026-06-17 | 0.3.0 | Add Section 1.1: Implementation Approaches (Flat YAML vs Nested/Hierarchical vs Code-First) |
| 2026-06-18 | 0.5.0 | Adopt OpenAPI 3.1 Schema as the data model definition standard; replace custom FieldDef format with JSON Schema; add HomeInsurance/UserInfo/Address/QuoteRequest/QuoteResponse examples; add downstream API schema patterns | |

---

## 1. 角色定位

The Domain Model is the **single source of truth** for a deterministic workflow. It defines *what* the workflow operates on — data entities, valid states, and transition rules — independent of *how* the framework executes extraction, validation, or routing.

```
Domain Model (WHAT)               Workflow Config (HOW)
────────────────────────          ──────────────────────
Entities + fields + types         extraction_strategy
States + state_hint                validate_strategy
Transitions + guards              transform_strategy
                                   context_window_size
                                   max_transform_attempts
                                   on_transform_failure
```

**Separation principle:** The Domain Model is reusable across workflows and products. The workflow configuration adds runtime strategy selection on top. This separation enables:

1. **Cross-workflow reuse** — `PropertyInfo` schema（位于 `HomeInsurance` 内）同时用于 `home_insurance_quote` 和 `home_insurance_refinance`
2. **Product-agnostic models** — same domain model across different implementations
3. **Skill-driven generation** — a downstream skill can interview a developer to fill in the domain model, then the framework provides sensible defaults for the how

### 1.1 实现方案

领域实体使用 [OpenAPI 3.1 Schema Objects](https://spec.openapis.org/oas/latest.html#schema-object) (JSON Schema 方言)，行业标准格式，具备完整生态支持——校验器、代码生成器、IDE 自动补全、Swagger UI。框架直接读取 `components/schemas/`，无需翻译层。`$ref` 实现 schema 组合且无重复，下游 API 合约与领域实体使用相同格式定义。完整具体示例见 [Section 2.2](#22-完整示例--住房保险) 或 [home-insurance.yaml](../../domain-models/home-insurance.yaml)。



## 2. 领域模型 Schema

A Domain Model is defined in an OpenAPI 3.1-compliant YAML file:

**Top-level structure:**

```yaml
openapi: "3.1.0"

info:
  title: <domain name>        # e.g., "Home Insurance Domain Model"
  version: <semantic version>
  description: <human-readable domain description>

components:
  schemas:                    # ⇐ entity definitions (OpenAPI Schema Objects)
    EntityName:
      type: object
      required: [field1, field2]
      properties:
        field1: { type: string, ... }
        field2:
          $ref: "#/components/schemas/OtherEntity"  # cross-reference

  x-state-bindings:           # ⇐ framework extension: maps states to entities
    state_name:
      entity: <schema_ref>    # which entity this state collects
      fields: [field1, ...]   # fields active in this state (subset)
      state_hint: <prompt>    # LLM context for extraction
```

**Framework consumes:**
- `components/schemas/` → auto-generate extraction rules, validation rules, LLM structured output schemas
- `$ref` → resolve referenced schemas, expand compound fields into flat extraction targets
- `x-state-bindings` → per-state field visibility, state-specific LLM prompts

### 2.1 File Location

```
docs/domain-models/
  home-insurance.yaml          # Primary: HomeInsurance, UserInfo, Address, QuoteRequest, etc.
```

For the complete concrete example, see [home-insurance.yaml](../../domain-models/home-insurance.yaml).

### 2.2 完整示例 — 住房保险

上述 schema 实例化为如下具体领域模型：

```yaml
# domain-models/home-insurance.yaml — OpenAPI components/schemas
components:
  schemas:
    Address:
      type: object
      required: [street, city, province, postal_code]
      properties:
        street:
          type: string
          minLength: 3
        city:
          type: string
        province:
          type: string
          enum: [ON, QC, BC, AB, MB, SK, NS, NB, NL, PE, NT, YT, NU]
        postal_code:
          type: string
          pattern: "^[A-Za-z][0-9][A-Za-z] ?[0-9][A-Za-z][0-9]$"

    UserInfo:
      type: object
      required: [first_name, last_name, email]
      properties:
        first_name: { type: string, minLength: 1 }
        last_name:  { type: string, minLength: 1 }
        email:      { type: string, format: email }
        phone:      { type: string, pattern: "^\\+?1?\\d{10}$" }
        date_of_birth: { type: string, format: date }

    HomeInsurance:
      description: "Complete home insurance application"
      type: object
      required: [owner, home_address, property_info, coverage_info]
      properties:
        owner:
          $ref: "#/components/schemas/UserInfo"
        home_address:
          $ref: "#/components/schemas/Address"
        property_info:
          $ref: "#/components/schemas/PropertyInfo"
        coverage_info:
          $ref: "#/components/schemas/CoverageInfo"

    QuoteRequest:
      description: "Downstream API request for submitting a quote"
      type: object
      required: [applicant, property, coverage, quote_id]
      properties:
        quote_id:  { type: string, format: uuid }
        applicant: { $ref: "#/components/schemas/UserInfo" }
        property:
          type: object
          required: [address, property_info]
          properties:
            address: { $ref: "#/components/schemas/Address" }
            property_info: { $ref: "#/components/schemas/PropertyInfo" }
        coverage:  { $ref: "#/components/schemas/CoverageInfo" }
        requested_at: { type: string, format: date-time }

  # 框架状态绑定
  x-state-bindings:
    collect_policyholder_info:
      entity: HomeInsurance
      fields: [owner]
    collect_property_address:
      entity: HomeInsurance
      fields: [home_address]
    submit_quote:
      entity: QuoteRequest
```

---

## 3. 实体定义

实体是定义在 `components/schemas/` 下的 OpenAPI 3.1 Schema Object。框架直接消费标准 JSON Schema 关键词——`type`、`required`、`enum`、`pattern`、`minLength`/`maxLength`、`minimum`/`maximum`、`format`、`description`、`$ref`——并据此自动生成 ExtractionRule、ValidationRule 和 TransformRule。

JSON Schema 未覆盖的框架特有行为通过 `x-` 前缀扩展添加：

```yaml
# OpenAPI Schema Object 与框架扩展
property_type:
  type: string
  enum: [apartment, house, villa]
  description: "Type of property being insured"
  x-fallback:                         # 框架：确定性提取回退
    keywords: [apartment, house, villa, condo, flat]
    regex: null
    priority: llm_wins
  x-transform:                        # 框架：类型转换管道
    - op: normalize
      config: { to: lowercase }
    - op: lookup
      config:
        mapping:
          condo: apartment
          flat: apartment
  x-examples:                         # 框架：注入 LLM 提取 prompt 的 few-shot 示例
    - "I live in a house"
    - "3-bedroom apartment"
```

| 扩展 | 用途 |
|------|------|
| `x-fallback` | LLM 置信度不足时的确定性提取回退：`{ keywords?: string[], regex?: string, priority: "llm_wins" \| "regex_wins" }` |
| `x-transform` | 类型强制转换/规范化管道：`[{ op: "cast" \| "normalize" \| "parse" \| "lookup" \| "default" \| "external", config: object }]` |
| `x-examples` | 注入 LLM 提取 prompt 的 few-shot 示例：`string[]` |

其他所有校验（类型检查、枚举匹配、正则 pattern、长度/范围检查）均从实体的标准 JSON Schema 关键词直接派生——框架无需为其额外配置。

---

## 4. 状态定义

### 4.1 StateDef Schema

```
StateDef {
  name:         string    // state name (e.g., "collect_home_insurance")
  description:  string    // human-readable description of what this state expects
  entity:       string    // which entity this state extracts (references a schema name under components/schemas/)
  state_hint:   string    // disambiguation hint injected into LLM extraction prompt
  max_retries?: int       // max retries before escalating (default: from framework config)
}
```

### 4.2 State → Entity Binding

每个 State 绑定到恰好一个 Entity（一个 OpenAPI Schema Object）。框架使用此绑定来：

1. 读取实体的 JSON Schema `properties` → 生成 `ExtractionRule[]`（从 `type`、`description`、`x-fallback`、`x-examples`）
2. 生成 `ValidationRule[]`（从 `required`、`type`、`pattern`、`enum`、`minLength`/`maxLength`、`minimum`/`maximum`）
3. 生成 `TransformRule[]`（从 `x-transform`）
4. 在该状态下提取数据时，将 `state_hint` 注入 LLM prompt

### 4.3 Example

```yaml
states:
  collect_home_insurance:
    description: "Collect property details from the user"
    entity: HomeInsurance
    state_hint: >
      The user is providing property information for a home insurance quote.
      Address may include street, city, province, postal code.
      Building age is in years. "Brand new" or "newly built" means age 0.

  collect_coverage_needs:
    description: "Collect coverage preferences"
    entity: coverage_needs
    state_hint: >
      The user is choosing coverage type and amount.
      Deductible options: low (500 CNY), standard (2000 CNY), high (5000 CNY).

  file_claim:
    description: "File a new claim"
    entity: claim_details
    state_hint: >
      The user is reporting an incident for a claim.
      Incident type must be one of: fire, water_damage, theft, natural_disaster, other.
      Date should be in YYYY-MM-DD format.
```

### 4.4 State Name → agentState.phase Mapping

At runtime, the framework maps each `StateDef.name` to the `agentState.phase` field on the shared state object. This mapping is direct and automatic:

```
# Domain model state definition
states:
  collect_home_insurance:
    ...

# Runtime behavior
agentState.phase = "collect_home_insurance"
```

The `agentState.phase` value is used by:
- **LangGraph conditional edges** — route to the correct node based on current phase
- **Sub-workflow dispatch** — match the current phase to a sub-workflow handler
- **Audit/logging** — record which phase the conversation is in at each step
- **Resumption** — when resuming a conversation, the stored phase determines which state to re-enter

No explicit mapping configuration is needed. The framework derives the phase value from `StateDef.name` during domain model loading (step 3 of the framework consumption flow).

---

## 5. 转移定义

### 5.1 TransitionDef Schema

```
TransitionDef {
  from:      string    // source state name
  to:        string    // target state name
  guard:     string    // guard expression (see Section 6)
  priority?: int       // higher = checked first (for conflict resolution)
  label?:    string    // optional label for documentation / conditional edge naming
}
```

### 5.2 Transition Semantics

- **Self-loop**: `from: collect_home_insurance, to: collect_home_insurance, guard: "context_incomplete"` — stay in current state until all required fields are filled
- **Advance**: `from: collect_home_insurance, to: assess_risk, guard: "property_type != null AND address != null AND building_age != null"` — move forward when entity fields are complete
- **Conditional branch**: multiple transitions from the same state with non-overlapping guards decide the next state

### 5.3 Conflict Resolution

When multiple transitions from the same state have guards that could both be true:

1. **Priority ordering** — higher `priority` value is checked first
2. **First-match wins** — the first guard that evaluates true determines the transition
3. **Unreachable fallback** — if all guards fail, the framework uses the `on_nomatch` transition (explicitly defined or `on_transform_failure` node)

### 5.4 Example

```yaml
transitions:
  # Quote flow
  - from: collect_home_insurance
    to: collect_coverage_needs
    guard: "property_type != null AND address != null AND building_age != null"
    label: "home_insurance_complete"
    priority: 10

  - from: collect_home_insurance
    to: collect_home_insurance
    guard: "context_incomplete"
    label: "still_collecting"
    priority: 5

  - from: collect_coverage_needs
    to: assess_risk
    guard: "coverage_type != null AND building_coverage != null"
    label: "coverage_needs_complete"

  - from: collect_coverage_needs
    to: collect_coverage_needs
    guard: "context_incomplete"

  # Claim flow
  - from: file_claim
    to: validate_claim
    guard: "incident_type != null AND incident_date != null AND estimated_loss != null"

  - from: file_claim
    to: file_claim
    guard: "context_incomplete"
```

### 5.5 Reserved Transition Target: `errorNode`

The transition target name `errorNode` is reserved for error handling. Behavior:

- **Always reachable**: Any state can transition to `errorNode` regardless of its explicit transition allowlist. No transition rule with `to: errorNode` needs to be declared in the domain model.
- **Automatic routing**: When extraction, validation, or transformation fails and retries are exhausted, the framework automatically routes the conversation to the `errorNode`.
- **Escalation path**: The `errorNode` serves as a catch-all escalation path. It can be configured per-workflow (e.g., hand off to a human agent, log the failure, terminate gracefully).
- **Do not declare**: Do not declare `errorNode` as a state in the domain model. It is a framework-level primitive, not a domain state.

```yaml
# NO need to declare this in transitions:
# transitions:
#   - from: collect_home_insurance
#     to: errorNode       # ← NOT needed; errorNode is always reachable
```

The `errorNode` is resolved by the framework (step 6 of the consumption flow) and injected into the LangGraph state machine alongside the domain-defined states.

---

## 6. 守卫表达式语法

Guards are boolean expressions evaluated against the current entity state. The **authoritative guard expression syntax** — including boolean operators, comparison operators, list membership, null checks, framework-generated meta-variables, and natural language fallback — is defined in [State Machine Design §3.4 Guard Expression Syntax](./03-state-machine-design.md).

The domain model uses guards in `TransitionDef` entries to determine which state the workflow enters next. The framework evaluates guards at runtime using the state machine's expression evaluator. For complex business rules, guards can delegate to custom guard functions or rule engines (see State Machine Design §3.4).

---

## 7. 与 Workflow YAML 的关系

### 7.1 Merge Strategy

At framework startup, the domain model and workflow config are merged:

```
Domain Model (entity/state/transition schemas)
         +
Workflow Config (strategy choices, runtime params)
         ↓
Framework resolves to concrete ExtractionNode / ValidateNode / TransformNode instances
```

### 7.2 What the Workflow Config Adds

| Configured By | Domain Model | Workflow Config |
|---------------|-------------|-----------------|
| Entity field schemas | ✅ | — |
| State definitions | ✅ | — |
| Transition guards | ✅ | — |
| State hints | ✅ | — |
| Extraction strategy | — | ✅ |
| Validation strategy | — | ✅ |
| Transform strategy | — | ✅ |
| Rule engine selection | — | ✅ |
| Context window size | — | ✅ |
| Max transform attempts | — | ✅ |
| On-failure routing | — | ✅ |

### 7.3 Example: Referencing a Domain Model

```yaml
# workflow_home_insurance_quote.yaml
workflow: home_insurance_quote
domain_model: home-insurance        # loads docs/domain-models/home-insurance.yaml

nodes:
  collect_home_insurance_extract:
    entity: HomeInsurance
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    context_window_size: 6
    max_transform_attempts: 2
    on_transform_failure: ask_missing_home_insurance

  collect_coverage_needs_extract:
    entity: coverage_needs
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    on_transform_failure: ask_missing_coverage
```

---

## 8. 跨工作流复用

A domain model is globally registered. Multiple workflows can reference it, with different strategy configurations.

```
domain-models/home-insurance.yaml
    ├── workflow_home_insurance_quote.yaml     (extract_strategy: hybrid)
    ├── workflow_home_insurance_refinance.yaml  (extract_strategy: llm_primary)
    └── workflow_home_insurance_renewal.yaml    (extract_strategy: deterministic)
```

### 8.1 Versioning

Domain models use semantic versioning. Workflows pin to a version:

```yaml
domain_model: home-insurance@1.2.0
```

Breaking changes to entity schemas (field removal, type change) require a major version bump.

### 8.2 Namespacing

When two domain models define entities with the same name, the framework disambiguates by domain prefix:

```yaml
entity: home_insurance.HomeInsurance
```

---

## 9. 框架消费流程

When the framework loads a workflow that references a domain model:

```
1. Load domain model YAML → parse entities, states, transitions
2. Load workflow YAML → parse nodes, strategy configs
3. For each state → look up bound entity → expand OpenAPI Schema Object properties to:
   a. ExtractionRule[]  (from field name, type, description, x-fallback, x-examples)
   b. ValidationRule[]  (from required, type, pattern, enum, minLength/maxLength, minimum/maximum)
   c. TransformRule[]   (from x-transform)
4. Merge with node-level overrides (context_window_size, max_transform_attempts, etc.)
5. Instantiate Extract / Validate / Transform nodes via ExtractionFactory(strategy)
6. Generate LangGraph nodes + conditional edges from transition definitions
```

### 9.1 Entity → Rules Expansion

The framework performs automatic expansion. For example, given the `property_type` property in the OpenAPI schema:

```yaml
# Domain model entity field (OpenAPI Schema Object + x- extensions)
property_type:
  type: string
  enum: [apartment, house, villa]
  description: "Type of property"
  x-fallback:
    keywords: [apartment, house, villa, condo, flat]
  x-transform:
    - op: normalize
      config: { to: lowercase }
    - op: lookup
      config:
        mapping:
          condo: apartment
          flat: apartment
```

The framework auto-generates:

```
ExtractionRule {
  field: "property_type"
  type: "string"
  description: "Type of property (apartment, house, villa)"
  fallback_keywords: ["apartment", "house", "villa", "condo", "flat"]
}

ValidationRule {
  field: "property_type"
  type: "string"
  required: true
  enum: ["apartment", "house", "villa"]
}

TransformRule {
  field: "property_type"
  rules: [
    { op: "normalize", config: { to: "lowercase" } },
    { op: "lookup", config: { mapping: { condo: "apartment", flat: "apartment" } } }
  ]
}
```

---

## 10. 边界情况

### 10.1 Optional vs. Required Fields

Fields marked `required: false` are extracted and validated if present, but `context_complete` evaluates true even if they are null. Optional fields do not block state transition.

### 10.2 Cross-Entity Data

当状态收集 `CoverageInfo` 但转移守卫引用先前状态收集的 `PropertyInfo` 中的字段时，框架在所有实体的累积 `collectedFields` 上评估守卫。这使得类似 `"building_age > 10 AND building_coverage > 500000"` 的守卫成为可能。

### 10.3 Dynamic Entity Selection

For scenarios where the entity schema depends on a prior decision (e.g., auto vs home insurance), use two-stage domain models:

```yaml
# Stage 1 entity
insurance_type:
  fields:
    product_type:
      type: enum
      values: [auto, home, life]
      required: true

# Stage 2 — dynamic entity binding
states:
  classify_product:
    entity: insurance_type  # Stage 1

  collect_property_details:
    entity: property_subtype_info   # Selected only if product_type == "home"

  collect_coverage_details:
    entity: coverage_info           # Selected after property details complete
```

The transition guard on the classify state determines which entity is used next:

```yaml
transitions:
  - from: classify_product
    to: collect_property_details
    guard: "product_type == 'home'"
  - from: collect_property_details
    to: collect_coverage_details
    guard: "context_complete"
```

---

## 11. 待决问题

| # | Question | Impact |
|---|----------|--------|
| 1 | Should entities support nested/compound fields (e.g., `address: { street, city, postal_code }`)? | Schema complexity |
| 2 | Should domain models support inheritance (e.g., `homeowner_policy extends base_policy`)? | Reuse granularity |
| 3 | For guard expressions — how much expressiveness before we defer to rule engines? | Language complexity vs. power |
| 4 | Should the domain model include computed fields (fields populated by code, not by user extraction)? | Entity purity |
| 5 | Cross-workflow entity references — should an entity in `home_insurance_quote` reference an entity in `home_insurance_claims`? | Modularity |
| 6 | Migration strategy when a domain model version changes while conversations are in-flight? | Deployment safety |

---

## 参考文献

- [High-Level Design](./01-deterministic-workflow-framework-design.md) — parent architecture document
- [Extraction Layer Design](./05-extraction-layer-design.md) — Extract/Validate/Transform interfaces
- [State Machine Design](./03-state-machine-design.md) — guard expression base, intent+state resolution
- [Home Insurance Workflow](../../examples/home-insurance/workflow.yaml) — reference domain model instantiation
- zelkim/langgraph-insurance-chatbot — two-stage dynamic entity selection (auto vs home vs life)
