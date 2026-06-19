# Domain Model Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Domain model as the single source of truth for entities, states, and transitions.
> **This spec defines schemas and interfaces — not a single solution.**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial domain model spec: Entity + State + Transition schema |
| 2026-06-17 | 0.2.0 | Add implementation options (flat vs nested vs code-first); agentState.phase mapping; errorNode as standard transition target |
| 2026-06-17 | 0.3.0 | Add Section 1.1: Implementation Approaches (Flat YAML vs Nested/Hierarchical vs Code-First) |
| 2026-06-18 | 0.5.0 | Adopt OpenAPI 3.1 Schema as the data model definition standard; replace custom FieldDef format with JSON Schema; add HomeInsurance/UserInfo/Address/QuoteRequest/QuoteResponse examples; add downstream API schema patterns | |

---

## 1. Role

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

1. **Cross-workflow reuse** — a `lead` entity used in both `mortgage_lead_submission` and `mortgage_lead_refinance`
2. **Product-agnostic models** — same domain model across different implementations
3. **Skill-driven generation** — a downstream skill can interview a developer to fill in the domain model, then the framework provides sensible defaults for the how

### 1.1 Implementation Approach

Domain entities are defined using [OpenAPI 3.1 Schema Objects](https://spec.openapis.org/oas/latest.html#schema-object) (JSON Schema dialect), an industry-standard format with full ecosystem support — validators, code generators, IDE auto-complete, Swagger UI. The framework reads `components/schemas/` directly with no translation layer needed. `$ref` enables schema composition without duplication, and downstream API contracts are defined in the same format as domain entities. For a complete concrete example, see [Section 2.2](#22-complete-example--mortgage-lead) or [mortgage-lead.yaml](../../domain-models/mortgage-lead.yaml).

#### Alternative Schema Formats (Context)

| Format | Why Rejected |
|--------|-------------|
| Custom FieldDef (flat YAML) | No tooling ecosystem; no code generators; no standard validators |
| JSON Schema Draft 2020-12 | Less mature tooling than OpenAPI 3.1 subset; no native Swagger UI integration |
| Pydantic BaseModel | Python-only; not language-agnostic; would violate spec-first principle |
| OpenAPI 3.1 Schema Object | **Chosen** (AD 29) — industry standard, rich tooling, $ref composition, x- extensions |

## 2. Domain Model Schema

A Domain Model is defined in an OpenAPI 3.1-compliant YAML file:

**Top-level structure:**

```yaml
openapi: "3.1.0"

info:
  title: <domain name>        # e.g., "Mortgage Lead Domain Model"
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
  mortgage-lead.yaml          # Primary: MortgageLead, Borrower, Address, LeadSubmission, etc.
```

For the complete concrete example, see [mortgage-lead.yaml](../../domain-models/mortgage-lead.yaml).

### 2.2 Complete Example — Mortgage Lead

The schema above instantiates into a concrete domain model like this:

```yaml
# domain-models/mortgage-lead.yaml — OpenAPI components/schemas
components:
  schemas:
    Address:
      type: object
      required: [street, city, state, postal_code]
      properties:
        street:
          type: string
          minLength: 3
        city:
          type: string
        state:
          type: string
          enum: [CA, NY, TX, FL, IL, PA, OH, GA, NC, MI]
        postal_code:
          type: string
          pattern: "^[0-9]{5}(-[0-9]{4})?$"

    Borrower:
      type: object
      required: [first_name, last_name, email]
      properties:
        first_name: { type: string, minLength: 1 }
        last_name:  { type: string, minLength: 1 }
        email:      { type: string, format: email }
        phone:      { type: string, pattern: "^\\+?1?\\d{10}$" }
        date_of_birth: { type: string, format: date }

    MortgageLead:
      description: "Complete mortgage lead application"
      type: object
      required: [borrower, property_address, lead]
      properties:
        borrower:
          $ref: "#/components/schemas/Borrower"
        property_address:
          $ref: "#/components/schemas/Address"
        lead:
          $ref: "#/components/schemas/Lead"

    LeadSubmission:
      description: "Downstream API request for submitting a lead"
      type: object
      required: [applicant, property, lead, application_id]
      properties:
        application_id: { type: string, format: uuid }
        applicant: { $ref: "#/components/schemas/Borrower" }
        property:
          type: object
          required: [address]
          properties:
            address: { $ref: "#/components/schemas/Address" }
        lead: { $ref: "#/components/schemas/Lead" }
        requested_at: { type: string, format: date-time }

  # Framework state bindings
  x-state-bindings:
    collect_borrower_info:
      entity: MortgageLead
      fields: [borrower]
    collect_property_address:
      entity: MortgageLead
      fields: [property_address]
    submit_lead:
      entity: LeadSubmission
```

### 2.3 Advanced Schema Patterns

OpenAPI/JSON Schema provides composition and constraint keywords that produce richer, more precise schemas than flat field lists:

**Polymorphism (`oneOf` + `discriminator`) —** when a field's type depends on a runtime value:

```yaml
LoanScenario:
  type: object
  required: [scenario_type, details]
  properties:
    scenario_type:
      type: string
      enum: [rate_check, pre_approval, refinance]
    details:
      oneOf:
        - $ref: "#/components/schemas/RateCheckDetail"
        - $ref: "#/components/schemas/PreApprovalDetail"
        - $ref: "#/components/schemas/RefinanceDetail"
      discriminator:
        propertyName: scenario_type
        mapping:
          rate_check: "#/components/schemas/RateCheckDetail"
          pre_approval: "#/components/schemas/PreApprovalDetail"
          refinance: "#/components/schemas/RefinanceDetail"
```

**Composition (`allOf`) —** merge a base schema with extensions:

```yaml
LoanEstimate:
  allOf:
    - $ref: "#/components/schemas/LeadSubmission"
    - type: object
      required: [monthly_payment, annual_payment]
      properties:
        monthly_payment: { type: number, minimum: 0 }
        annual_payment:  { type: number, minimum: 0 }
```

**Conditional validation (`if`/`then`/`else`) —** validate one field based on another's value:

```yaml
Borrower:
  type: object
  required: [mortgage_product]
  properties:
    mortgage_product:
      type: string
      enum: [fixed, adjustable, interest_only]
    credit_score:
      type: integer
    interest_rate:
      type: number
  if:
    properties:
      mortgage_product:
        enum: [fixed, adjustable]
    required: [mortgage_product]
  then:
    required: [credit_score]
  if:
    properties:
      mortgage_product:
        enum: [adjustable, interest_only]
    required: [mortgage_product]
  then:
    required: [interest_rate]
```

**Arrays with constraints —** structured lists with size bounds, uniqueness, and item schema:

```yaml
QuoteHistory:
  type: object
  properties:
    prior_quotes:
      type: array
      minItems: 0
      maxItems: 50
      uniqueItems: true
      items:
        $ref: "#/components/schemas/PriorQuote"
  additionalProperties: false       # reject unknown fields
```

**Key patterns for the framework:**

| Pattern | Use Case |
|---------|----------|
| `oneOf` + `discriminator` | Entity subtype selection (rate check vs pre-approval vs refinance) |
| `allOf` | Extend a base entity with derived fields |
| `if`/`then`/`else` | Conditional required fields (only ask interest_rate when mortgage_product is `adjustable`) |
| `minItems`/`maxItems`/`uniqueItems` | Bounded lists (max 50 prior quotes, no duplicates) |
| `multipleOf` | Numeric step constraint (loan amount in $1000 increments) |
| `additionalProperties: false` | Strict schema — reject unrecognized LLM output fields |

---

## 3. Entity Definition

An Entity is an OpenAPI 3.1 Schema Object defined under `components/schemas/`. The framework consumes standard JSON Schema keywords directly — `type`, `required`, `enum`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, `format`, `description`, `$ref` — and generates ExtractionRule, ValidationRule, and TransformRule from them automatically.

**Every field must define two core parameters:**

| Parameter | JSON Schema Keyword | Purpose |
|-----------|---------------------|---------|
| **Required** | `required` (schema-level array) | Declares whether the field must be non-null; drives `context_complete` guard evaluation |
| **Regex** | `pattern` | Regex pattern for string validation; the primary deterministic validation rule |

A field without `required` defaults to optional (does not block transitions). A field without `pattern` has no regex validation — other JSON Schema keywords (`enum`, `minLength`, `minimum`/`maximum`) may still apply.

Framework-specific behavior that JSON Schema does not cover is added via `x-` prefixed extensions:

```yaml
# OpenAPI Schema Object with framework extensions
loan_purpose:
  type: string
  enum: [purchase, refinance, cash_out]
  description: "Purpose of the mortgage"
  x-fallback:                         # Framework: deterministic extraction fallback
    keywords: [purchase, refinance, cash_out, home_equity, new_home]
    regex: null
    priority: llm_wins
  x-transform:                        # Framework: type coercion pipeline
    - op: normalize
      config: { to: lowercase }
    - op: lookup
      config:
        mapping:
          home_equity: refinance
          new_home: purchase
  x-examples:                         # Framework: few-shot examples for LLM prompt
    - "I want to buy a new house"
    - "Looking to refinance my mortgage"
```

| Extension | Purpose |
|-----------|---------|
| `x-fallback` | Deterministic extraction fallback when LLM confidence is low: `{ keywords?: string[], regex?: string, priority: "llm_wins" \| "regex_wins" }` |
| `x-transform` | Type coercion / normalization pipeline: `[{ op: "cast" \| "normalize" \| "parse" \| "lookup" \| "default" \| "external", config: object }]` |
| `x-examples` | Few-shot examples injected into LLM extraction prompt: `string[]` |

All other validation (type checking, enum matching, pattern regex, length/range bounds) is derived directly from the entity's standard JSON Schema keywords — the framework needs no additional configuration for them.

The framework auto-generates ExtractionRule, ValidationRule, and TransformRule from each field. For example, given:

```yaml
loan_purpose:
  type: string
  enum: [purchase, refinance, cash_out]
  description: "Purpose of the mortgage"
  x-fallback:
    keywords: [purchase, refinance, cash_out, home_equity, new_home]
  x-transform:
    - op: normalize
      config: { to: lowercase }
    - op: lookup
      config:
        mapping:
          home_equity: refinance
          new_home: purchase
```

The framework produces:

```
ExtractionRule {
  field: "loan_purpose"
  type: "string"
  description: "Purpose of the mortgage (purchase, refinance, cash_out)"
  fallback_keywords: ["purchase", "refinance", "cash_out", "home_equity", "new_home"]
}

ValidationRule {
  field: "loan_purpose"
  type: "string"
  required: true
  enum: ["purchase", "refinance", "cash_out"]
}

TransformRule {
  field: "loan_purpose"
  rules: [
    { op: "normalize", config: { to: "lowercase" } },
    { op: "lookup", config: { mapping: { home_equity: "refinance", new_home: "purchase" } } }
  ]
}
```

---

## 4. State Definition

### 4.1 StateDef Schema

```
StateDef {
  name:         string    // state name (e.g., "collect_lead_purpose")
  description:  string    // human-readable description of what this state expects
  entity:       string    // which entity this state extracts (references a schema name under components/schemas/)
  state_hint:   string    // disambiguation hint injected into LLM extraction prompt
  max_retries?: int       // max retries before escalating (default: from framework config)
}
```

### 4.2 State → Entity Binding

Each state binds to exactly one entity (an OpenAPI Schema Object). The framework reads the entity's schema to auto-generate extraction, validation, and transform rules (see [Section 9 — Framework Consumption Flow](#9-framework-consumption-flow) for the full pipeline).

### 4.3 Example

```yaml
states:
  collect_lead_purpose:
    description: "Collect lead details from the user"
    entity: $ref: "#/components/schemas/Lead"
    state_hint: >
      The user is providing lead information for a mortgage application.
      Address may include street, city, state, postal code.
      Loan amount is in USD. "A little under a million" means ~950000.
    x-state-bindings:                # per-state extraction scope (see §3)
      loan_purpose: {}
      address: {}
      loan_amount: {}
      property_value: {}
      property_type: {}

  collect_financial_profile:
    description: "Collect borrower financial profile"
    entity: $ref: "#/components/schemas/Borrower"
    state_hint: >
      The user is providing financial information for a mortgage lead.
      Credit score tiers: excellent (750+), good (700-749), fair (650-699), poor (<650).
    x-state-bindings:
      mortgage_product: {}
      interest_rate: {}

  submit_lead:
    description: "Submit a new mortgage lead"
    entity: $ref: "#/components/schemas/QuoteDetails"
    state_hint: >
      The user is submitting a mortgage lead for distribution.
      Quote type must be one of: rate_check, pre_approval, full_underwrite.
      Desired close date should be in YYYY-MM-DD format.
    x-state-bindings:
      quote_type: {}
      rate_criteria: {}
      desired_close_date: {}
      property_use: {}
```

### 4.4 State Name → agentState.phase Mapping

At runtime, the framework maps each `StateDef.name` to the `agentState.phase` field on the shared state object. This mapping is direct and automatic:

```
# Domain model state definition
states:
  collect_lead_purpose:
    ...

# Runtime behavior
agentState.phase = "collect_lead_purpose"
```

The `agentState.phase` value is used by:
- **LangGraph conditional edges** — route to the correct node based on current phase
- **Sub-workflow dispatch** — match the current phase to a sub-workflow handler
- **Audit/logging** — record which phase the conversation is in at each step
- **Resumption** — when resuming a conversation, the stored phase determines which state to re-enter

No explicit mapping configuration is needed. The framework derives the phase value from `StateDef.name` during domain model loading (step 3 of the framework consumption flow).

---

## 5. Intent Model

The Intent Model defines the contract between **what the user says** (Layer 1 — NLU) and **what the system does** (Layer 2 — Routing). Every user utterance maps to an intent, which maps to an entry state.

### 5.1 IntentDef Schema

```yaml
intents:
  submit_mortgage_lead:
    name: submit_mortgage_lead
    description: "User wants to submit a mortgage lead"
    confidence_threshold: 0.7
    entry_state: collect_lead_purpose
    examples:
      - "I want to apply for a mortgage"
      - "How much can I borrow?"
      - "Get me a rate quote for my home"
    fallback_intent: general_inquiry

  check_rates:
    name: check_rates
    description: "User wants to check mortgage rates"
    confidence_threshold: 0.8
    entry_state: submit_lead
    examples:
      - "I want to see current mortgage rates"
      - "What's the best rate you can offer?"
    fallback_intent: general_inquiry

  general_inquiry:
    name: general_inquiry
    description: "General question not matching specific intents"
    confidence_threshold: 0.0
    entry_state: handle_general_inquiry
```

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Unique intent identifier |
| `description` | string | Guides LLM classification prompt |
| `confidence_threshold` | float (0.0–1.0) | Minimum confidence to match; below threshold → `fallback_intent` |
| `entry_state` | string | State the workflow enters when this intent matches |
| `examples` | string[] | Few-shot examples for LLM classification |
| `fallback_intent` | string | Intent to use when confidence is below threshold |

### 5.2 Intent → State Routing

The intent model is the **deterministic entry point** into the state machine:

```
User Input: "I want to apply for a mortgage"
    │
    ▼
Intent Classifier (Layer 1)
    │  confidence: 0.92 → submit_mortgage_lead
    │
    ▼
Route to entry_state: collect_lead_purpose
    │
    ▼
State Machine starts executing transitions from collect_lead_purpose
```

The framework uses `entry_state` to set `agentState.phase` on first turn, then transitions take over. If the classifier returns an intent below `confidence_threshold`, the framework routes to the `fallback_intent`'s `entry_state` instead.

### 5.3 Multi-Intent Sessions

A single conversation may match multiple intents over its lifetime:

```
Turn 1: "I want a mortgage"       → intent: submit_mortgage_lead  → state: collect_lead_purpose
Turn 2: "Also, I want to check rates"  → intent: check_rates      → state: submit_lead (re-routes)
```

When a new intent arrives mid-conversation, the framework evaluates whether to **re-route** (switch to new entry_state) or **continue** (stay in current state). The default behavior is to re-route unless the current state's transition rules explicitly prevent it.

---

## 6. Transition Definition

Transitions define valid paths between states. Guards are boolean expressions evaluated against the current entity state. The **authoritative guard expression syntax** is defined in [State Machine Design §3.4](./2026-06-16-state-machine-design.md).

### 6.1 TransitionDef Schema

```
TransitionDef {
  from:      string    // source state name
  to:        string    // target state name
  guard:     string    // guard expression (see Section 6)
  priority?: int       // higher = checked first (for conflict resolution)
  label?:    string    // optional label for documentation / conditional edge naming
}
```

### 6.2 Transition Semantics

- **Self-loop**: `from: collect_lead_purpose, to: collect_lead_purpose, guard: "context_incomplete"` — stay in current state until all required fields are filled
- **Advance**: `from: collect_lead_purpose, to: assign_lead, guard: "loan_purpose != null AND loan_amount != null AND state != null"` — move forward when entity fields are complete
- **Conditional branch**: multiple transitions from the same state with non-overlapping guards decide the next state

### 6.3 Conflict Resolution

When multiple transitions from the same state have guards that could both be true:

1. **Priority ordering** — higher `priority` value is checked first
2. **First-match wins** — the first guard that evaluates true determines the transition
3. **Unreachable fallback** — if all guards fail, the framework uses the `on_nomatch` transition (explicitly defined or `on_transform_failure` node)

### 6.4 Example

```yaml
transitions:
  # Lead flow
  - from: collect_lead_purpose
    to: collect_financial_profile
    guard: "loan_purpose != null AND loan_amount != null AND state != null"
    label: "lead_purpose_complete"
    priority: 10

  - from: collect_lead_purpose
    to: collect_lead_purpose
    guard: "context_incomplete"
    label: "still_collecting"
    priority: 5

  - from: collect_financial_profile
    to: assign_lead
    guard: "mortgage_product != null AND interest_rate != null"
    label: "financial_profile_complete"

  - from: collect_financial_profile
    to: collect_financial_profile
    guard: "context_incomplete"

  # Quote flow
  - from: submit_lead
    to: validate_lead
    guard: "quote_type != null AND desired_close_date != null AND estimated_loan_value != null"

  - from: submit_lead
    to: submit_lead
    guard: "context_incomplete"
```

### 6.5 Reserved Transition Target: `errorNode`

The transition target name `errorNode` is reserved for error handling. Behavior:

- **Always reachable**: Any state can transition to `errorNode` regardless of its explicit transition allowlist. No transition rule with `to: errorNode` needs to be declared in the domain model.
- **Automatic routing**: When extraction, validation, or transformation fails and retries are exhausted, the framework automatically routes the conversation to the `errorNode`.
- **Escalation path**: The `errorNode` serves as a catch-all escalation path. It can be configured per-workflow (e.g., hand off to a human agent, log the failure, terminate gracefully).
- **Do not declare**: Do not declare `errorNode` as a state in the domain model. It is a framework-level primitive, not a domain state.

```yaml
# NO need to declare this in transitions:
# transitions:
#   - from: collect_lead_purpose
#     to: errorNode       # ← NOT needed; errorNode is always reachable
```

The `errorNode` is resolved by the framework (step 6 of the consumption flow) and injected into the LangGraph state machine alongside the domain-defined states.

---

## 7. Relationship with Workflow YAML

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
# workflow_mortgage_lead_submission.yaml
workflow: mortgage_lead_submission
domain_model: mortgage-lead        # loads docs/domain-models/mortgage-lead.yaml

nodes:
  collect_lead_purpose_extract:
    entity: lead
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    context_window_size: 6
    max_transform_attempts: 2
    on_transform_failure: ask_missing_lead_info

  collect_financial_profile_extract:
    entity: borrower
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    on_transform_failure: ask_missing_financial
```

---

## 8. Cross-Workflow Reuse

A domain model is globally registered. Multiple workflows can reference it, with different strategy configurations.

```
domain-models/mortgage-lead.yaml
    ├── workflow_mortgage_lead_submission.yaml  (extract_strategy: hybrid)
    ├── workflow_mortgage_lead_refinance.yaml   (extract_strategy: llm_primary)
    └── workflow_mortgage_lead_renewal.yaml     (extract_strategy: deterministic)
```

### 8.1 Versioning

Domain models use semantic versioning. Workflows pin to a version:

```yaml
domain_model: mortgage-lead@1.2.0
```

Breaking changes to entity schemas (field removal, type change) require a major version bump.

### 8.2 Namespacing

When two domain models define entities with the same name, the framework disambiguates by domain prefix:

```yaml
entity: mortgage_lead.lead
```

---

## 9. Framework Consumption Flow

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

---

## 10. Persistence Schema

The Domain Model also defines what gets persisted — the runtime data structures consumed by checkpoint storage, audit logging, and code generation. These schemas live alongside business entities in `components/schemas/`.

### 10.1 AgentState

The shared state object persisted at every turn checkpoint:

```yaml
AgentState:
  type: object
  required: [conversation_id, user_id, phase, fieldTo, fieldExtractedList, collectedFields]
  properties:
    conversation_id:
      type: string
      format: uuid
    user_id:
      type: string
      description: "trace_id — same as user_id per tracing model"
    phase:
      type: string
      description: "Current state name (matches StateDef.name)"

    # --- Field → Entity routing ---
    fieldTo:
      type: object
      additionalProperties: { type: string }
      description: >
        Maps each field name to its target entity name.
        Derived from x-state-bindings at domain model load time.
        Example: { "street": "Address", "first_name": "Borrower",
                   "monthly_payment": "LeadSubmission" }

    # --- Extraction tracking ---
    fieldExtractedList:
      type: array
      items: { type: string }
      description: >
        List of field names that passed Extract → Validate → Transform
        successfully. Only fields in this list are written into
        collectedFields (the DomainModel entity).
        Fields that failed validation or transformation are NOT added here.

    # --- DomainModel entity values (successfully collected only) ---
    collectedFields:
      type: object
      additionalProperties: true
      description: >
        Accumulated field values that passed all three stages
        (Extract → Validate → Transform). Structured per-entity:
        { "Address": { "street": "123 Main", "city": "Toronto" },
          "Borrower": { "first_name": "Alice" } }
        This IS the DomainModel entity state — only verified values live here.

    lastIntent:
      type: string
      description: "Last classified intent name"
    intentConfidence:
      type: number
      minimum: 0
      maximum: 1
    turnNumber:
      type: integer
      minimum: 0
    lifecycleState:
      type: string
      enum: [created, active, paused, completed, abandoned, timeout, archived]
    createdAt:
      type: string
      format: date-time
    lastActiveAt:
      type: string
      format: date-time
```

**Key invariant:**

```
Extract → Validate → Transform passes for field X
  → X is added to fieldExtractedList
  → X's value is written into collected_fields[fieldTo[X]]
  → context_complete guard checks collected_fields[entity].required fields

Extract → Validate → Transform fails for field Y
  → Y is NOT added to fieldExtractedList
  → Y is NOT written into collected_fields
  → collected_fields is PARTIAL but always CORRECT
```

`collected_fields` is the single source of truth for what has been successfully collected. If a user provides address AND phone, but phone fails validation, only address is in `collected_fields` — the DomainModel entity never contains unverified data.

### 10.2 Checkpoint Record

LangGraph checkpoint enriched with domain metadata:

```yaml
Checkpoint:
  type: object
  required: [checkpoint_id, conversation_id, agent_state]
  properties:
    checkpoint_id:
      type: string
      format: uuid
    conversation_id:
      type: string
      format: uuid
    agent_state:
      $ref: "#/components/schemas/AgentState"
    context:
      type: object
      properties:
        extraction_result: { type: object }
        routing_decision:  { type: object }
        response_data:     { type: object }
    messages:
      type: array
      maxItems: 20
      items:
        $ref: "#/components/schemas/ConversationMessage"
    audit:
      type: object
      properties:
        state_transitions:
          type: array
          items:
            $ref: "#/components/schemas/LifecycleAuditEntry"
        llm_calls:
          type: array
          items:
            $ref: "#/components/schemas/LLMCallRecord"
```

### 10.3 Conversation History

```yaml
ConversationMessage:
  type: object
  required: [message_id, turn_number, role, content, timestamp]
  properties:
    message_id:
      type: string
    turn_number:
      type: integer
    role:
      type: string
      enum: [user, agent, system]
    content:
      type: string
      maxLength: 10000
    extracted:
      type: object
      description: "Fields extracted from this message (Layer 1 output)"
    intent:
      type: string
    confidence:
      type: number
    components:
      type: array
      description: "Widget components rendered in this message"
    masked:
      type: boolean
      description: "Whether PII was scrubbed before storage. The authoritative PII rules definition is in [Response Generation §8](./2026-06-17-response-generation-layer-design.md)."
    timestamp:
      type: string
      format: date-time
```

### 10.4 Audit Records

```yaml
LifecycleAuditEntry:
  type: object
  required: [timestamp, conversation_id, previous_state, new_state, trigger]
  properties:
    timestamp:      { type: string, format: date-time }
    conversation_id: { type: string }
    user_id:         { type: string }
    previous_state:  { type: string }
    new_state:       { type: string }
    trigger:         { type: string }
    turn_number:     { type: integer }
    checkpoint_id:   { type: string }

LLMCallRecord:
  type: object
  required: [timestamp, model, latency_ms, tokens_used]
  properties:
    timestamp:    { type: string, format: date-time }
    model:        { type: string }
    provider:     { type: string }
    latency_ms:   { type: integer }
    tokens_used:
      type: object
      properties:
        input:  { type: integer }
        output: { type: integer }
    schema_violation: { type: boolean }
    retry_attempt:    { type: integer }
```

### 10.5 Code Generation Contract

The framework consumes these schemas to generate:

| Generated Artifact | Source Schema |
|--------------------|--------------|
| `AgentState` Python dataclass / TypeScript interface | `AgentState` schema |
| `Checkpoint` serialization/deserialization code | `Checkpoint` schema |
| `ConversationMessage` DTO | `ConversationMessage` schema |
| Database migration (checkpoint store DDL) | `AgentState` + `Checkpoint` schemas |
| Audit log query API | `LifecycleAuditEntry` + `LLMCallRecord` schemas |
| Intent classifier training data format | `IntentDef` entries |

---

## 11. Edge Cases

### 11.1 Cross-Entity Data

When a state collects `borrower` but the transition guard references a field from `lead` (collected in a previous state), the framework evaluates the guard against the accumulated `collectedFields` across all entities. This enables guards like `"loan_amount <= 920000 AND state in licensed_states"`.

### 11.2 Dynamic Entity Selection

For scenarios where the entity schema depends on a prior decision (e.g., purchase vs refinance mortgage), use two-stage domain models:

```yaml
# Stage 1 entity
lead_type:
  fields:
    lead_type:
      type: enum
      values: [purchase, refinance, cash_out]
      required: true

# Stage 2 — dynamic entity binding
states:
  classify_lead:
    entity: lead_type  # Stage 1

  collect_lead_details:
    entity: lead   # Selected only if lead_type == "purchase"

  collect_financial_profile:
    entity: borrower           # Selected after lead details complete
```

The transition guard on the classify state determines which entity is used next:

```yaml
transitions:
  - from: classify_lead
    to: collect_lead_details
    guard: "lead_type == 'purchase'"
  - from: collect_lead_details
    to: collect_financial_profile
    guard: "context_complete"
```

---

## 12. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should entities support nested/compound fields (e.g., `address: { street, city, postal_code }`)? | Schema complexity |
| 2 | Should domain models support inheritance (e.g., `homeowner_policy extends base_policy`)? | Reuse granularity |
| 3 | For guard expressions — how much expressiveness before we defer to rule engines? | Language complexity vs. power |
| 4 | Should the domain model include computed fields (fields populated by code, not by user extraction)? | Entity purity |
| 5 | Cross-workflow entity references — should an entity in `mortgage_lead_submission` reference an entity in `mortgage_lead_claims`? | Modularity |
| 6 | Migration strategy when a domain model version changes while conversations are in-flight? | Deployment safety |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — parent architecture document
- [Extraction Layer Design](./2026-06-17-extraction-layer-design.md) — Extract/Validate/Transform interfaces
- [State Machine Design](./2026-06-16-state-machine-design.md) — guard expression base, intent+state resolution
- [Mortgage Lead Workflow](../../examples/mortgage-lead/workflow.yaml) — reference domain model instantiation
- zelkim/langgraph-insurance-chatbot — two-stage dynamic entity selection (auto vs home vs life)
