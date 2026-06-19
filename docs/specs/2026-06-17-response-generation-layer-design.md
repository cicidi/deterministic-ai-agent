# Response Generation Layer Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Goal setting, response generation, goal completion verification, templates, sensitive field handling.
> **This spec defines interfaces and alternative implementation strategies — not a single solution.**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial response generation spec: goal setting, response generation, goal completion check, parallel execution |
| 2026-06-17 | 0.2.0 | Refactor response modes: Pure Message (LLM+eval) vs Widget (deterministic); add Node Loop-Back |
| 2026-06-17 | 0.3.0 | Replace Python code blocks with YAML schemas/configs; add errorNode cross-reference in 4.4; state "All LLM output = JSON" in Sections 2 and 4 |
| 2026-06-17 | 0.4.0 | Section 4.3: remove duplicate JSON guardrail declaration; Section 2.4: add YAML example of default goal fallback; Section 6 diagram: fix "error handler" → "errorNode" |

---

## 1. Role

The Response Generation layer (Layer 3) answers: *"What do we say back to the user?"*

It consumes structured outcomes from Layer 2 (Routing & Execution) and produces the user-visible response. It also verifies that the workflow actually achieved its stated goal. Response generation and goal verification run in parallel.

```
Layer 2 → structured outcomes
              ↓
+-----------------------------+
| Layer 3: RESPOND            |
|                             |
|  [Goal Setter]  ←──────── workflow start (async)
|                             |
|  [Generate Response] ──┐   |
|                        ├── parallel fan-out
|  [Goal Checker] ───────┘   |
|                             |
|  If gap > threshold: 422   |
+-----------------------------+
              ↓
         user response
```

### 1.1 What Layer 3 Does NOT Cover

- **Entity extraction** → Layer 1
- **Intent classification** → Layer 1
- **Business logic** → Layer 2
- **Routing decisions** → Layer 2
- **Retry / error handling** → Layer 2 (Section 6)
- **Permission enforcement** → Layer 2 (Section 7)

---

## 2. Goal Setting

> **All LLM output is JSON.** The framework enforces structured JSON output with schema validation guardrails on every LLM interaction. Free-text generation is limited to Layer 3 (Response).

### 2.1 Concept

Every workflow starts with a **goal** — a structured description of what the workflow intends to accomplish, derived from the user's initial utterance and intent.

The goal is set **asynchronously by LLM** at workflow start, stored in `agentState.goal`. The workflow proceeds immediately; it does not block on goal setting.

### 2.2 Goal Schema

```
WorkflowGoal {
  summary:          string    // human-readable summary of what the user wants
  intent:           string    // classified intent (e.g., "submit_lead")
  expected_entities: string[] // which entities should be collected
  expected_outputs: string[]  // which outputs should be produced
  success_criteria: string[]  // measurable criteria for "done"
  priority:          "normal" | "high" | "critical"
}

# Example
goal: {
  summary: "User wants a mortgage lead quote for their apartment",
  intent: "submit_lead",
  expected_entities: ["lead_purpose", "loan amount_needs"],
  expected_outputs: ["rate_calculation", "rate_calculation", "quote"],
  success_criteria: [
    "loan_purpose is known",
    "address is collected",
    "annual_rate is calculated",
    "quote is presented to user"
  ],
  priority: "normal"
}
```

### 2.3 Async Execution

Goal setting is dispatched asynchronously at workflow start. The workflow proceeds immediately without blocking on the LLM call. When the LLM completes, the goal is written to `agentState.goal`. If the goal setter has not completed by the time the goal check node runs, the framework waits (1-second timeout max).

**All LLM output is JSON.** The framework enforces structured JSON output with schema validation guardrails on every LLM interaction.

```yaml
# Per-workflow config
goal_setting:
  executor: llm
  output_schema: WorkflowGoal
  temperature: 0
  prompt_template: goal_setter_prompt
  async: true                 # dispatched immediately, does not block workflow
  timeout_ms: 1000            # max wait if not completed before goal check
  fallback_on_failure: derive_from_intent  # default goal from intent + entities
```

### 2.4 Goal Availability Guarantee

The goal is guaranteed available before the goal check node runs (end of workflow). If the async goal setter has not completed by then, the framework waits (1-second timeout max). If the goal setter fails → a default goal is derived from the intent + collected entities.

```yaml
# Default goal fallback example:
# intent=submit_lead + entities=[lead_purpose] → goal: "Provide mortgage lead quote"
default_goal_fallback:
  strategy: derive_from_intent     # fallback derives goal from intent + collected entities
  mapping:
    submit_lead:
      summary_template: "User wants a {product_type} mortgage rate"
      expected_outputs: ["rate_calculation", "rate_calculation", "quote"]
    check_rates:
      summary_template: "User wants to check rates for {loan_type}"
      expected_outputs: ["rate_comparison", "rate_result"]
    ask_question:
      summary_template: "User asked a question about {topic}"
      expected_outputs: ["answer"]
```

---

## 3. Response Generation

### 3.1 Contract

```
Input:
  outcome:       Map<string, any>   // structured results from Layer 2
  entities:      Map<string, any>   // collected entities
  goal:          WorkflowGoal       // the workflow's goal
  conversation:  ContextWindow      // conversation history

Output:
  response:      ResponseMessage    // the user-visible response
```

### 3.2 ResponseMessage Schema

```
ResponseMessage {
  text:           string            // main text content (markdown supported)
  components?:    UIComponent[]     // structured UI elements
  actions?:       SuggestedAction[] // quick reply buttons, follow-up suggestions
  sensitive_data_scrubbed: boolean  // framework flag: PII removed from free text
}
```

### 3.3 Implementation Options

Both modes serve the same purpose: **deliver the correct answer and guide the user to the next step.**

#### Option A: Pure Message (LLM)

LLM generates a natural-language message based on the current `agentState`. The framework injects a prompt guiding the LLM on what to say and how to say it.

| Aspect | Detail |
|--------|--------|
| Strengths | Natural language; adapts to any outcome shape |
| Weaknesses | Non-deterministic; LLM cost; needs prompt eval testing |
| Prompt | Framework-injected: includes goal, outcomes, entities, conversation context |
| Temperature | 0.3 (enough for natural phrasing, not enough for creative drift) |
| Guardrail | Framework post-processes: cross-check values against entities, redact PII |
| Eval required | Prompt guidance accuracy must be tested via eval suite |

```yaml
# Per-workflow prompt config for pure message generation
response_generation:
  mode: pure_message
  prompt_template: response_generator_prompt
  prompt_variables:
    - goal
    - outcomes
    - entities
    - conversation
    - next_step_suggestion     # always true: guide user to next action
  output_schema: ResponseMessage
  temperature: 0.3
  guardrails:
    - schema_validation        # enforce ResponseMessage schema
    - cross_check_entities     # verify referenced values match collected entities
    - redact_pii               # strip sensitive data before delivery
```

**Prompt guidance eval:** The prompt must reliably produce responses that:
1. Reference entity values accurately (no hallucinated numbers)
2. Include a clear next-step suggestion
3. Match the tone configured for the workflow
4. Do not fabricate outcomes that were not produced

```yaml
# Eval case definition for prompt evaluation
eval_cases:
  - id: "prod_default"
    description: "Standard mortgage rate completion"
    given_state:
      goal:
        summary: "User wants a mortgage lead quote"
        intent: "submit_lead"
      entities:
        loan_amount: "123 Main St"
        loan_purpose: "apartment"
      outcomes:
        rate_calculation:
          annual_rate: 1200
    expected:
      themes: ["address confirmed", "rate calculated", "next step"]
      forbidden_themes: ["unknown data", "fabricated outcome"]
      tone: "professional"
    threshold_pct: 95

  - id: "incomplete_flow"
    description: "Workflow ended with missing entity"
    given_state:
      goal:
        summary: "User wants a quote"
        intent: "submit_lead"
      entities:
        loan_amount: "456 Oak Ave"
        # loan_purpose intentionally missing
      outcomes:
        error: "loan_purpose not collected"
    expected:
      themes: ["we need more information", "property type"]
      forbidden_themes: ["rate calculated", "quote ready"]
      tone: "professional"

# Eval suite runs on every prompt change. Must pass ≥95%.
```

#### Option B: Widget / Component (Deterministic Logic)

Pure logic generates structured UI components. No LLM call. The widget contains the answer + next-step guidance in a machine-readable format that the frontend renders.

| Aspect | Detail |
|--------|--------|
| Strengths | Deterministic; zero LLM cost; consistent rendering; instant |
| Weaknesses | Cannot adapt to unexpected outcomes; frontend must support component types |
| Best for | Structured data presentation (rate cards, lead status, risk gauges) |
| Generation | Pure code: map outcomes → widget template → populate with entity data |

```yaml
# Per-workflow widget mapping: outcomes → components
widget_mapping:
  rate:
    outcome_key: "rate"
    condition: "outcomes.rate is present"
    component: rate_breakdown_card
    required_fields: [annual_rate, monthly_rate, loan amount_type]

  risk_score:
    outcome_key: "risk_score"
    condition: "outcomes.risk_score is present"
    component: risk_score_gauge
    required_fields: [score, factors]

  requires_approval:
    outcome_key: "requires_approval"
    condition: "outcomes.requires_approval == true"
    component: approval_buttons

  default_next_step:
    component: next_step_actions
    always: true
```

Widgets are defined as registered components:

```yaml
components:
  rate_breakdown:
    type: widget
    fields:
      annual_rate:   { type: float, required: true }
      monthly_rate:  { type: float, required: true }
      loan amount_type:    { type: string, required: true }
      risk_score:       { type: int, range: [0, 100] }
    render:
      template: rate_breakdown_card_template
  risk_gauge:
    type: widget
    fields:
      score:    { type: int, range: [0, 100] }
      factors:  { type: list }
```

#### Option C: Mixed — Widget + Message Fallback

Primary response via widget (deterministic). A plain-text message is auto-generated as fallback for channels that don't support rich components.

```yaml
response_strategy:
  primary: widget          # widget | pure_message
  fallback: auto_message   # auto_message | none
```

### 3.4 Comparison Matrix

| Dimension | Pure Message (LLM) | Widget (Deterministic) | Mixed |
|-----------|-------------------|----------------------|-------|
| Response generation | LLM | Pure code | Widget + LLM fallback |
| Cost | $$$ | $ | $$ |
| Determinism | Low | High | High (primary is deterministic) |
| Next-step guidance | LLM prompt guided | Coded in widget logic | Widget logic |
| Rich UI | Text only | Structured components | Structured components |
| Prompt eval needed | Yes | No | Only for fallback |
| Best for | Text-heavy channels, simple responses | Rich clients, structured data | Production default |

---

## 4. Goal Completion Check

> **All LLM output is JSON.** The goal checker is an LLM node that produces structured `GoalCheckResult` JSON with schema validation guardrails.

### 4.1 Concept

At workflow end, an LLM node runs **in parallel with response generation** to verify whether the workflow actually achieved its goal. This is the `goalChecker` node.

```
Workflow End
     │
     ├──→ [generateResponse] ──→ response_text
     │
     └──→ [goalChecker] ──→ goal_check_result
                │
                ├── gap ≤ threshold → deliver response
                └── gap > threshold → HTTP 422 Unprocessable Content
```

### 4.2 GoalCheckResult Schema

```
GoalCheckResult {
  goal_met:          boolean           // true if goal was achieved
  completion_percentage: float        // 0.0 - 1.0
  satisfied_criteria: string[]        // which success_criteria were met
  unsatisfied_criteria: string[]      // which success_criteria were NOT met
  gap_analysis:      string           // LLM reasoning: what's missing
  missing_entities:  string[]         // entities not collected
  missing_outputs:   string[]         // outputs not produced
}
```

### 4.3 Gap Threshold & Error 422

The goal checker runs in parallel with response generation.

```yaml
# Per-workflow config
goal_check:
  executor: llm
  output_schema: GoalCheckResult
  temperature: 0
  prompt_template: goal_checker_prompt
  prompt_variables:
    - goal
    - entities
    - outcomes
    - conversation

  gap_threshold: 0.3          # completion < (1 - threshold) → 422
  # Example: threshold = 0.3 means completion ≥ 70% required

  on_gap:
    strategy: error_422       # error_422 | loop_back | escalate
    response:
      status: 422
      body:
        error: "goal_not_met"
        goal_summary: "{{ goal.summary }}"
        completion: "{{ result.completion_percentage }}"
        unsatisfied: "{{ result.unsatisfied_criteria }}"
        gap_analysis: "{{ result.gap_analysis }}"
```

### 4.4 Goal Check Failure Handling

When 422 is raised:

1. The response is **not** delivered to the user
2. The error propagates to the calling system
3. The conversation state is checkpointed (can be resumed by a human agent)
4. Audit log records: goal, completion percentage, gap analysis, unsatisfied criteria
5. The 422 error ultimately routes through `errorNode` (see Layer 2, Section 6 — Retry & Error Handling) for unified error logging, checkpointing, and escalation

The caller can choose to:
- Display `"We're having trouble completing your request. An agent will follow up."`
- Automatically retry the workflow with enriched context
- Escalate to human review

### 4.5 Goal Check in Non-Transactional Flows

For conversational/FAQ flows (no transactional goal), the `goal_checker` still runs but with a relaxed threshold:

```yaml
goal_check:
  transactional_threshold: 0.7    # 70% completion required for transactional workflows
  conversational_threshold: 0.3   # 30% for FAQ — answering one question is "good enough"
  enabled: true                   # can be disabled per workflow
```

---

## 5. Node Loop-Back (Self-Correction)

### 5.1 Concept

A node that completes its task can still detect that something is incomplete, and **loop back to re-run earlier nodes.** This enables self-correcting workflows — for example:

```
[code] → [test] → (fails) → [debug] → [code] → [test] → (passes) → [respond]
```

This is not specific to Layer 3 — it applies to any node in any layer. But it integrates with the Response Generation through the goal checker: if the goal checker finds a gap, it can trigger a loop-back instead of just returning 422.

### 5.2 Loop-Back Trigger

A node can declare a post-execution check. If the check fails → loop back to a specified state:

```yaml
states:
  run_tests:
    executor: code
    execute: run_test_suite
    post_check:
      condition: "all_tests_passed == false"
      on_fail: debug_and_fix      # loop back to this state
      max_loops: 3                # prevent infinite loops

  deploy:
    executor: code
    execute: deploy_to_staging
    post_check:
      condition: "deployment_healthy == false"
      on_fail: rollback_and_retry
      max_loops: 2
```

### 5.3 Integration with Goal Checker

When the goal checker detects a gap (completion < threshold), instead of throwing 422, the workflow can be configured to loop back:

```yaml
# Per-workflow config
goal_check:
  on_gap:
    strategy: loop_back        # loop_back | error_422 | escalate
    loop_back_to: start_phase  # which phase to return to
    max_loop_backs: 2          # max total loop-backs per workflow execution
```

### 5.4 Loop-Back State

Loop-back preserves collected data (entities filled so far). The restarted node receives:
- All entities collected up to this point
- The gap analysis from the goal checker (what was missing)
- The loop-back counter (remaining attempts)

```
[collect] → [validate] → [calculate] → [goalChecker]
                    ↑                        │
                    │                  (gap: address missing)
                    │                        │
                    └── loop_back ───────────┘
                    (address asked, filled)
                         │
                         ↓
              [validate] → [calculate] → [goalChecker] → (passes)
```

### 5.5 Loop-Back vs Retry

| Mechanism | Retry (Layer 2, Section 6) | Loop-Back (this section) |
|-----------|--------------------------|-------------------------|
| Triggers on | Node execution failure (timeout, error) | Task incompleteness (results aren't right) |
| Repeats | Same node with same input | Different node (earlier in the workflow) with enriched state |
| Purpose | Transient error recovery | Self-correcting incomplete work |
| Budget | `max_attempts` per node | `max_loops` per loop-back + `max_loop_backs` per workflow |

---

## 6. Parallel Execution Pattern (response + goal checker)

### 6.1 Fan-Out at Workflow End

```
[Last Layer 2 Node] → conditional edge
                            │
                    ┌───────┴───────┐
                    │               │
              [generateResponse]  [goalChecker]
                    │               │
                    └───────┬───────┘
                            │
                     [responseRouter]
                            │
                    ┌───────┴───────┐
            (goal met)          (422: goal not met)
                │                      │
           deliver response      errorNode
```

### 6.2 Implementation Approach

The parallel fan-out uses LangGraph's `Send` API to dispatch state to `generateResponse` and `goalChecker` simultaneously from the last Layer 2 node via a conditional edge. Both nodes execute concurrently and converge at a `responseRouter` node, which inspects `goal_check.passed` to decide: deliver the response (route to `END`) or handle goal-not-met (route to `errorNode` for unified 422 handling).

The graph structure:

- **Nodes:** `generateResponse`, `goalChecker`, `responseRouter`, `errorNode`
- **Fan-out:** `lastLayer2Node` → conditional edge → `Send` to both `generateResponse` and `goalChecker`
- **Convergence:** Both `generateResponse` and `goalChecker` → edges → `responseRouter`
- **Routing:** `responseRouter` → conditional edge → `END` (deliver) or `errorNode` (422)

---

## 7. Frontmatter Component Protocol

For deterministic structured UI rendering (e.g., formatted cards in a chat interface), the framework adopts a frontmatter protocol inspired by zelkim:

```
ResponseMessage {
  text: "Here's your quote..."
  components: [
    {
      type: "rate_breakdown_card",
      metadata: { ... },
      data: { ... }           // structured, machine-readable
    }
  ]
}
```

The `text` field is the fallback for channels that only support plain text (SMS, email). The `components` array provides structured rendering for rich clients (web, mobile).

### 7.1 Component Types (Extensible)

| Component Type | Description |
|---------------|-------------|
| `rate_breakdown_card` | Insurance rate details with line items |
| `risk_score_gauge` | Visual risk score (0-100) |
| `loan_comparison_table` | Side-by-side loan options |
| `lead_status_tracker` | Lead lifecycle progress |
| `lead_receipt` | Lead submission receipt with lead ID |
| `document_upload_prompt` | File upload with type constraints |
| `approval_buttons` | Confirm / Decline / Modify actions |

Custom components are registered via plugin.

---

## 8. Sensitive Field Handling

### 8.1 Post-Generation PII Scrubbing

The framework runs a post-processing pass on every generated response. PII rules (defined in the domain model, see Section 8.2) are applied to both the response `text` and component `data` fields.

```yaml
# PII scrubbing config (per-workflow or global)
pii_scrubbing:
  enabled: true
  scope:
    - response_text             # apply regex + field-masking to ResponseMessage.text
    - component_data            # mask sensitive field values in UI components
  rule_source: domain.pii_rules # rules defined in domain model (Section 8.2)
  on_complete:
    set_flag: sensitive_data_scrubbed  # = true
```

### 8.2 PII Rules (Defined in Domain Model)

```yaml
pii_rules:
  - pattern: "\\b[0-9]{16}\\b"         # credit card number
    replacement: "****-****-****-{last4}"
  - pattern: "\\b[0-9]{18}\\b"         # Chinese ID number
    replacement: "******{last4}"
  - fields: [phone, email, id_number]   # entity fields to mask
    strategy: partial_mask              # show first 3, mask rest
```

### 8.3 Sensitive Data in LLM Prompts

When constructing the LLM prompt for response generation, only the **non-sensitive subset** of collected entities is passed. PII rules (from Section 8.2) are applied **before** prompt construction.

```yaml
# Per-workflow config
prompt_entity_filter:
  enabled: true
  rule_source: domain.pii_rules      # matches Section 8.2
  strategy: partial_mask             # partial_mask | exclude | redact
  # partial_mask: show first 3 chars, mask rest (e.g., "Joh***")
  # exclude: omit field entirely from prompt
  # redact: replace with "[REDACTED]"
```

The framework applies this filter to `state.collectedFields` before injecting entities into any LLM prompt template. The resulting `safe_entities` map is what the prompt template receives via the `entities` variable.

---

## 9. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should the goal checker also run mid-workflow (at each phase transition) or only at the end? | Early failure detection |
| 2 | 422 error — should the framework support auto-retry of the entire workflow, or always escalate? | Recovery strategy |
| 3 | For async goal setting: what happens if the user rephrases or changes their request before the goal is set? | Goal accuracy |
| 4 | Template authoring — should templates be written in YAML, Jinja2, or a custom DSL? | Developer experience |
| 5 | Component protocol — should components be defined as a standard schema (like JSON Schema) for cross-platform interoperability? | Rich client support |
| 6 | PII scrubbing — should it be language-aware (e.g., Chinese ID vs US SSN patterns)? | Internationalization |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — parent architecture, framework principles (JSON guardrails)
- [Domain Model Design](./2026-06-17-domain-model-design.md) — entity schemas, PII rules in domain model
- [Routing & Execution Layer Design](./2026-06-17-routing-execution-layer-design.md) — Layer 2 outputs consumed by response generation
- zelkim/langgraph-insurance-chatbot — frontmatter component protocol, hybrid template pattern
- Prodigal Payment Collection Agent — post-API response scrubbing (card data wiped from memory)
