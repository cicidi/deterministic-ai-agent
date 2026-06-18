# LLM Gateway — Mandatory Structured Output Interface

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: The single LLM entry point that enforces mandatory structured JSON output for every LLM interaction.
> **This is the enforcement mechanism for "All LLM output is JSON" (VISION.md §6.3).**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial LLM Gateway spec |

---

## 1. Role

Every LLM call in the framework goes through **one gateway interface**. This gateway enforces three rules:

1. **`output_schema` is mandatory** — you cannot call the LLM without declaring what JSON shape you expect back
2. **The framework validates the response** against the schema before returning it
3. **If validation fails, the framework retries** (within retry budget) — the caller never sees a malformed response

This is NOT a "nice-to-have" or "per-task optional setting." It is a **hard constraint** enforced at the interface level.

```
Layer 1 (Extract)
Layer 2 (Decision)   ──→  [LLM Client Gateway]  ──→  LLM Provider (OpenAI / Anthropic / DeepSeek)
Layer 3 (Response)         ├─ schema enforcement
                           ├─ JSON validation
                           ├─ type coercion
                           └─ retry on violation
```

## 2. Interface Contract

### 2.1 Call Input

```
LLMCall {
  prompt:           string | Message[]    // system + user messages
  output_schema:    JSONSchema           // MANDATORY — what shape the response must have
  temperature:      float                // 0 for extraction/decision, 0.3 for response
  max_tokens?:      int
  provider?:        string               // "openai" | "anthropic" | "deepseek" | ...
  model?:           string               // "gpt-4o" | "claude-sonnet-4-20250514" | ...
  conversation_id?: string               // for tracing / audit
}
```

### 2.2 Call Output

```
LLMResult {
  data:       dict              // validated JSON matching output_schema
  raw:        string            // raw LLM response (for audit trail)
  model:      string            // which model was used
  usage:      TokenUsage        // tokens in / out
  attempts:   int               // how many attempts (1 if first try passed)
  validated:  boolean           // always true — gateway guarantees this
}
```

### 2.3 TokenUsage

```
TokenUsage {
  prompt_tokens:      int
  completion_tokens:  int
  total_tokens:       int
}
```

## 3. Framework Guarantees

The gateway guarantees that **`LLMResult.data` is always valid JSON matching `output_schema`** — or the call fails entirely (errorNode). The caller never receives a partially valid or unvalidated response.

### 3.1 Validation Pipeline

```
LLM call
    │
    ├── success ──→ Step 1: Parse JSON
    │                   │
    │                   ├── valid JSON ──→ Step 2: Schema match
    │                   │                      │
    │                   │                      ├── matches schema ──→ return LLMResult
    │                   │                      └── mismatch ──→ retry (with error context)
    │                   │
    │                   └── not JSON ──→ retry (with "must output JSON" instruction)
    │
    └── provider error (timeout, 5xx) ──→ retry (within retry budget) → errorNode
```

### 3.2 Validation Checks

| Check | What | Failure Action |
|-------|------|---------------|
| **JSON parse** | Response is valid JSON | Retry with "Output must be valid JSON" |
| **Schema match** | All required fields present | Retry with missing field names |
| **Type coercion** | `"123"` → `123` if schema says `int` | Auto-coerce where safe; retry where ambiguous |
| **No extra fields** | No fields outside the schema | Strip extra fields (configurable: strip vs error) |

### 3.3 Retry on Violation

```
Retry budget per LLM call:
  max_attempts:      3              // base retry
  +1 llm_extra:      true           // LLM gets +1 = 4 total attempts
  backoff:           exponential    // 500ms → 1s → 2s → 4s
  on_exhausted:      errorNode      // always errorNode
```

Each retry injects the validation error into the prompt so the LLM can self-correct:

```
Attempt 1 → LLM responds with {"intent": "get_quote"}    → missing "confidence" field
Attempt 2 → LLM responds with {"intent": "get_quote", "confidence": "high"}  → type error (string not number)
Attempt 3 → LLM responds with {"intent": "get_quote", "confidence": 0.92}    → valid, return
```

### 3.4 LLM +1 Extra Retry

Per VISION.md §6.3, LLM nodes receive +1 extra retry on top of the base retry budget. This is applied by the gateway:

```
max_attempts = node.retry_budget.max_attempts + 1  // auto-injected by gateway for LLM nodes
```

## 4. Implementation Options

### Option A: Provider-Native Structured Output

Pass `output_schema` as `response_format` to LLM providers that support native structured output (OpenAI JSON mode, Anthropic tool use with strict mode). The LLM itself enforces the schema.

| Strengths | Provider guarantees schema at generation time; fewer retries |
|-----------|--------------------------------------------------------------|
| Weaknesses | Only some providers support it; schema complexity limits vary |
| Best for | Production, when using OpenAI / Anthropic |

### Option B: Post-Process Validation (Provider-Agnostic)

Always call LLM without `response_format`. Parse and validate the response in the gateway after receiving it. Works with any LLM provider.

| Strengths | Works with any provider; no schema complexity limits |
|-----------|----------------------------------------------------|
| Weaknesses | More retries; LLM may produce incorrect shape frequently |
| Best for | Local models, Ollama, providers without structured output support |

### Option C: Hybrid (Default Recommendation)

Try Option A first. If the provider supports `response_format`, use it. If not, fall back to Option B. If the provider supports `response_format` but the LLM call fails schema check (rare), retry with enriched error context.

```yaml
llm:
  gateway_strategy: hybrid        # hybrid | native_only | post_process_only
  native_providers:               # which providers support response_format
    - openai
    - anthropic
  fallback_providers:             # post-process only
    - ollama
    - deepseek
```

### 4.4 Comparison Matrix

| Dimension | Option A (Native) | Option B (Post-Process) | Option C (Hybrid) |
|-----------|-------------------|------------------------|-------------------|
| Provider support | Limited (OpenAI, Anthropic) | Any provider | Any, with optimization |
| Retry frequency | Low | Medium-High | Low |
| Schema complexity limit | Provider-dependent | Unlimited | Best available |
| Latency | 1 call typically | 1-4 calls | 1 call typically |
| Implementation | Leverage provider SDK | Pure JSON Schema validation | Both |

## 5. Schema Definition

### 5.1 JSONSchema Format

The gateway accepts standard JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "intent": {
      "type": "string",
      "description": "The classified intent label"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Confidence score"
    },
    "reasoning": {
      "type": "string",
      "description": "LLM's reasoning for the classification"
    }
  },
  "required": ["intent", "confidence"]
}
```

### 5.2 YAML Schema Declaration

For workflow authors, the schema is declared in YAML and auto-converted to JSON Schema:

```yaml
# In workflow node or domain model
output_schema:
  intent:
    type: string
    description: "The classified intent label"
    required: true
  confidence:
    type: number
    range: { min: 0, max: 1 }
    required: true
  reasoning:
    type: string
    required: false
```

## 6. Usage in Each Layer

### 6.1 Layer 1 — Extraction

```yaml
extraction_nodes:
  collect_property_info_extract:
    executor: llm
    output_schema:          # MANDATORY — gateway enforces
      property_type:
        type: string
        required: true
      address:
        type: string
        required: true
      building_age:
        type: number
        required: true
      floor_area:
        type: number
        required: false
```

### 6.2 Layer 2 — Decision

```yaml
decision_nodes:
  risk_triage:
    executor: llm
    output_schema:          # MANDATORY
      route:
        type: string
        enum: [auto_approve, standard_review, manual_review]
        required: true
      reason:
        type: string
        required: true
```

### 6.3 Layer 3 — Response

```yaml
response_nodes:
  goal_setter:
    executor: llm
    output_schema:          # MANDATORY
      summary:
        type: string
        required: true
      intent:
        type: string
        required: true
      success_criteria:
        type: array
        items: { type: string }
        required: true

  goal_checker:
    executor: llm
    output_schema:          # MANDATORY
      goal_met:
        type: boolean
        required: true
      completion_percentage:
        type: number
        range: { min: 0, max: 1 }
        required: true
      gap_analysis:
        type: string
        required: true

  generate_response:
    executor: llm
    output_schema:          # MANDATORY — even for free-text generation
      text:
        type: string
        required: true
      components:
        type: array
        items: { type: object }
        required: false
```

## 7. Integration with errorNode

When the gateway exhausts all retry attempts and still has an invalid response:

```
LLM Client Gateway (retry exhausted)
    │
    ▼
errorNode ──→ strategy: retry_with_context | escalate_to_human | terminate
    │
    ▼
  audit log: { schema_violation: true, attempts: 4, last_error: "missing field 'intent'" }
```

The gateway records every failed attempt, including the schema violation details, in the audit trail.

## 8. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should the gateway support streaming (incremental schema validation as tokens arrive) or only full-response validation? | Latency for long responses |
| 2 | Should the gateway cache identical LLM calls (same prompt + schema + model) to reduce cost during development? | Cost, determinism in dev |
| 3 | How should `$ref` and `$defs` in complex JSON Schema be handled across different LLM providers with different schema capabilities? | Schema complexity support |
| 4 | Should the gateway emit detailed schema violation traces to LangSmith/LangFuse for prompt improvement? | Debugability |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — §4.3 "LLM Output is JSON — Always", §4.1 framework principles
- [Extraction Layer](./2026-06-17-extraction-layer-design.md) — Extract/Validate/Transform pipeline, LLM usage
- [Routing & Execution](./2026-06-17-routing-execution-layer-design.md) — Decision nodes, errorNode, retry budgets
- [Response Generation](./2026-06-17-response-generation-layer-design.md) — Goal setter, goal checker, response generator
- [VISION.md](../VISION.md) — §6.3 LLM Rules, §6.5 Error Handling
