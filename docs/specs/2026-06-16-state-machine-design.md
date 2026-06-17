# State Machine Layer Design — transitions + LangGraph Fusion

> See also: [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) for overall architecture and non-FSM concerns.
> All concrete workflow examples have been extracted to [examples/home-insurance/](../../examples/home-insurance/).

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-16 | 0.1.0 | Initial design: transitions as source of truth, LangGraph as infra layer |
| 2026-06-16 | 0.2.0 | Add state metadata (precondition, postcondition, guards, invariants) |
| 2026-06-16 | 0.3.0 | Add invoice and payment use cases; full English translation |
| 2026-06-16 | 0.4.0 | Add Section 8: Intent + State resolution (per-state intent policy, confirmation flow) |
| 2026-06-16 | 0.5.0 | Extract all examples to examples/home-insurance/; remove invoice/payment appendices; unify on home insurance domain |

---

## 1. Core Principle

> **transitions defines WHAT (business correctness). LangGraph executes HOW (conversation infrastructure).**
>
> Developers maintain only the transitions definition. The LangGraph graph, LLM nodes, checkpointing, and interrupt are all auto-generated.

---

## 2. transitions Definition Format (Single Source of Truth)

> **Developers maintain only the transitions definition.** The LangGraph graph, LLM nodes, checkpointing, and interrupt are all auto-generated from this single YAML file.

For the complete definition format and a concrete home insurance workflow, see [workflow.yaml](../../examples/home-insurance/workflow.yaml). The format supports:

- **states**: typed nodes (`executor: llm | code`) with schemas, guards, metadata, and tool allowlists
- **transitions**: named edges with guard expressions and self-loops
- **Meta-variables**: framework-generated flags (`context_incomplete`, `exit_guard_pass`, `all_approved`, etc.) usable in guard expressions

---

## 3. State Metadata — Precondition / Postcondition / Guard / Invariant

Each state can carry 5 types of metadata, enforced at different points in the state lifecycle:

```
                  +---------------------------------------+
                  |  precondition                          |
                  |  "What must be true before entry"       |
                  |  (design contract — static verification)|
                  +------------------+--------------------+
                                     |
                  +------------------v--------------------+
                  |  entry_guard                           |
                  |  "Final check at the door"             |
                  |  (runtime — reject on failure)         |
                  +------------------+--------------------+
                                     | passed
              +----------------------v------------------------+
              |            STATE: calculate                    |
              |                                                |
              |   +----------------------------------------+  |
              |   |  data_invariant                         |  |
              |   |  "What must hold while in this state"    |  |
              |   |  (runtime — assertion error on violation)|  |
              |   +----------------------------------------+  |
              |                                                |
              |   action: compute_premium(data)                 |
              |                                                |
              |   +----------------------------------------+  |
              |   |  exit_guard                              |  |
              |   |  "One more check before leaving"          |  |
              |   |  (runtime — block transfer, route elsewhere)|  |
              |   +------------------+---------------------+  |
              +----------------------+------------------------+
                                     | passed
                  +------------------v--------------------+
                  |  postcondition                         |
                  |  "What must be true after exit"         |
                  |  (design contract — static verification)|
                  +---------------------------------------+
```

### 3.1 Definitions

| Concept | Trigger Timing | Failure Behavior | Purpose |
|---------|---------------|------------------|---------|
| **precondition** | Before entry | Does not block runtime; static analysis reports contract violation | Design contract for test generation |
| **entry_guard** | At entry | Runtime rejection; routes to fallback or error state | Runtime safety gate |
| **data_invariant** | Throughout state lifetime | Runtime AssertionError; interrupts workflow | Runtime data integrity protection |
| **exit_guard** | At exit | Runtime block; routes to alternate branch | Branch routing based on computed result |
| **postcondition** | After exit | Does not block runtime; verification tool reports violation | Ensures action function output contract |

> **Note on static verification:** The "static analysis" and "verification tool" referenced above refers to a planned YAML linter and test generator (design TBD) that reads preconditions, postconditions, and invariants to catch contract violations before deployment. This tooling is out of scope for the current design document; see Appendix C.7 for related open questions.

### 3.2 Example Patterns

> For a complete state annotated with all 5 metadata fields, see `assess_risk` and `calculate_premium` states in [workflow.yaml](../../examples/home-insurance/workflow.yaml). Below are the key behavioral patterns.

**Guard vs Contract:**

```
                      Guard                          Contract
                      (entry_guard / exit_guard)     (precondition / postcondition)

  Timing              Runtime                         Offline (static analysis / test generation)
  Failure behavior    Routes to fallback / error       Marks as "contract violation", does not block execution
  Typical use         "age < 18 -> direct reject"      "This state declares it needs age; generate test with age<18"
  Expression req.     Must be runtime-evaluable        Can be descriptive comment or formal formula
```

### 3.3 Complete State Field Reference

```yaml
states:
  - name: <state_name>
    executor: llm | code

    # --- State Metadata (all optional) ---
    precondition:     "expression or comment"
    entry_guard:      "runtime-evaluated boolean expression"
    data_invariant:   "constraint monitored throughout state lifetime"
    exit_guard:       "boolean expression evaluated on exit"
    postcondition:    "expression or comment"

    # --- Data Schemas (optional, recommended) ---
    input_schema:     {field: type, ...}     # data required from upstream state
    context_schema:   {field: type, ...}     # working memory while in this state
    output_schema:    {field: type, ...}     # data produced for downstream states

    # --- Execution ---
    action:           "function name (required for code executor)"
    prompt:           "system prompt (required for llm executor)"
    tool_allowlist:   [...]                  # tools the LLM may call in this state
    human_review:     true | false           # whether to interrupt for human approval
    review_prompt:    "what the approver sees"
    stream:           true | false           # whether to stream LLM output
    on_exit:          "callback function run after state completes"
    on_error:         <fallback_state>       # state to enter on unhandled error
    description:      "human-readable note about what this state does"

    # --- Guard Meta-Variables (framework-generated, usable in guard expressions) ---
    # These are not user-defined fields. The framework sets them automatically:
    #   exit_guard_pass    — true if all exit_guard constraints passed
    #   exit_guard_blocked — true if any exit_guard constraint failed
    #   context_complete   — true when the LLM confirms it has all needed data
    #   context_incomplete — true when the LLM needs more info (drives self-loop)
    #   all_approved       — true when all required human approvals received
    #   any_rejected       — true when any human approval was rejected
    #   any_field_missing  — true when output_schema has null required fields
    #   retries_exhausted  — true when LLM or code node has exceeded max retries
```

### 3.4 Guard Expression Syntax

Guard expressions support:
- **State field access:** `field_name`, `schema.field_name` (e.g., `amount`, `collected_data.age`)
- **Boolean operators:** `AND`, `OR`, `NOT`, `and`, `or`, `not`
- **Comparison operators:** `==`, `!=`, `>`, `<`, `>=`, `<=`
- **List membership:** `field in [a, b, c]`, `field in ['a', 'b', 'c']`
- **Null checks:** `field != null`, `field == null`
- **Meta-variables:** framework-generated flags listed in §3.4
- **Natural language prose:** allowed as fallback when the condition cannot be mechanically evaluated (treated as "not verifiable by static analysis, always raises a warning")

Full formal grammar is deferred to implementation planning (see Appendix C.2).

---

## 4. Auto-Generated LangGraph Graph

The framework auto-generates a LangGraph StateGraph from the YAML transitions definition. Each state becomes one LangGraph node; each transition becomes a conditional edge.

For the generated graph of a complete workflow, see the diagram in [README.md](../../examples/home-insurance/README.md) and the state-by-state walkthrough in [e2e-scenarios.md](../../examples/home-insurance/e2e-scenarios.md).

**Each state -> one LangGraph node. Executor determines node behavior:**

| executor | LangGraph Node Behavior |
|----------|------------------------|
| `llm` | Auto-inject chat history -> call LLM -> stream output -> checkpoint |
| `code` | Execute deterministic action function; inputs/outputs are auditable |

The graph structure mirrors the transitions definition exactly: the nodes are the states, the edges are the transitions with their guard conditions. Self-loops (e.g., `guard: context_incomplete`) keep the conversation in a state until data is complete.

---

## 5. Five-Capability Integration Matrix

| Capability | Mechanism | Integration Point |
|------------|-----------|-------------------|
| **LLM invocation** | executor=llm nodes auto-attach ChatOpenAI | Auto-generated |
| **Streaming output** | executor=llm + stream:true nodes auto-enable .astream_events() | Auto-generated |
| **Conversation persistence** | SqliteSaver.put() auto-called after every node exit | Checkpointer injection |
| **Human-in-the-loop (interrupt)** | executor=llm + human_review:true nodes auto-interrupt() after LLM generation, resume on approval | LangGraph interrupt |
| **Tool calling** | tool_allowlist tools auto-injected into ToolNode | LangGraph ToolExecutor |

---

## 6. End-to-End Walkthrough

> For complete end-to-end conversation examples (quote flow, claim flow, high-risk routing), see [e2e-scenarios.md](../../examples/home-insurance/e2e-scenarios.md). The walkthrough covers:
> - LLM-powered data collection with tool calling
> - Deterministic code execution (risk scoring, premium calculation)
> - Guard-based routing and self-loops
> - Human-in-the-loop interrupt + approval
> - Audit log auto-generation


---

## 7. Why This Architecture Works

| Concern | Resolution |
|---------|------------|
| Maintaining two graphs | Only maintain one YAML; LangGraph graph is generated output, never hand-edited |
| Two state machines conflicting | transitions is the single authority on state; LangGraph is a pure execution engine |
| Too complex | Developer only faces YAML + action functions; generator hides LangGraph details |
| Generator hard to maintain | Generator is itself a deterministic component (YAML in -> graph out), unit-testable |

---

## 8. Intent + State Resolution

### 8.1 Principle

Intent classification (Layer 1) and the state machine (Layer 2) are not independent. An intent has different meanings depending on the current state. The combination of **(intent, current_state)** determines whether a transition is valid, requires confirmation, or is rejected.

### 8.2 Per-State Intent Policy

Each state declares which intents it accepts and how to handle unaccepted intents:

```yaml
states:
  - name: collect_info
    intent_policy:
      accept:
        - provide_information    # user gives data → continue form
        - ask_question           # user asks about coverage → answer within flow
        - decline                # user wants to cancel → confirm then exit
      on_unlisted: ask_confirm   # unrecognized intent → ask user to confirm
```

**Policy behaviors:**

| Behavior | Description |
|----------|-------------|
| `accept` | Intent is valid in this state; proceed with transition |
| `on_unlisted: ask_confirm` | Unlisted intent triggers confirmation: "You're in the middle of [current task]. Do you want to cancel and [new intent]?" |
| `on_unlisted: reject` | Unlisted intent is silently blocked; agent prompts user to continue current task |

### 8.3 Resolution Flow

```
User utterance
      │
      ▼
┌─────────────────┐
│ Layer 1: Intent  │
│ Classification   │ → intent: make_payment, confidence: 0.92
└────────┬────────┘
         ▼
┌─────────────────┐
│ Layer 2: Check   │
│ intent vs state  │
│                  │
│ state=filling_form
│ intent_policy:   │
│   accept:        │
│     - provide_information
│     - ask_question
│     - decline
│   on_unlisted: ask_confirm
│                  │
│ make_payment ∉ accept
└────────┬────────┘
         ▼
┌─────────────────┐
│ ask_confirm:     │
│ "You're filling  │
│  a quote form.   │
│  Cancel and pay?"│
└────────┬────────┘
         ▼
    user responds
         │
    ┌────┴────┐
    ▼         ▼
  "yes"     "no"
    │         │
    ▼         ▼
  state     stay in
  → idle   filling_form
  intent    (re-classify
  → make_   next input)
  payment
```

### 8.4 Example Scenarios

For concrete intent+state resolution examples within home insurance workflows, see [intent-definitions.md](../../examples/home-insurance/intent-definitions.md) and the `intent_policy` sections in [workflow.yaml](../../examples/home-insurance/workflow.yaml).

### 8.5 Relationship to Other State Machine Concerns

- **Retry counters** are independent of intent resolution. A user who triggers `ask_confirm` does not consume a retry attempt — only invalid data inputs (wrong name, wrong code) increment retries.
- **Sensitive field scrubbing** happens on state exit regardless of whether the exit was triggered by a normal transition, a `decline`, or a confirmed intent switch.

## Appendix C: Implementation Planning — Open Questions (State Machine)

> Questions identified during design but deferred for implementation planning.
> For non-FSM questions, see [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) Appendix.

### C.1 State Design

> **Sub-workflow:** a state whose internal logic is itself a complete workflow (nested YAML definition). The parent state delegates execution to the child workflow and resumes when it completes.

| # | Question | Impact |
|---|----------|--------|
| 1 | How to define state data schema? `input_schema` / `context_schema` / `output_schema` three-layer isolation vs flat dict | Audit trace granularity, data isolation safety |
| 2 | Maximum sub-workflow nesting depth? Does deep nesting hurt readability | Workflow reusability, maintainability |
| 3 | Is history state (restore to last active sub-state) needed? Implementation strategy | Complex flow breakpoint recovery |
| 4 | Parent state unified entry/exit behavior — should all children run cleanup/validation when leaving parent | Resource management, leak prevention |
| 5 | Dynamic vs static workflow — can the graph structure be modified at runtime | Flexibility vs determinism conflict |

### C.2 Transition & Guard

> **History state:** a pseudo-state that remembers which sub-state was active when the parent was exited, enabling re-entry at the same point. Standard UML statechart concept.

| # | Question | Impact |
|---|----------|--------|
| 6 | Guard expressiveness boundary: pure functions only? Allow external service calls (DB/API) | Performance, determinism, testability |
| 7 | Guard conflict resolution — what happens when multiple guards are simultaneously true | Runtime behavioral determinism |
| 8 | Guard completeness enforcement — how to statically detect uncovered exit guard cases | Prevents runtime deadlock in a state |
| 9 | Implicit fallback (no-match) design: explicit catch-all vs framework-injected error handler | Compliance — system must not "freeze" |
| 10 | Full guard expression grammar (see §3.5 for current syntax) | Developer experience, security |

### C.3 Parallel States

> **Orthogonal regions:** multiple concurrently active sub-states within a parent state. For example, while in "onboarding", simultaneously run "verify_identity" and "collect_preferences" in parallel. Standard UML statechart concept.

| # | Question | Impact |
|---|----------|--------|
| 11 | Can orthogonal regions communicate (share data/events) | Parallel branch coupling |
| 12 | How do parallel branches converge: all-complete vs any-complete vs timeout | Complex workflow orchestration flexibility |

### C.4 Error & Recovery

| # | Question | Impact |
|---|----------|--------|
| 13 | When code nodes encounter external API failure or DB unavailability, how does the state machine trigger retry/compensation/rollback transitions | State transition reliability |
| 14 | Global error workflow design — unified fallback target state for all uncaught exceptions | Compliance — state machine must not freeze or silently fail |

### C.5 Version Migration

| # | Question | Impact |
|---|----------|--------|
| 15 | How to smoothly migrate in-flight conversation states to a new workflow YAML version | Zero-downtime production updates |
| 16 | How to map old states to new states — auto-inference vs manual mapping table; strategy for state creation/deletion/modification | Migration accuracy |

### C.6 Code Generator

| # | Question | Impact |
|---|----------|--------|
| 17 | How to guarantee YAML definition -> LangGraph graph equivalence | System trust foundation |
| 18 | Generator testability — given YAML input, assert output graph structure is correct | Regression protection |

### C.7 Static Verification

| # | Question | Impact |
|---|----------|--------|
| 19 | Dead state detection — states defined but unreachable by any transition | Code quality |
| 20 | Missing transition detection — states with uncovered event/condition branches | Runtime completeness |
| 21 | Unreachable state detection — states with incoming transitions but unreachable entry | Code quality |
| 22 | Guard conflict detection — two guards that can be simultaneously true pointing to different targets | Runtime non-determinism |
| 23 | Postcondition satisfiability — does the declared postcondition necessarily hold on the normal path | Contract validity |
| 24 | YAML schema strictness — how many errors (field typos, type mismatches) can be caught before deployment | Developer experience |
