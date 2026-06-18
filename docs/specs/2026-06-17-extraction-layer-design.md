# Extraction Layer Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Entity extraction, validation, and transformation within Layer 1 (UNDERSTAND).
> **This spec defines interfaces and alternative implementation strategies — not a single solution.**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial extraction layer spec: Extract/Validate/Transform pipeline |
| 2026-06-17 | 0.2.0 | Refactor to interface-first: each interface with 2+ implementation options |
| 2026-06-17 | 0.3.0 | Replace Python code blocks with YAML schemas; add errorNode cross-reference in Sections 2.2 & 2.3; add LLM JSON guardrail note in Section 3.2; add agentState.phase to StateContext in Section 3.3 |
| 2026-06-17 | 0.4.0 | Section 2.3: add explicit LLM +1 extra retry rule for extract/transform nodes; fix Chinese text on line 35; Section 4.2 Option B: replace Python expressions with declarative predicate descriptions |

---

## 1. Role

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

## 2. Core Pipeline

### 2.1 Three Interfaces

The extraction pipeline consists of three node interfaces. Each interface defines a contract; the implementation is chosen per deployment.

| Interface | Responsibility |
|-----------|----------------|
| **Extract** | Pull raw entities from user utterance |
| **Validate** | Check entities against rules; produce pass/fail + errors |
| **Transform** | Type coercion, normalization, data completion/correction |

### 2.2 Flow

```
User Input ──→ [Extract] ──→ entities_raw
                  │
                  ↓
             [Validate] ──(all pass)──→ emit result to Layer 2
                  │
               (fail)
                  │
                  ↓
             [Transform] ──(success)──→ loop back to [Validate]
                  │
               (fail: max attempts exhausted or unrecoverable error)
                  │
                  ↓
             on_transform_failure node → ultimately routes to errorNode (see Routing & Execution spec Section 6)
```

### 2.3 Retry Gating

Each extraction node declares `max_transform_attempts` (default: 2). The Validate→Transform→Validate loop runs up to that limit. **LLM-based extraction and transform nodes receive +1 extra retry beyond `max_transform_attempts`** (to compensate for LLM non-determinism), matching the framework-wide rule that all LLM nodes get +1 retry. Non-LLM nodes retry exactly `max_transform_attempts` times. On the final attempt, if Validate still fails, the pipeline routes to the configured `on_transform_failure` node, which ultimately routes to `errorNode` (see Routing & Execution spec Section 6).

### 2.4 Graph Topology

The three interfaces are **independent nodes** in the LangGraph — not a hidden macro-node.

```yaml
nodes:
  - {step}_extract
  - {step}_validate
  - {step}_transform
  - {next_step}
  - {on_failure}

edges:
  {step}_extract    → {step}_validate
  {step}_validate   → {next_step}              (all rules pass)
  {step}_validate   → {step}_transform         (any rule fails)
  {step}_transform  → {step}_validate           (transform succeeded)
  {step}_transform  → {on_failure}              (transform failed)
```

### 2.5 Interface Definition

The framework exposes nodes through a strategy-based factory pattern. Each extraction node (extract / validate / transform) conforms to a shared contract:

```yaml
# Extraction Node Protocol (interface contract)
# Each node receives the full GraphState, returns updated GraphState.
# Nodes are stateless — all context lives in the state graph.
extraction_node_protocol:
  signature: (GraphState) → GraphState
  description: >
    Execute this node against the current LangGraph state.
    The node reads from and writes to the state graph.
    No side effects outside of state mutation.
```

The framework wires nodes into the graph via a factory configured per-node in YAML:

```yaml
# ExtractionFactory configuration (per-node in workflow YAML)
extraction_factory:
  # Strategy selection drives which implementation is instantiated
  extract_strategy: hybrid        # llm_primary | deterministic | hybrid
  validate_strategy: native       # durable_rules | business_rules | pyknow | native | pydantic
  transform_strategy: deterministic  # deterministic | llm_assisted | hybrid

  # Each factory method signature:
  #   create_extract(strategy: string, config: dict) → ExtractionNode
  #   create_validate(strategy: string, config: dict) → ExtractionNode
  #   create_transform(strategy: string, config: dict) → ExtractionNode
  #
  # The factory reads the strategy name and instantiates the corresponding
  # implementation class, passing the YAML `config` as constructor arguments.
```

---

## 3. Extract Interface

### 3.1 Contract

```
Input:
  user_input:           string              // raw user utterance
  conversation_context: ContextWindow        // last N messages
  extraction_rules:     ExtractionRuleSchema[] // what fields to look for
  state_context:        StateContext          // FSM state name + hint

Output:
  entities:   Map<string, string>  // field_name → raw extracted value
  source:     string               // which strategy produced the result
  confidence: float                // 0.0 - 1.0
  reasoning?: string               // extraction reasoning (audit trail)
```

### 3.2 Implementation Options

#### Option A: LLM-Primary — Structured Output (zelkim pattern)

Use LLM with structured output (JSON mode / function calling) to extract all fields at once. Relies on the LLM's natural language understanding to handle varied phrasings, multi-turn context, and implicit references.

| Aspect | Detail |
|--------|--------|
| Strengths | Handles varied phrasings; understands implicit references; multi-turn aware |
| Weaknesses | LLM cost/latency; non-deterministic; can hallucinate values |
| Best for | Open-ended forms, free-text fields, ambiguous inputs |
| Dependencies | LLM provider (OpenAI, Anthropic, local) |
| Fallback | On LLM failure → return partial results with lower confidence |

**Prompt construction:**
- System prompt: `extraction_rules` descriptions + `state_context.state_hint`
- Context: last N messages from `conversation_context`
- Output format: JSON with field_name → value, plus `reasoning`
- Temperature: 0
- **Guardrail**: All LLM-based extraction output is JSON. The framework enforces output validation guardrails (schema check, field presence, type coercion) before the result enters the extraction pipeline.

#### Option B: Keyword/Regex — Deterministic-Only (no LLM)

Extract entities using only deterministic pattern matching. No LLM call. Each field has a `fallback_pattern` (regex) or `fallback_keywords` (string list).

| Aspect | Detail |
|--------|--------|
| Strengths | Zero LLM cost; deterministic; fast; auditable |
| Weaknesses | Brittle on rephrasing; can't handle implicit references |
| Best for | Structured fields (postal code, phone, account ID); compliance-critical use cases |
| Dependencies | None (pure Python `re`) |
| Fallback | If no regex matches → field remains null |

#### Option C: Hybrid — LLM-First + Deterministic Fallback (Prodigal pattern)

LLM extracts first. Then for each field with a `fallback_pattern` or `fallback_keywords`, run deterministic extraction and merge results.

| Aspect | Detail |
|--------|--------|
| Strengths | Best of both: LLM handles ambiguity, regex guarantees precision on structured fields |
| Weaknesses | LLM cost; merge conflict resolution complexity |
| Best for | Regulated industries with mixed field types |
| Dependencies | LLM provider + rule engine |
| Conflict resolution | Configurable per field: `llm_wins` / `regex_wins` / `llm_unless_confidence_below` |

**Merge strategy (configurable per node):**

```
1. Try LLM extraction → entities_llm
2. For each field with deterministic fallback:
     run regex/keyword → entities_regex
3. Merge:
     complement:      entities_llm[field] ?? entities_regex[field]
     llm_wins:        entities_llm[field]   (ignore regex)
     regex_wins:      entities_regex[field] (ignore LLM)
```

### 3.3 State-Aware Prompting

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

---

## 4. Validate Interface

### 4.1 Contract

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

#### Option B: Pure Python Predicate Functions

Each rule type maps to a simple function. No external rule engine dependency. Rules are declared in YAML and evaluated by the framework's native predicate engine:

```yaml
# Native predicate rule definitions (engine evaluates per-field against these rules)
validation_rules:
  required:
    predicate: "value is non-null and non-empty"
  type:
    predicate: "Type match (int/float/string/date/boolean/enum)"
  enum:
    predicate: "value is one of the listed options"
  range:
    predicate: "value is within numeric range (min <= value <= max)"
  regex:
    predicate: "value matches the given regex pattern"
  length:
    predicate: "string length is within bounds (min <= length <= max)"
  custom:
    predicate: "user-provided validation function passes"
```

| Aspect | Detail |
|--------|--------|
| Strengths | Zero dependencies; simple; debuggable |
| Weaknesses | No cross-field rules; no inference; limited composability |
| Best for | Simple per-field checks; minimal deployments |
| Configuration | `rule_engine: native` in node metadata |

#### Option C: Schema Validator — Pydantic / dataclass

Define entities as structured schemas with built-in validators. The framework maps YAML declarations to type-safe validation models at runtime:

```yaml
# Schema declaration (maps to type-safe validator at runtime)
# The framework generates validation logic from this declaration.
schema:
  PropertyInfo:
    fields:
      property_type:
        type: enum
        allowed: [apartment, house, villa]
      address:
        type: string
        min_length: 5
      postal_code:
        type: string
        pattern: "^[0-9]{6}$"
      building_age:
        type: int
        range: { min: 0, max: 200 }
      floor_area:
        type: float
        range: { min: 1, max: 100000 }
        required: false
```

| Aspect | Detail |
|--------|--------|
| Strengths | Type-safe; IDE support; serialization built-in |
| Weaknesses | Schema is code (not YAML); cross-field validators are verbose; dynamic schemas harder |
| Best for | Python-native projects with known schemas at dev time |
| Configuration | `rule_engine: pydantic` in node metadata |

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

## 5. Transform Interface

### 5.1 Contract

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

### 5.2 Transform Operation Types

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

### 5.3 Implementation Options

#### Option A: Declarative Rule Pipeline

Transform rules execute as an ordered pipeline per field. Purely deterministic (no LLM). Operations `cast`, `normalize`, `parse`, `lookup`, `default`, `external`.

| Aspect | Detail |
|--------|--------|
| Strengths | Deterministic; auditable; no LLM cost |
| Weaknesses | Cannot handle ambiguous or implicit data |
| Best for | Type coercion, normalization, lookup tables |
| Dependencies | None (or external API for `external` operations) |

#### Option B: LLM-Assisted Transform

Transform uses LLM for `llm_correct` and `llm_complete` operations. Temperature = 0.

- **`llm_correct`**: The raw value is close but invalid (e.g., "Nisaan" → "Nissan"). The LLM receives the raw value + validation error + expected format.
- **`llm_complete`**: A field is null but inferrable from other fields + conversation context (e.g., street + city → postal code).

| Aspect | Detail |
|--------|--------|
| Strengths | Handles near-miss errors; can infer implicit data |
| Weaknesses | LLM cost/latency; non-deterministic |
| Best for | Free-text corrections, intelligent completion |
| Dependencies | LLM provider |

#### Option C: Hybrid — Rules Pipeline + LLM Fallback

Deterministic rules execute first. If they fail (unrecoverable), invoke LLM as a last resort.

Execution order:

```
1. cast → normalize → parse → lookup → default → external
2. If still invalid → llm_correct
3. If still null and required → llm_complete
```

| Aspect | Detail |
|--------|--------|
| Strengths | Combines determinism with LLM flexibility; LLM only invoked when needed |
| Weaknesses | More complex pipeline; LLM still has latency |
| Best for | Most production use cases |
| Dependencies | Rule engine + LLM provider |

### 5.4 Comparison Matrix

| Dimension | Option A (Deterministic) | Option B (LLM-Assisted) | Option C (Hybrid) |
|-----------|------------------------|------------------------|-------------------|
| Cost | $ | $$$ | $$ |
| Latency | <10ms | ~1-3s (LLM calls) | <10ms typical, ~1-3s fallback |
| Determinism | High | Low | Medium |
| Handling near-misses | Limited | Good | Good |
| Handling missing data | Default only | Inference | Default → inference |
| Complexity | Low | Low | Medium |
| Auditability | Full | Partial | Partial |

---

## 6. Node Metadata Schema

Each extraction node in the YAML carries its own `extraction_rules`, `validation_rules`, and `transform_rules`. These schemas are the **interface contract** consumed by all implementation options.

### 6.1 Extraction Rule Schema

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

### 6.2 Validation Rule Schema

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

### 6.3 Transform Rule Schema

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

## 7. Integration with Intent Classification

### 7.1 Layer 1 Data Flow

```
User Input
   |
   v
[Intent Classification]  →  intent_label, confidence, source
   |
   v
[State Machine]           →  determines which extraction node to activate
   |
   v
[Extract]                 →  entities_raw
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

1. **Intent gates the extraction node**: The state machine uses the intent label to select which extraction node to activate. `get_quote` routes to `collect_property_info_extract`; `file_claim` routes to `file_claim_extract`.

2. **Intent may skip extraction**: If the intent is `unrecognized_intent` or `ask_question`, extraction skips entirely and routes directly to a clarification or Q&A node.

---

## 8. Pattern: Two-Stage Extraction

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

## 9. Edge Cases

### 9.1 Partial Extraction

Extract returns some but not all required fields → Validate catches missing fields → Transform's `llm_complete` (Option B/C) may infer them. If unrecoverable → `on_transform_failure`.

### 9.2 Extraneous Information

User provides information for fields the current node does not request. Extract may still capture them. The framework stores extra data in the state graph for potential use by downstream nodes.

### 9.3 Field Value Correction Mid-Workflow

User corrects a previously filled field ("Wait, the address is not X, it's Y"). Conversation context in Extract captures the new value. The accumulated `collectedFields` is overwritten.

### 9.4 Ambiguous Values

When a raw value could map to multiple valid options (e.g., "basic" = `coverage_level` or `deductible`), the `state_hint` disambiguates. If ambiguity persists, Validate reports error → Transform corrects or fail node clarifies.

---

## 10. Open Questions

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

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — parent architecture document
- [Intent Classification Design](./2026-06-16-intent-classification-design.md) — Layer 1 intent classification
- [State Machine Design](./2026-06-16-state-machine-design.md) — state context injection, intent+state resolution
- [Home Insurance Workflow](../../examples/home-insurance/workflow.yaml) — reference extraction rules
- zelkim/langgraph-insurance-chatbot — two-phase dynamic schema + LLM-structured-output pattern
- Prodigal Payment Collection Agent — hybrid LLM + per-slot regex fallback pattern
