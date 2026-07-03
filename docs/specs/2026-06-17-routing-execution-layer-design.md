# Routing & Execution Layer Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Business logic execution, decision routing, phase-aware routing + return stack, sub-workflow reuse, retry budgets, permission model, tool system.
> **This spec defines interfaces and alternative implementation strategies — not a single solution.**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial routing & execution spec: executor, decision nodes, phase-aware routing + return stack, sub-workflow, retry, permission, tool system |
| 2026-06-17 | 0.2.0 | Replace all Python code blocks with YAML schemas/structured descriptions; merge errorNode config (§8) into retry section (§6); add YAML schemas for AbstractState, code executors, decision rules, phase routing, errorNode, permission enforcement, tool interface, transition enforcement |
| 2026-06-17 | 0.3.0 | Add §1.2 AgentState Concurrency Model: copy-on-write + reducer merge, conflict scenarios, reducer strategies (last_write_wins/conflict_detect/append/merge), Java ConcurrentHashMap comparison; Section 2.3: remove ≤50 lines constraint from YAML comment; delete Section 8 stub (now consolidated in Section 6); fix missing closing ``` on ASCII flow diagram in Section 6.7 |
| 2026-06-17 | 0.4.0 | Add §5 A2A protocol cross-reference (sub-workflows as A2A definition language); add A2A Protocol spec to References |
| 2026-06-18 | 0.5.0 | Extend `Tool.type` enum from `api \| mcp \| command \| llm` to `api \| mcp \| command \| llm \| a2a \| sdk`; add `a2a` tool type for agent-to-agent as a tool; add `sdk` tool type for OpenCode/Claude SDK as a tool |
| 2026-06-25 | 0.6.0 | Major error handling overhaul: add §6.3 Error Classification (transient/permanent/partial) — required before strategy selection. Add §6.5 Structured Error Schema (FrameworkError with root_cause chain for cross-agent tracing). Expand strategies from 5 to 8: add `retry_with_backoff`, `graceful_degradation`, `dead_letter_queue`. Add §6.7 Strategy Decision Matrix. Update §6.8 errorNode interface to accept FrameworkError. Update §6.9 flow diagram. Add §6.10 per-node error strategy configuration with DLQ backend config. Aligns with AD #15 revision. |
| 2026-06-25 | 0.6.1 | Fix §1.2–§1.3 concurrency model contradiction: remove absolute "all fields append-only, not configurable" claim. Split fields into two categories: audit fields (`messages`, `audit_log`, `llm_calls`) = append-only locked; business fields (`collectedFields`, `response`, `goal_check_result`, `entities`, `phase_stack`) = configurable via `state_reducers`, append is default. Update conversation-lifecycle §4.4 to match. |

---

## 1. Role

The Routing & Execution layer (Layer 2) answers: *"What should we do with the extracted data?"*

It consumes validated entities from Layer 1 (Extraction) and produces structured outcomes for Layer 3 (Response). It is the **core business logic layer** — where rules are enforced, decisions are made, and side effects (API calls, database writes) occur.

```
Layer 1 → validated entities
              ↓
+-----------------------------+
| Layer 2: DECIDE             |
|                             |
|  [Code Executor]            |  → business computation
|  [Decision Node]            |  → rule engine routing
|  [Sub-workflow Invoker]     |  → shared capability reuse
|  [Phase-Aware Routing]   |  → state locking via return stack
|  [Retry Manager]            |  → retry + escalation
|  [Permission Enforcer]      |  → tool + transition access
+-----------------------------+
              ↓
Layer 3 ← structured outcomes
```

### 1.1 What Layer 2 Does NOT Cover

- **Entity extraction** → Layer 1 (Extraction spec)
- **Intent classification** → Layer 1 (Intent Classification spec)
- **Field validation** → Layer 1 (Validate node in Extraction spec)
- **Response generation** → Layer 3 (Response Generation spec)
- **State machine mechanics** → State Machine Design spec (transitions, guards, metadata)
- **Domain model definition** → Domain Model spec (entities, states, transitions)

### 1.2 AgentState Concurrency Model

Multiple nodes read and write to `agentState` — but this does NOT cause race conditions. The design follows **copy-on-write + reducer merge**, inherited from LangGraph's `StateGraph` semantics. No ReadWriteLock needed.

**How it works:**

```
Node A execution:
  state_copy = agentState.deep_copy()     # take a snapshot
  state_copy.collectedFields["address"] = "Beijing"  # write to copy
  return {"collectedFields": state_copy.collectedFields}  # submit update

Node B execution:
  state_copy = agentState.deep_copy()     # independent copy
  state_copy.goal_check = result          # write to copy
  return {"goal_check": result}           # submit update

Framework merge (single-threaded reducer):
  agentState = merge(updates)  # { collectedFields: {address: "Beijing"}, goal_check: {...} }
```

**Key properties:**

| Property | How |
|----------|-----|
| **No shared mutable state** | Each node operates on its own copy |
| **No lock contention** | Merge is single-threaded, not concurrent |
| **Parallel nodes (Send API)** | Each parallel branch gets its own copy; reducers merge results |
| **Field isolation** | Parallel nodes write to different fields (response → `response`, goalChecker → `goal_check`) |

**Conflict scenario — parallel sub-workflow + parent:**

The only scenario where a write conflict is possible is an async sub-workflow and parent both writing to the same field. The framework handles this through configurable **state reducers** that determine how parallel writes to the same field are resolved.

Fields are divided into two categories with different concurrency guarantees:

| Category | Fields | Behavior | Configurable? |
|----------|--------|----------|---------------|
| **Audit fields** | `messages`, `audit_log`, `llm_calls` | Always append-only — framework-locked, not configurable. All parallel writes are accumulated, never overwritten. | ❌ Locked |
| **Business fields** | `collectedFields`, `response`, `goal_check_result`, `entities`, `phase_stack` | Default: append. Configurable via `state_reducers` to `last_write_wins`, `conflict_detect`, `merge`, or `custom`. | ✅ Configurable |

```yaml
state_reducers:
  # Audit fields — append-only, locked, not configurable
  messages:
    strategy: append    # appended to message history (framework-enforced)
  audit_log:
    strategy: append    # appended to audit trail (framework-enforced)

  # Business fields — configurable, append is default
  collectedFields:
    strategy: conflict_detect   # parallel writes → raise on conflict
    on_conflict: raise
  response:
    strategy: last_write_wins   # most recent response wins
  goal_check_result:
    strategy: last_write_wins
```

**Why audit fields are locked append-only:** For a regulated-industry framework, no conversation message and no audit log entry should be silently lost. If two parallel nodes both produce output, both outputs are preserved. The downstream node (or human reviewer) decides which to use — the framework never discards audit data.

**Why business fields are configurable:** Business fields (`collectedFields`, `response`, `goal_check_result`) have legitimate use cases for non-append strategies. For example, `response: last_write_wins` makes sense when parallel response generators produce competing outputs — only the most recent is relevant. `collectedFields: conflict_detect` makes sense when parallel extraction nodes should not silently accumulate conflicting values for the same field.

### 1.3 State Reducer Configuration

**Audit fields** (`messages`, `audit_log`, `llm_calls`) are **append-only and not configurable** — the framework enforces this at load time. This guarantees that no conversation message or audit event is silently discarded.

**Business fields** (`collectedFields`, `response`, `goal_check_result`, `entities`, `phase_stack`) are **configurable via `state_reducers`**. When `parallel_nodes` is non-empty and multiple nodes write to the same business field, the framework requires a reducer to be declared. Append is the default.

**YAML declaration:**

```yaml
state_reducers:            # REQUIRED when parallel_nodes is non-empty
  # Business fields — configurable
  collectedFields:
    strategy: conflict_detect
    on_conflict: raise      # raise StateConflictError | log_and_override | queue
  response:
    strategy: last_write_wins
  goal_check_result:
    strategy: last_write_wins
  # messages and audit_log are append-only — no declaration needed
```

**Interface:**

```
Reducer {
  field:      string                                    // which field this reducer governs
  strategy:   "last_write_wins" | "conflict_detect" | "append" | "merge" | "custom"
  on_conflict: "raise" | "log_and_override" | "queue"   // what to do on conflict
  custom_fn?: string                                    // registered custom reducer function name
}
```

**Framework enforcement flow:**

```
1. Workflow YAML loaded
2. Framework scans for parallel_nodes
3. If parallel_nodes is non-empty:
   a. For each business field written by a parallel node → check state_reducers has an entry
   b. Missing reducer → YAML validation error, workflow REFUSED to load
   c. Audit fields (messages, audit_log) → append-only, auto-assigned, no declaration needed
   d. All reducers present → compile into LangGraph channel reducers
```

**Why this matters:**

Without reducers, two parallel nodes writing to the same field produce non-deterministic results — whichever finishes last wins silently. The framework catches this at load time, not at runtime, preventing silent data corruption in production.

**Guarantees:**

| Scenario | Guarantee |
|----------|-----------|
| Serial nodes | Zero contention (each node sees previous node's output before running) |
| Parallel nodes writing to different fields | No conflict — each writes to its own field |
| Parallel nodes writing to the same business field | Resolved by declared `state_reducers` strategy |
| Parallel nodes writing to audit fields | Append-only — both results preserved, never lost |

---

## 2. Code Executor Node

### 2.1 Contract

Code executors are **pure business logic** functions. They receive validated data, compute results, and return them. They are small, composable, and deterministic.

```
Input:
  entities:   Map<string, any>   // validated entities from Layer 1
  state_context: StateContext     // current state information
  previous_results: Map<string, any> // results from prior nodes in this workflow

Output:
  results:    Map<string, any>   // computed business results
  decisions:  DecisionResult[]   // routing hints for downstream nodes
  side_effects: SideEffect[]     // API call results, DB writes (recorded for audit)
```

### 2.2 Design Conventions

- Every executor method ≤ **50 lines**
- Every executor file ≤ **1000 lines**
- Complex computations split into sub-functions or sub-workflows
- Executors are pure functions: same input → same output (no hidden state)
- Side effects (API calls, DB writes) are declared explicitly in `side_effects`

### 2.3 Abstract Parent Data Model

Every state shares a common abstract parent that provides metadata. The framework manages the metadata fields below; the developer implements a single `execute(input: StateInput) → StateOutput` function (≤ 50 lines) containing the business logic for this state.

```yaml
# Abstract parent data model — every state shares this structure
abstract_state:
  # --- Framework-managed (set in workflow YAML, populated at runtime) ---
  state_name: string              # unique node identifier
  state_entity: string            # bound domain model entity name
  state_hint: string              # disambiguation hint for downstream nodes
  permission: NodePermission      # tool + transition allowlist (see §7)
  retry_budget: RetryBudget       # retry configuration (see §6.2)

  # --- Developer-implemented ---
  # execute: (input: StateInput) -> StateOutput
  #   Business logic for this state. Delegate complex logic to sub-functions.
```

### 2.4 Implementation Options

#### Option A: Pure Functions (Recommended)

Code executors are registered as module+function references in the workflow YAML. The framework resolves the reference at load time and calls the function with validated input. The function is a pure, stateless computation — no side effects, no framework dependency.

```yaml
# Code executor configured as a pure function reference
executor: code
execute: rate.calculate                  # module.function reference
input_mapping:
  lead_purpose: "{{entities.lead_purpose}}"
  financial_profile: "{{entities.financial_profile}}"
output:
  rate_multiplier: number
  annual_rate: number
  monthly_payment: number
```

| Strengths | Testable in isolation; zero framework dependency; IDE-friendly |
|-----------|---------------------|
| Weaknesses | No built-in lifecycle hooks; manual audit trail |
| Best for | Stateless computation; risk scoring; rate calculation |

#### Option B: StateHandler Class

When richer lifecycle hooks are needed (pre/post execute, audit, error handling), the executor is configured with class-level metadata alongside the handler class reference:

```yaml
# StateHandler configured with lifecycle metadata
executor: code
execute: rate.CalculateRateHandler    # class reference
state_name: calculate_rate
state_entity: rate_result
lifecycle:
  pre_execute: rate.validate_inputs       # optional hook
  post_execute: rate.audit_calculation    # optional hook
  on_error: rate.log_calculation_error    # optional hook
audit: true                                  # framework auto-records audit trail
```

| Strengths | Lifecycle hooks (pre/post execute); framework-managed audit; reusable base |
|-----------|---------------------|
| Weaknesses | More boilerplate; harder to unit test in isolation |
| Best for | Complex multi-step computation; nodes that need rich lifecycle |

### 2.5 Comparison Matrix

| Dimension | Option A (Pure Function) | Option B (Class Handler) |
|-----------|------------------------|------------------------|
| Testability | Excellent (no framework) | Good (with fixtures) |
| Lines of code | ~10-30 per executor | ~20-50 per executor |
| Audit trail | Manual | Auto by framework |
| Lifecycle hooks | None | pre/post_execute, on_error |
| Suitability | Simple computation | Complex orchestration |

---

## 3. Decision Nodes

### 3.1 Role

Decision nodes answer: *"Which path should the workflow take next?"* — beyond simple field-completion guards (which are handled by the state machine's transition guards).

> **All LLM output is JSON.** Decision nodes that use LLM produce structured JSON output with framework-enforced guardrails (schema validation, field presence, type coercion). See HLD Section 4.3.

Examples:
- Risk triage: `rate_multiplier > 80 → manual_review` / `rate_multiplier ≤ 80 → auto_approve`
- Fraud detection: anomaly patterns trigger `manual_review` branch
- Loan routing: `loan_type == "fixed"` routes to `calculate_fixed_rate`

### 3.2 Implementation Options

#### Option A: 100% Rule Engine — Deterministic (Mandatory baseline)

All decisions must go through the rule engine first. No LLM involvement. Rules are defined declaratively in YAML:

```yaml
# Decision ruleset — evaluated top-to-bottom, first match wins
decision_rules:
  assign_lead:
    input: entities.rate_calculation.rate_multiplier
    rules:
      - condition: "rate_multiplier >= 0 AND rate_multiplier <= 30"
        decision:
          route: auto_approve
          reason: "Low risk: {{rate_multiplier}}"
      - condition: "rate_multiplier > 30 AND rate_multiplier <= 80"
        decision:
          route: standard_review
          reason: "Medium risk: {{rate_multiplier}}"
      - condition: "rate_multiplier > 80"
        decision:
          route: manual_review
          reason: "High risk: {{rate_multiplier}}"
    on_unmatched: escalate               # default action when no rule matches
```

| Aspect | Detail |
|--------|--------|
| Strengths | Deterministic; auditable; explainable; fast |
| Weaknesses | Rule maintenance; cannot handle novel patterns |
| Dependencies | Rule engine (durable_rules / business-rules / native) |
| On unhandled case | Default route or error escalation |

#### Option B: Rule Engine + LLM Fallback (Future)

When the rule engine cannot resolve a case (e.g., novel fraud pattern), the framework **optionally** delegates to an LLM for a decision. The LLM receives:
- The full workflow context (current state, entity data, conversation history)
- Decision criteria from the rule engine (what could not be resolved)
- Expected output schema (JSON)

**This is deferred for future discussion.** The mechanism for how the LLM understands the workflow and makes correct decisions (e.g., via a skill or prompt construction) requires separate design.

#### Option C: Rule Engine Only — No Fallback, Direct Error (Strict mode)

Security-critical deployments disable LLM fallback entirely. If the rule engine cannot resolve → escalate to `on_unresolved_decision` node (typically human review or termination).

### 3.3 Decision Output Contract

Every decision node produces a structured result:

```yaml
# DecisionResult schema
DecisionResult:
  route: string                                  # target node name
  reason: string                                 # why this route was chosen (audit trail)
  confidence: number                             # optional, 1.0 for rule engine; variable for LLM fallback
  source: rule_engine | llm_fallback | default   # origin of the decision
```

### 3.4 Decision Evals

LLM-based decisions (Option B) require an eval framework:

```
EvalCase {
  input:    dict         # entity state fed to decision node
  expected: DecisionResult   # expected routing decision
  tolerance: float       # acceptable confidence threshold (default: 0.7)
}
```

Framework runs evals on each LLM decision model change. Must pass ≥ 95% of eval cases before deployment. Eval cases cover:
- Edge cases (boundary risk scores)
- Ambiguous inputs (missing optional fields)
- Safety-critical cases (must never route `high_risk → auto_approve`)

### 3.5 Comparison Matrix

| Dimension | Option A (Rule Engine) | Option C (Strict) |
|-----------|----------------------|-------------------|
| Determinism | 100% | 100% |
| Coverage | Closed-world rules | Closed-world rules |
| Unhandled case | Default route | Error → escalate |
| Auditability | Full | Full |
| Use case | Most production | High-security (lead distribution, PII data) |

---

## 4. Phase-Aware Routing + Return Stack

### 4.1 Concept

Every node, when it completes, determines the **next node** based on:

```
next_node = resolve(agentState.phase, intent)
```

Key behaviors:

1. **Normal flow**: `phase=collect_lead_purpose` + `intent=provide_information` → route to `validate_lead_purpose`
2. **Mid-flow question**: `phase=collect_lead_purpose` + `intent=ask_question` → route to `rag_faq` sub-workflow
3. **Return after question**: when `rag_faq` completes → return to **the previous phase** (`collect_lead_purpose`)

The framework maintains a **phase return stack** to support this. When a mid-flow question detours, the current phase is pushed onto the stack. When the question is answered, the stack is popped, and the workflow resumes at the previous phase.

### 4.2 Phase Return Stack

```
agentState = {
    phase:          "collect_lead_purpose",   // current phase
    phase_stack:    [],                         // push/pop for mid-flow detours
    collectedFields: { ... },                   // accumulated entity data
    ...
}
// See [Domain Model §10.1](./2026-06-17-domain-model-design.md) for the canonical AgentState schema.
```

**Flow example:**

```
1. User: "I want a mortgage for my apartment"
   phase = "collect_lead_purpose"
   
2. Agent: "What's your address?"
   (waiting for user input)
   
3. User: "What does fixed rate cover?"
   intent = ask_question
   → phase_stack.push("collect_lead_purpose")    // save current phase
   → route to rag_faq sub-workflow               // answer question
   
4. Agent: "Fixed rate mortgages have a consistent interest rate throughout the loan term..."
   rag_faq complete
   → phase = phase_stack.pop()                    // restore: "collect_lead_purpose"
   → agent continues: "So, what's your address?"
```

### 4.3 Node Next-Step Resolution

The framework resolves the next node by looking up `(current_phase, detected_intent)` in a phase routing table:

```yaml
# Phase routing table — next node resolved from (phase, intent)
phase_routing:
  collect_lead_purpose:
    provide_information: validate_lead_purpose     # normal flow
    ask_question: rag_faq                            # detour (push phase → answer → pop → resume)
    cancel: terminate                                # exit (pop stack if non-empty, else terminate)
  validate_lead_purpose:
    provide_information: assign_lead
    ask_question: rag_faq
    cancel: terminate
  # ... additional phases added per domain
```

### 4.4 Phase Continuity

The zelkim "once transactional, always transactional" pattern is reframed as: **phase determines routing, not a binary mode flag.** When `phase` is a transactional phase (e.g., `collect_lead_purpose`), the routing always stays within the transactional branch — questions detour but return, and the phase stack ensures continuity.

```yaml
# Phase definition includes routing map
phases:
  collect_lead_purpose:
    entity: lead_purpose
    transitions:
      provide_information: validate_lead_purpose
      ask_question: rag_faq                    # detour → return after
      cancel: terminate
```

---

## 5. Sub-Workflow

### 5.1 Concept

**Sub-workflows are the definition language for A2A (Agent-to-Agent) communication.** They define *what* agents communicate and *how* they coordinate — the inputs, outputs, permissions, and execution contracts between agents. See [A2A Protocol spec](./2026-06-17-a2a-protocol.md) for the runtime protocol that sub-workflows execute over (agent discovery, capability negotiation, task lifecycle, message formats).

Sub-workflows are **complete, standalone workflows** with the same structure as the super workflow — their own domain model (entities, states, transitions), permission model, retry budgets, and routing. Shared capabilities (RAG FAQ, lead verification, lead distribution) are defined once and invoked from any state in any parent workflow.

This prevents the zelkim anti-pattern where RAG logic is duplicated across conversational and transactional branches.

**Deadlock protection:** Sub-workflows must not create circular invocation chains (A → B → A). The framework enforces this at two levels:
- **Depth limit:** `max_sub_workflow_depth: 3` — after 3 nested sub-workflow levels, the conversation terminates with `errorNode`
- **Cycle detection:** The framework tracks the sub-workflow call stack. If a sub-workflow is invoked while already present in the stack, the call is rejected with `StateConflictError` and routes to `errorNode`

### 5.2 Full Workflow Structure

A sub-workflow has the **exact same structure** as a super workflow. No reduced subset:

```yaml
# sub-workflows/rag_faq.yaml — complete workflow
domain: rag_faq
version: 1.0.0
description: "Answer user questions using RAG knowledge base"

entities:
  question_input:
    fields:
      question:
        type: string
        required: true
      conversation_context:
        type: string
        required: false
  answer_output:
    fields:
      answer:
        type: string
        required: true
      sources:
        type: list
        required: false

states:
  search_knowledge_base:
    entity: question_input
    executor: code
    execute: search_vector_db
    permission:
      allowed_tools: [vector_search_mcp]
      allowed_transitions: [generate_answer]
    retry_budget:
      max_attempts: 2
      timeout_ms: 10000

  generate_answer:
    entity: answer_output
    executor: llm
    output_schema: { answer: string, sources: string[] }
    retry_budget:
      max_attempts: 4    # 3 base + 1 LLM extra

  return_to_caller:
    executor: code

transitions:
  - from: search_knowledge_base
    to: generate_answer
    guard: "question != null"
  - from: generate_answer
    to: return_to_caller
    guard: "answer != null"
```

### 5.3 Node Orchestration Within Sub-Workflow

Nodes within a sub-workflow support three orchestration patterns. **LangGraph natively supports all three** via its `Send` API, conditional edges, and sub-graph composition.

#### Pattern A: Serial (Sequential)

```
[A] → [B] → [C] → [D]
```

Standard edge routing. Each node completes before the next starts.

```yaml
transitions:
  - from: search_kb
    to: filter_results
  - from: filter_results
    to: generate_answer
  - from: generate_answer
    to: return_to_caller
```

#### Pattern B: Parallel (Fan-Out / Fan-In)

```
         ┌→ [B1] ─┐
[A] ──→  ├→ [B2] ─┼──→ [C]
         └→ [B3] ─┘
```

LangGraph `Send` API fans out to multiple nodes simultaneously. All must complete before converging at C.

```yaml
# Fan-out from A to multiple B nodes
parallel_nodes:
  from: search_kb
  fan_out:
    - search_policy_db       # search policy knowledge base
    - search_lead_db           # search lead knowledge base
    - search_faq_db          # search FAQ database
  fan_in: merge_results      # converge here when all 3 complete
```

#### Pattern C: Mixed (DAG)

```
         ┌→ [B] ─→ [C] ─┐
[A] ──→  │               ├──→ [E]
         └→ [D] ─────────┘
```

Serial and parallel combined. LangGraph supports arbitrary DAG topologies via conditional edges + `Send`.

```yaml
# DAG: serial chain B→C runs in parallel with D
parallel_nodes:
  from: classify_query
  fan_out:
    - chain:                    # serial sub-chain
        - extract_entities
        - validate_entities
    - search_knowledge_base     # single parallel node
  fan_in: synthesize_response
```

### 5.4 Sync vs Async Invocation

| Mode | Behavior | Use Case |
|------|----------|---------|
| **Sync** | Parent waits for sub-workflow to complete, then resumes | RAG FAQ (must get answer before continuing) |
| **Async** | Parent fires sub-workflow and continues immediately; result delivered via callback or polling | Audit logging, notification, background verification |

```yaml
# Sync invocation (default)
handle_question_in_quote:
  executor: sub_workflow
  sub_workflow: rag_faq
  mode: sync
  on_return: collect_lead_purpose

# Async invocation
background_risk_check:
  executor: sub_workflow
  sub_workflow: lead_verification
  mode: async
  on_complete: risk_result_received     # callback when async sub-workflow finishes
```

### 5.5 Sub-Workflow Nesting

Sub-workflows can recursively define child sub-workflows. A `rag_faq` sub-workflow can itself invoke a `translate_query` sub-workflow, which can invoke further sub-workflows. Each level has its own isolated state, phase stack, and retry budgets.

```yaml
# rag_faq calls translate_query as a sub-sub-workflow
states:
  translate_query:
    executor: sub_workflow
    sub_workflow: translate_query
    mode: sync
    on_return: search_knowledge_base
```

### 5.6 Invocation from Parent

```yaml
# In parent workflow
states:
  handle_question_in_quote:
    executor: sub_workflow
    sub_workflow: rag_faq                              # registered sub-workflow
    mode: sync                                          # sync | async
    input_mapping:
      question: "{{state.last_user_message}}"
      conversation_context: "{{state.conversation_history}}"
    on_return: collect_lead_purpose                    # resume parent phase after return
```

### 5.7 LangGraph Support Summary

| Feature | LangGraph API | Supported |
|---------|--------------|-----------|
| Serial node chain | `add_edge("A", "B")` | ✅ |
| Parallel fan-out/fan-in | `Send()` API | ✅ (v0.2+) |
| Conditional routing | `add_conditional_edges()` | ✅ |
| Sub-graph composition | `StateGraph` nesting | ✅ |
| Checkpoint/resume (sync) | `checkpointer` | ✅ |
| Async execution | `ainvoke()` / `astream()` | ✅ (v0.2+) |
| Mixed DAG | Send + conditional edges combined | ✅ |

---

## 6. Retry & Error Handling

### 6.1 Core Principle: All Errors → errorNode

No per-category dispatch. No multi-link escalation chain. **All errors, all timeouts, all retry-exhausted failures — route to a single `errorNode` for unified handling.** The `errorNode` is the one place where error recovery logic lives.

### 6.2 Retry Budget

Every node has a retry configuration:

```yaml
retry_budget:
  max_attempts: 3
  backoff: exponential            # linear | exponential | fixed
  base_delay_ms: 500
  max_delay_ms: 10000
  jitter: true                    # add randomness to prevent thundering herd
  timeout_ms: 30000               # per-attempt timeout
  on_exhausted: errorNode          # ALWAYS errorNode
```

**LLM nodes get +1 extra retry.** If `max_attempts` is 3, LLM nodes retry 4 times. This compensates for LLM non-determinism (transient hallucinations, malformed JSON).

The effective retry count is `max_attempts + 1` for LLM nodes (to compensate for non-determinism), and `max_attempts` for all other node types.

### 6.3 Error Classification (Required Before Strategy Selection)

> **New in v0.6.0.** Before selecting a recovery strategy, the errorNode MUST classify the error into one of three types. The classification determines which strategies are valid — not all strategies work for all error types.

Errors are classified into **three types** based on whether retrying the same operation could succeed:

| Type | Can retry succeed? | Examples | Valid strategies |
|------|-------------------|----------|-----------------|
| **transient** | ✅ Yes — the error is temporary | API timeout, 429 rate limit, 502/503, network blip, LLM provider overload | `retry_with_backoff` (before errorNode), `fallback_value`, `graceful_degradation` |
| **permanent** | ❌ No — same input will always fail | 400 bad request, 401 auth fail, schema validation error, field out of range, content_refusal, missing required field | `ask_clarify` (if user data), `fallback_value` (if system down), `graceful_degradation`, `dead_letter_queue`, `escalate_to_human`, `terminate` |
| **partial** | ⚠️ Depends — some steps succeeded | Sub-workflow completed 2 of 3 steps, multi-intent: one succeeded one failed | `graceful_degradation`, `dead_letter_queue`, `terminate` |

```yaml
# Error classification rules (configurable)
error_classification:
  transient:
    - http_timeout
    - http_429_rate_limit
    - http_502
    - http_503
    - network_error
    - llm_provider_overload
    - circuit_breaker_open

  permanent:
    - http_400_bad_request
    - http_401_unauthorized
    - http_403_forbidden
    - schema_validation_error
    - field_out_of_range
    - missing_required_field
    - content_refusal              # LLM safety refusal — do NOT retry
    - business_rule_violation
    - permission_denied

  partial:
    - sub_workflow_partial_success
    - multi_intent_partial_fail
    - parallel_node_partial_fail
```

> **Why classify?** Because retrying a permanent error wastes budget and delays the user. Retrying a `content_refusal` (LLM safety rejection) is pointless — the model will refuse again. Retrying a `field_out_of_range` with the same value will fail again. Classification prevents these waste cycles.

### 6.4 Error Categories (for audit logging)

> The 7 error categories below (introduced in v0.4.0) are retained for audit logging and are orthogonal to the three error types in §6.3. A category answers "what kind of system failed?"; a type answers "can retry fix it?". Every error has both a category and a type.

| Category | Type (typically) | Examples |
|----------|-----------------|---------|
| `llm_error` | transient or permanent | LLM timeout (transient), malformed JSON (transient), hallucination guardrail (permanent), content_refusal (permanent) |
| `api_error` | transient or permanent | API timeout (transient), 5xx (transient), 400 (permanent), 401 (permanent) |
| `tool_error` | transient or permanent | MCP server unavailable (transient), command non-zero exit (permanent) |
| `validation_error` | permanent | Data invariant violation, type mismatch, field out of range |
| `business_rule_error` | permanent | Loan amount out of range, duplicate lead |
| `permission_error` | permanent | Unauthorized tool call, forbidden transition |
| `unrecoverable_error` | permanent | Corrupted state, missing required entity |

### 6.5 Structured Error Schema

> **New in v0.6.0.** Errors are not just a category + message string. They carry structured context that enables programmatic strategy selection, root-cause analysis, and cross-agent tracing.

```yaml
# Structured error envelope — used by errorNode, A2A error responses, and audit trail
FrameworkError:
  # --- Identity ---
  error_id: string                 # UUID — unique per error occurrence
  correlation_id: string           # ties to the conversation/request that caused it
  timestamp: string                # ISO 8601

  # --- Classification ---
  category: string                 # one of 7 categories (§6.4)
  type: string                     # transient | permanent | partial (§6.3)
  error_code: string               # machine-readable code (e.g., "FIELD_OUT_OF_RANGE")
  retryable: boolean               # derived from type: transient=true, permanent=false

  # --- Context ---
  source:
    agent_id: string               # which agent/workflow produced this error
    node_id: string                # which node failed
    layer: string                  # L1 | L2 | L3
  message: string                  # human-readable error description
  
  # --- Details (error-code-specific) ---
  details:                         # structured fields for programmatic analysis
    field: string                  # which field caused the error (if applicable)
    received_value: any            # what was provided
    expected: string               # what was expected (range, type, enum)
    constraint: string             # which constraint was violated

  # --- Root Cause Chain (for A2A / multi-agent) ---
  root_cause:                      # nested FrameworkError — if this error was caused
    error_id: string               # by another agent's error, the original error is
    agent_id: string               # preserved here (read-only, not modified)
    error_code: string             # each layer appends my_context but never deletes
    message: string                # root_cause
    details: {}
    root_cause: FrameworkError     # can nest further (C's error inside B's inside A's)
  
  # --- Recovery hints ---
  suggested_strategies: string[]   # errorNode may suggest which strategies fit
  user_facing_message: string      # only set at the top level (A knows user context)
```

**Design rules for root_cause chain:**
1. Each layer appends `my_context` (its own perspective) but **never modifies or deletes** `root_cause`
2. `retryable` is inherited from the deepest `root_cause` — if C says not retryable, B and A inherit
3. `user_facing_message` is only generated at the **top-level agent** (the one talking to the user)
4. `correlation_id` is shared across the entire chain — enables trace store lookup (see A2A §6.3)

**Example — credit_score=7200 out of range (3-agent chain):**

```yaml
# Agent A (mortgage) receives this error from Agent B (check_rates)
# which received it from Agent C (eligibility)

FrameworkError:
  error_id: "err-aaa"
  correlation_id: "conv-123"
  timestamp: "2026-06-25T10:00:03Z"
  category: validation_error
  type: permanent
  error_code: "RATE_CHECK_FAILED"
  retryable: false
  source:
    agent_id: "mortgage"
    node_id: "handle_rate_query"
    layer: "L2"
  message: "cannot calculate rate, eligibility rejected input"
  details:
    my_context: "user asked for rate quote during lead collection"
  root_cause:
    error_id: "err-bbb"
    agent_id: "check_rates"
    error_code: "DEPENDENCY_FAILED"
    message: "eligibility check rejected the input"
    details:
      my_context: "rate calculation requires eligibility first"
    root_cause:
      error_id: "err-ccc"
      agent_id: "eligibility"
      error_code: "FIELD_OUT_OF_RANGE"
      message: "credit_score=7200 out of range 300-850"
      details:
        field: "credit_score"
        received_value: 7200
        expected: "300-850 (US FICO range)"
        constraint: "range_check"
      root_cause: null          # original cause — no further nesting
  suggested_strategies: ["ask_clarify"]   # user likely mistyped 720 as 7200
  user_facing_message: "The credit score 7200 is outside the valid range (300-850). Did you mean 720?"
```

### 6.6 Recovery Strategies (Canonical Definition — 8 Strategies)

> **This is the canonical, authoritative definition of errorNode strategies.** All other spec documents (state-machine, extraction-layer, response-generation, A2A-protocol) that reference errorNode strategies MUST cross-reference this section as the single source of truth. Any discrepancy between this section and another spec's mention of errorNode is a spec bug — this section takes precedence.

| # | Strategy | Applicable error type | Behavior | When to use |
|---|----------|----------------------|----------|-------------|
| 1 | `retry_with_backoff` | transient | Retry with exponential backoff + jitter | API timeout, 429, 502/503. Runs BEFORE errorNode (in retry budget). Listed here for completeness. |
| 2 | `retry_with_context` | permanent (LLM quality) | Re-invoke failed node with error context injected into prompt | LLM returned valid JSON but wrong content (type mismatch, missing field). NOT for safety refusals. |
| 3 | `ask_clarify` | permanent (user data) | Re-prompt user with a clarification question | User input caused the error (field out of range, ambiguous input). NOT for system errors. |
| 4 | `fallback_value` | permanent (system down) | Use configured default value, log warning, continue | External dependency unavailable AND a reasonable default exists. NOT for user data errors (use ask_clarify). |
| 5 | `graceful_degradation` | partial or permanent | Return partial results, continue with reduced functionality | Non-core sub-task failed; or multi-intent where one intent succeeded. Don't fail the whole conversation for a non-core failure. |
| 6 | `dead_letter_queue` | permanent (all auto-recovery failed) | Store failed request in DLQ, return acknowledgment to user, continue | All automated strategies exhausted. Regulated industries: never lose a request. User gets a receipt; ops team handles it async. |
| 7 | `escalate_to_human` | permanent (permission/security) | Queue for human review, suspend conversation | Permission denied on dangerous_operation_write, or requires real-time human judgment. NOT for system timeouts (use fallback/degradation). |
| 8 | `terminate` | permanent (unrecoverable) | Graceful exit with message + audit log | Corrupted state, auth failure after retries, suspected adversarial input. No recovery possible. |

**Strategy selection rules:**
- `retry_with_backoff` runs in the retry budget (§6.2) BEFORE errorNode is invoked
- `retry_with_context` is for LLM nodes only (Layer 1 extraction, Layer 3 response)
- `ask_clarify` is NOT for system errors — don't ask the user "the API timed out, can you clarify?"
- `fallback_value` is NOT for user data errors — don't silently replace user's bad input with a default
- `graceful_degradation` is preferred over `terminate` when partial success is meaningful
- `dead_letter_queue` is preferred over `escalate_to_human` when the error doesn't need real-time human judgment
- `terminate` is the last resort — only when no other strategy applies

### 6.7 Strategy Decision Matrix

```
Error occurs
    │
    ├─ type = transient?
    │   ├─ retry budget remaining → retry_with_backoff (in §6.2, not errorNode)
    │   └─ retry budget exhausted → treat as permanent (fall through)
    │
    ├─ type = permanent?
    │   ├─ is user data error?
    │   │   ├─ can ask user → ask_clarify
    │   │   └─ has default value → fallback_value (with audit warning)
    │   │
    │   ├─ is system/dependency error?
    │   │   ├─ has default value → fallback_value
    │   │   ├─ non-core failure → graceful_degradation
    │   │   ├─ core failure, no default → dead_letter_queue
    │   │   └─ core failure, needs real-time judgment → escalate_to_human
    │   │
    │   ├─ is LLM quality error?
    │   │   ├─ format/content issue → retry_with_context
    │   │   └─ content_refusal → dead_letter_queue (do NOT retry safety refusal)
    │   │
    │   ├─ is permission/security error?
    │   │   ├─ needs approval → escalate_to_human
    │   │   └─ suspected attack → terminate
    │   │
    │   └─ unrecoverable? → terminate
    │
    └─ type = partial?
        ├─ failed part is non-core → graceful_degradation (return success part)
        ├─ failed part is core, retryable → dead_letter_queue (async retry)
        └─ failed part is core, not retryable → escalate_to_human or terminate
```

### 6.8 errorNode Interface (Canonical Definition)

> **This is the canonical, authoritative definition of the errorNode interface.** All other spec documents that reference the errorNode input/output contract MUST cross-reference this section. Any discrepancy between this section and another spec's mention of errorNode I/O is a spec bug — this section takes precedence.

```yaml
# errorNode contract — v0.6.0
errorNode_input:
  error: FrameworkError             # structured error (§6.5), not just category + message
  source: string                    # which node failed
  attempts: integer                 # retries attempted before exhaustion
  conversation_state: AgentState     # current state for context

errorNode_output:
  action: string                    # one of 8 strategies (§6.6)
  correction: object                # correction instruction applied to the failed node
  user_message: string              # user-facing message (generated from error + context)
  audit_entry: object               # structured audit record
  # For dead_letter_queue:
  dlq_entry:                        # only present when action = dead_letter_queue
    original_request: object        # the failed request, preserved for later retry
    error: FrameworkError           # full error context
    retry_after: string             # suggested retry time (ISO 8601 or null)
```

### 6.9 Flow Diagram (Updated)

```
Node execution
    │
    ├── success ──→ next node
    │
    └── failure
          │
          ├── classify error (§6.3): transient | permanent | partial
          │
          ├── type = transient?
          │     ├── retry budget remaining → retry_with_backoff (jitter)
          │     └── retry budget exhausted → errorNode
          │
          ├── type = permanent?
          │     └── errorNode
          │           ├── user data error → ask_clarify
          │           ├── system down → fallback_value / graceful_degradation
          │           ├── LLM quality → retry_with_context
          │           ├── LLM safety refusal → dead_letter_queue
          │           ├── permission/security → escalate_to_human / terminate
          │           ├── all auto-recovery failed → dead_letter_queue
          │           └── unrecoverable → terminate
          │
          └── type = partial?
                └── errorNode
                      ├── non-core failure → graceful_degradation
                      └── core failure → dead_letter_queue / escalate_to_human
```

### 6.10 errorNode Configuration

```yaml
# Global default
error_handling:
  default_strategy: ask_clarify       # default strategy if no per-node override
  max_total_errors: 5                 # conversation-level: after 5 errors → terminate
  max_conversation_duration_ms: 300000  # 5 min hard limit → terminate
  
  errorNode_config:
    retry_with_backoff:
      max_attempts: 3                 # handled in retry budget (§6.2), listed for completeness
      base_delay_ms: 500
      max_delay_ms: 10000
      jitter: true
    
    retry_with_context:
      max_context_retries: 2          # max times to re-invoke with error context
      prompt_strategy: summarize      # carry_forward | reset | summarize
    
    ask_clarify:
      max_clarifications: 3           # max re-prompts before escalating
      on_max_exhausted: escalate_to_human
    
    fallback_value:
      default_values: {}              # per-field defaults
      audit_warning: true             # always log when fallback is used
    
    graceful_degradation:
      partial_response_template: "partial results available: {{successes}}"
      failed_part_message: "{{failed_part}} temporarily unavailable"
    
    dead_letter_queue:
      backend: postgresql             # postgresql | redis | file
      retention_days: 30
      alert_on_count: 10              # alert ops if DLQ has >10 items
      retry_schedule: "0 */6 * * *"   # cron: retry every 6 hours
    
    escalate_to_human:
      queue: "agent_review"
      timeout_minutes: 15
      notification_channel: pagerduty  # pagerduty | slack | email
    
    terminate:
      message_template: "I'm sorry, I ran into an unrecoverable error. Our team has been notified."
      audit_required: true

# Per-node override
nodes:
  distribute_lead:
    error_strategy: escalate_to_human  # lead distribution errors → human
  calculate_rate:
    error_strategy: fallback_value     # use default rate on calc failure
  check_rates:
    error_strategy: ask_clarify        # rate check usually needs user clarification
  submit_lead:
    error_strategy: dead_letter_queue  # never lose a lead submission
```

Conversation-level budgets apply globally across all nodes in a conversation. When `max_total_errors` is exhausted OR `max_conversation_duration_ms` is exceeded, the conversation terminates regardless of per-node retry budget remaining. This bounds worst-case latency and prevents adversarial loops.

### 6.11 errorNode → Conversation Continuity

After `errorNode` handles the error, the conversation resumes from the state that triggered the error. The `errorNode` does NOT change the workflow state — it returns a **correction instruction** that the framework applies to the failed node.

### 6.12 Relationship with Extraction Layer

The Extraction Layer's `max_transform_attempts` is separate from Layer 2's node-level `retry_budget`. Extraction retries handle field-level corrections; Layer 2 retries handle node-level execution failures. Both route to `errorNode` on exhaustion.

---

## 7. Permission Model

### 7.1 Two-Level Enforcement

| Level | When | How |
|-------|------|-----|
| **Config-level** | Workflow load time (static) | YAML allowlists: `allowed_tools`, `allowed_transitions` |
| **OAuth / Role-based** | Runtime (dynamic) | User context: what is the authenticated user authorized to do? |

### 7.2 NodePermission Schema

```yaml
# Defined per node in workflow YAML
permission:
  allowed_tools:
    - calculate_rate_api        # read: can call rate calculation
    - lead_distribution_api            # dangerous_operation_write: can distribute leads
    - vector_search_mcp            # read: can query knowledge base
  allowed_transitions:
    - assign_lead
    - manual_review
    - distribute_lead               # can route to these states
  # deny_all_transitions_except: true   # strict mode
```

### 7.3 Tool Classification

> **Note:** The canonical `ToolMeta.type` enum (`api | mcp | command | llm | a2a | sdk`) is defined in [HLD §4.4](./2026-06-16-deterministic-workflow-framework-design.md). This section extends it with routing-specific detail.

Every tool (API, MCP server, command, LLM call) has metadata:

```yaml
tools:
  calculate_rate_api:
    type: api
    access_level: read
    description: "Calculate mortgage rate based on loan purpose + financial profile data"
    endpoint: POST /api/v1/rate/calculate
    timeout_ms: 5000

  lead_distribution_api:
    type: api
    access_level: dangerous_operation_write
    description: "Submit lead through the lead distribution engine"
    endpoint: POST /api/v1/leads/submit
    timeout_ms: 15000
    requires_approval: true       # human-in-the-loop gate

  vector_search_mcp:
    type: mcp
    access_level: read
    description: "Semantic search over mortgage knowledge base"
    server: knowledge_base_mcp
    tool_name: search_documents

  run_lead_scoring_model:
    type: command
    access_level: read
    description: "Execute mortgage lead scoring model"
    command: "python /opt/models/lead_scoring.py"
    timeout_ms: 30000
```

### 7.4 Tool Interface

Every tool conforms to a standard contract (defined in [HLD §4.4](./2026-06-16-deterministic-workflow-framework-design.md)). The framework checks permissions before invoking the tool's execution function.

```yaml
# Tool contract (interface) — type enum: see HLD §4.4
Tool:
  name: string                                        # unique tool identifier
  type: ToolMeta.type                                 # canonical enum in HLD §4.4
  access_level: read | write | sensitive_data_read | dangerous_operation_write
  metadata: ToolMeta                                  # endpoint, timeout, approval (see §7.3)
  # execute: (params: object, context: ExecutionContext) → ToolResult
  #   Framework calls this after permission check passes.

# ToolResult schema
ToolResult:
  success: boolean
  data: object
  error: string                                       # null if success
  duration_ms: integer
  audit_entry: AuditEntry                             # auto-generated by framework
```

### 7.5 Access Level Matrix

| Access Level | Examples | Extra Controls |
|-------------|----------|---------------|
| `read` | Vector search, rate calculation, policy lookup | None |
| `write` | Save quote, update profile, log event | Audit trail |
| `sensitive_data_read` | View PII, medical records, credit score | OAuth scope + audit |
| `dangerous_operation_write` | Distribute lead, cancel application, delete data | Human approval gate + OAuth + audit |

### 7.6 OAuth / Role-Based Enforcement

At runtime, the framework enforces a two-level permission check for every tool invocation:

1. **Config-level:** The tool must be in the node's `allowed_tools` list (see §7.2).
2. **Role-level:** The authenticated user's OAuth scopes must satisfy the tool's `access_level`.

```yaml
# Permission enforcement rules (evaluated per tool invocation)
permission_enforcement:
  # Level 1: Static config — tool must be in node's allowlist
  config_check:
    rule: "tool.name in node.permission.allowed_tools"
    on_violation: deny

  # Level 2: OAuth scope check (runtime, per authenticated user)
  scope_requirements:
    read: []                                          # no scope needed
    write: []                                         # audit trail only, no scope needed
    sensitive_data_read: ["sensitive_data:read"]
    dangerous_operation_write: ["dangerous_operation:write"]

  # Human-in-the-loop gate for dangerous operations
  approval_gate:
    condition: "tool.metadata.requires_approval == true"
    action: await_human_approval                      # blocks until approved
```

### 7.7 Transition Permission

Nodes also restrict which other nodes they can transition to. The framework enforces this on every state transition:

```yaml
# Transition permission enforcement (evaluated per transition)
transition_enforcement:
  rule: "to_node in from_node.permission.allowed_transitions"
  on_violation:
    error: TRANSITION_DENIED
    message: "Node '{{from_node}}' cannot transition to '{{to_node}}'. Allowed: {{allowed_transitions}}"
```

---

## 8. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | How does the LLM (in Option B decision nodes) understand the full workflow context to make correct decisions? Prompt construction? Skill-based injection? | LLM decision reliability |
| 2 | Should sub-workflows support recursion (sub-workflow calling another sub-workflow)? | Workflow complexity |
| 3 | Should retry budgets be cumulative or per-node? (i.e., global conversation-level retry budget + per-node allocation) | Resource management |
| 4 | For OAuth enforcement, should the framework integrate with specific providers (Auth0, Okta) or expose a generic interface? | Integration surface |
| 5 | How are sensitive data tool results handled — auto-redaction? Separate audit channel? | PII compliance |
| 6 | Should the framework support suspending/resuming sub-workflows (checkpoint at sub-workflow boundary)? | Long-running workflows |
| 7 | LLM decision evals — automated CI pipeline or manual review per change? | Quality assurance process |
| 8 | `errorNode` — should it be a single global node or per-workflow configurable? | Error handling flexibility |
| 9 | async sub-workflow + parent concurrent write to same `collectedFields` key — `conflict_detect` by default or `last_write_wins`? | State safety vs developer ergonomics |
| 10 | Should the framework surface a `StateConflictError` to the developer (for debugging) or silently resolve via merge strategy? | Debugability |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — parent architecture, framework principles, permission model overview
- [State Machine Design](./2026-06-16-state-machine-design.md) — transition mechanics, state metadata, guard expressions
- [Domain Model Design](./2026-06-17-domain-model-design.md) — entity/state/transition schema
- [Extraction Layer Design](./2026-06-17-extraction-layer-design.md) — Extract/Validate/Transform interfaces
- [A2A Protocol](./2026-06-17-a2a-protocol.md) — Agent-to-Agent runtime protocol (discovery, negotiation, task lifecycle, message formats)
- zelkim/langgraph-insurance-chatbot — phase-aware routing pattern, sub-workflow anti-pattern
- Prodigal Payment Collection Agent — per-phase retry budgets, tool execution pattern
