# A2A (Agent-to-Agent) Protocol

> Part of [Deterministic Workflow Framework — High-Level Design](./01-deterministic-workflow-framework-design.md)
> Covers: How sub-workflows become agent-to-agent communication — A2A message format, discovery, sync/async semantics, relationship with MCP, and the A2A runtime protocol.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial A2A protocol spec: message format, discovery, sync/async, MCP comparison |
| 2026-06-18 | 0.1.1 | Add cross-reference to [Tool Ecosystem §7.5](./13-tool-ecosystem.md) for `type: a2a` tool integration (A2A agents as node-level tools with multi-turn conversations); sync with Decision 24 |
| 2026-06-25 | 0.2.0 | Add §1.3 A2A as Deterministic Microservice Protocol — clarify that A2A is not limited to autonomous LLM agents; when both caller and callee use the deterministic framework, A2A becomes the agent-world equivalent of microservice communication. Add §3.2 A2A vs API vs LangGraph Subgraph comparison — three integration modes with trade-off matrix and decision framework. Align with VISION §6.8 LLM Positioning (deterministic core + LLM as component). |

---

## 1. Role

A company's business flows are all interconnected — one workflow is another's sub-workflow. The architecture is fundamentally Agent-to-Agent.

Sub-workflows are **NOT** just function calls. They are agent-to-agent interactions — each sub-workflow is itself a complete agent with its own domain model, permission model, retry budgets, and routing. When a parent workflow invokes a sub-workflow, it is delegating a goal to another agent, not calling a subroutine. The callee agent may be deterministic (YAML state machine — see §1.3) or autonomous (LLM-driven); the A2A protocol is the same either way.

```
Parent Workflow (Agent A)
    │
    │  "I need a FAQ answer for this question"
    │  A2A: entities + goal → Agent B
    │
    ▼
Sub-Workflow (Agent B: rag_faq)
    │
    │  executes: search → generate → return
    │  A2A: results + audit → Agent A
    │
    ▼
Parent Workflow resumes with Agent B's output
```

This spec defines **A2A as the runtime communication protocol** between agents. Sub-workflows (see Routing & Execution spec §5) are the **definition language** — they define the agent's domain model, states, transitions, permissions, and retry budgets. A2A is **how agents talk to each other at runtime**.

### 1.1 Key Insight: Every Sub-Workflow is an Agent

| Concept | Sub-Workflow Spec | A2A Protocol |
|---------|-------------------|--------------|
| **Role** | Definition language — what this agent can do | Runtime protocol — how agents communicate |
| **Artifact** | `rag_faq.yaml` — entities, states, transitions, permissions | A2A messages — input/output over the wire |
| **When used** | Design time (workflow authoring) | Runtime (agent-to-agent invocation) |
| **Analogy** | Class definition | Method invocation |

### 1.2 What A2A Does NOT Cover

- **Sub-workflow definition** → Routing & Execution spec §5
- **MCP tool invocation** → Tool Ecosystem spec §7
- **OAuth / user identity** → Auth Token Verification spec
- **Response generation** → Response Generation spec

> **New (2026-06-18):** The A2A protocol is also available as a **tool type** (`type: a2a`) — any node can call another agent as one of its `tool_allowlist` tools, with multi-turn conversation support. See [Tool Ecosystem §7.5](./13-tool-ecosystem.md) for A2A tool registration, multi-turn A2A conversations, and the A2A-tool-vs-sub-workflow comparison matrix.

### 1.3 A2A as Deterministic Microservice Protocol

#### The Key Clarification

A2A is often misunderstood as a protocol for "autonomous LLM agents that make their own decisions." That is only one use case. **When both the caller and the callee use this framework's deterministic architecture, A2A becomes the agent-world equivalent of microservice communication** — deterministic services communicating through a standard protocol.

```
Traditional microservice architecture:
  Order Service  ──HTTP/API──→  Payment Service  ──HTTP/API──→  Inventory Service
  (deterministic)              (deterministic)                (deterministic)

A2A with deterministic agents (this framework):
  Mortgage Agent  ──A2A──→  CheckRates Agent  ──A2A──→  Eligibility Agent
  (YAML state     (YAML state      (YAML state
   machine)        machine)         machine)
  (deterministic) (deterministic)  (deterministic)
```

Each agent is a **deterministic microservice**:
- **Internal:** YAML state machine + LangGraph runtime — deterministic, auditable, reproducible
- **External:** A2A protocol — communicates with other agents via intent-based messages
- **Independent:** own workflow.yaml, own checkpoint store, own deployment, own version lifecycle

#### Why Deterministic + A2A Does NOT Conflict

A common concern: "A2A means the callee is an autonomous agent that makes non-deterministic decisions, which conflicts with the framework's deterministic principle (AD #3)."

**This concern is based on a false assumption** — that A2A requires the callee to be an autonomous LLM agent. It does not. When the callee is also a deterministic state machine:

| Property | Autonomous LLM Agent (A2A) | Deterministic Agent (A2A, this framework) |
|----------|---------------------------|-------------------------------------------|
| Internal decisions | LLM decides what to do | State machine + guards decide |
| Determinism | ❌ Same input → different paths | ✅ Same input + same state → same path |
| Auditability | ❌ "The LLM decided to..." | ✅ "Guard X passed → transition to Y" |
| Reproducibility | ❌ Cannot replay | ✅ Checkpoint + replay |
| Cost | N LLM calls per delegation | LLM only for NLU + generation (per node) |

**When both sides are deterministic, the entire A2A chain is deterministic and auditable:**
- Caller audit trail: state transitions + guard results + A2A request sent
- A2A communication audit: message sent + message received + correlation ID
- Callee audit trail: state transitions + guard results + A2A response returned
- Full chain: reproducible from end to end

#### A2A's True Positioning

A2A is NOT "the protocol for autonomous agents." A2A is:

> **The microservice communication protocol for the agent world** — whether those agents are deterministic state machines or autonomous LLM reasoners. The protocol is the same; the internal architecture of each agent is independent.

This positions A2A alongside MCP in the protocol stack:

| Protocol | Communication between | Semantics |
|----------|----------------------|-----------|
| **MCP** | Agent ↔ Tool | Function-call: "execute this operation with these parameters" |
| **A2A** | Agent ↔ Agent | Intent-based: "achieve this goal with these entities" |
| **REST** | Service ↔ Service (non-AI) | HTTP: standard web API |

---

## 2. A2A Protocol Contract

### 2.1 Core Semantics

```
A2A Call (Agent A → Agent B):
  Input:   entities + goal + correlation_id
  Output:  results + audit + correlation_id
```

The protocol is intent-based, not function-call-based. Agent A sends *what it wants to accomplish* (goal + relevant entities), not *how to do it*. Agent B decides how to achieve the goal using its own internal workflow.

### 2.2 A2A Message Format

Every A2A message carries a standard envelope:

```yaml
# A2A Request — sent by caller agent to target agent
a2a_request:
  # --- Routing ---
  agent_id: string                   # target agent identifier (registered in registry)
  correlation_id: string             # UUID — ties request to response across async boundaries

  # --- Context ---
  caller:
    agent_id: string                 # caller agent identifier
    workflow_id: string              # which workflow instance is calling

  # --- Payload ---
  goal:
    summary: string                  # what the caller wants the target to accomplish
    expected_outputs: string[]       # which outputs are expected back

  entities:                          # relevant entity data passed to target agent
    <entity_name>: <entity_data>

  constraints:
    deadline_ms: integer             # optional — hard deadline for response
    priority: low | normal | high | critical

  # --- Protocol ---
  mode: sync | async                 # caller expects to wait or continue
  version: string                    # A2A protocol version (e.g., "1.0.0")
```

```yaml
# A2A Response — sent by target agent back to caller
a2a_response:
  # --- Routing ---
  correlation_id: string             # matches the request's correlation_id

  # --- Status ---
  status: completed | failed | partial | timeout | clarification_needed

  # --- Payload (when status = completed or partial) ---
  results:                           # structured output from the target agent
    <output_name>: <output_data>

  # --- Clarification (when status = clarification_needed) ---
  clarification:                     # see §6.3 for bidirectional clarification
    question: string                 # what the callee needs to know
    options:                         # structured choices for the caller
      - value: string
        label: string
    my_context: string               # callee's explanation of why it needs this

  # --- Audit ---
  audit:
    agent_id: string                 # which agent produced this response
    steps_completed: string[]        # states traversed within the target agent
    duration_ms: integer
    attempts: integer                # retries used (including LLM +1)

  # --- Error (when status = failed) ---
  # Uses FrameworkError schema with root_cause chain — see §6.3 and Routing §6.5
  error:
    error_id: string
    category: string                 # llm_error | api_error | tool_error | validation_error | permission_error | business_rule_error | unrecoverable_error
    type: string                     # transient | permanent | partial
    error_code: string               # machine-readable code
    retryable: boolean
    source:
      agent_id: string
      node_id: string
    message: string
    details: object
    root_cause: FrameworkError       # nested — preserves original error from deeper agent
    suggested_strategies: string[]
    user_facing_message: string      # only set by top-level agent
```

### 2.3 A2A vs Sub-Workflow Input Mapping

The A2A protocol is the wire format. Sub-workflow `input_mapping` (Routing & Execution spec §5.6) defines how parent state maps to A2A request fields:

```yaml
# parent workflow YAML — sub-workflow invocation
states:
  handle_question_in_quote:
    executor: sub_workflow
    sub_workflow: rag_faq
    mode: sync
    input_mapping:                        # these map to A2A request
      goal:
        summary: "Answer user's FAQ question"
        expected_outputs: [answer]
      entities:
        question_input:
          question: "{{state.last_user_message}}"
          conversation_context: "{{state.conversation_history}}"
      constraints:
        deadline_ms: 10000
    on_return: collect_lead_purpose
```

The framework auto-generates the A2A envelope from this mapping. The developer never writes A2A messages manually.

---

## 3. Two API Formats the Framework Exposes

The framework exposes two protocol families. Both are JSON-based, stateless at the transport layer, and carry correlation IDs — but serve different use cases.

| | MCP | A2A |
|---|-----|-----|
| **Role** | External tool invocation | Internal agent delegation |
| **Consumer** | External systems (Claude Desktop, IDE, CLI) | Internal agents (parent workflows) |
| **Semantics** | Function-call: "execute this tool with these params" | Intent-based: "achieve this goal with these entities" |
| **State** | Stateless tool execution | Agent has its own state machine, permissions, retry |
| **Discovery** | MCP `list_tools` | Agent Registry `discover` |
| **Response** | ToolResult { success, data } | AgentResult { status, results, audit } |
| **Auth** | MCP server-level auth | Inherited from caller's UserContext |
| **Example** | `calculate_rate(params)` | "Distribute a lead → agent_lead_distribution" |

```
┌─────────────────────────────────────────────────────────┐
│                   FRAMEWORK BOUNDARY                      │
│                                                           │
│  External                    Internal                     │
│  ┌──────────┐               ┌──────────────────┐         │
│  │  MCP     │──────────────→│  Tool Execution  │         │
│  │  Client  │  function-call│  (stateless)     │         │
│  │ (Claude, │               └──────────────────┘         │
│  │  IDE)    │                                            │
│  └──────────┘               ┌──────────────────┐         │
│                              │  Agent Registry  │         │
│  ┌──────────┐               │       │          │         │
│  │  Agent A │──────────────→│  A2A  │  Agent B │         │
│  │ (Parent  │  intent-based │       │  (Sub-   │         │
│  │  Workflow│               │       │  workflow)│         │
│  └──────────┘               └──────────────────┘         │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 3.1 Same Protocol Family, Different Use Case

MCP and A2A share a common design philosophy:
- Both carry `correlation_id` for traceability
- Both are JSON-structured
- Both support sync and async patterns
- Both are registered and discovered via a registry

They differ in **semantic level**: MCP is tool-level ("do this operation"), A2A is agent-level ("achieve this goal").

```yaml
# framework.yaml — protocol configuration
protocols:
  mcp:
    enabled: true
    servers:                          # see Tool Ecosystem spec §7
      knowledge_base: ...
      lead_distribution_engine: ...

  a2a:
    enabled: true
    version: "1.0.0"
    agents:
      discovery: registry             # registry | static_list
      registry:
        backend: postgresql           # postgresql | file | consul
        connection_string: "${A2A_REGISTRY_DSN}"
```

### 3.2 A2A vs Direct API vs LangGraph Subgraph

When a parent workflow needs to delegate work to a sub-task (e.g., `check_rates`), there are three integration modes. The choice depends on the **level of decoupling** needed, not on whether the callee is deterministic.

#### The Three Modes

```
Mode 1: LangGraph Subgraph (in-process)
  Parent Workflow ──in-memory──→ Subgraph (same process, shared checkpoint)
  The subgraph is compiled into the parent's LangGraph graph.

Mode 2: Direct API (function call)
  Parent Workflow ──function call──→ Python function / HTTP API
  The callee is a stateless function or external API.

Mode 3: A2A (cross-process agent delegation)
  Parent Workflow ──A2A message──→ Independent Agent (own process/service)
  The callee is a full agent with its own state machine, checkpoint, deployment.
```

#### Comparison Matrix

| Dimension | LangGraph Subgraph | Direct API | A2A |
|-----------|-------------------|------------|-----|
| **Callee type** | State machine (same framework) | Stateless function / external API | Full agent (deterministic or autonomous) |
| **Coupling** | Tight — shared checkpoint, same process | Medium — caller knows callee's interface | Loose — caller only knows goal + expected outputs |
| **Callee has own state machine** | ✅ (subgraph) | ❌ (stateless) | ✅ (independent agent) |
| **Callee collects its own info** | ✅ (own states) | ❌ (caller must provide all params) | ✅ (own states, own collection flow) |
| **Independent deployment** | ❌ (same process) | ✅ (if external API) | ✅ (own service) |
| **Independent scaling** | ❌ | ✅ (if external API) | ✅ |
| **Independent versioning** | ❌ (same YAML repo) | ✅ (API versioning) | ✅ (agent registry version) |
| **Independent team ownership** | ❌ | ✅ | ✅ |
| **Fault isolation** | ❌ (subgraph crash = parent crash) | ✅ (API error caught by caller) | ✅ (agent failure isolated) |
| **Shared state access** | ✅ (direct memory) | ❌ (only via params) | ❌ (only via A2A message) |
| **Communication overhead** | Nanoseconds (in-memory) | Microseconds–milliseconds (function/HTTP) | Milliseconds (serialization + network) |
| **Determinism** | ✅ (if state machine) | ✅ (if pure function) | ✅ (if callee is deterministic — see §1.3) |
| **Auditability** | ✅ (shared audit trail) | ✅ (call + response logged) | ✅ (full A2A audit + callee audit) |
| **Reusability** | Same framework only | Any caller that knows the API | Any A2A-compatible agent |
| **Caller knows callee internals** | Sees subgraph states | Knows full interface/schema | Only knows goal + expected outputs |

#### When to Use Each

| Scenario | Recommended Mode | Why |
|----------|-----------------|-----|
| Sub-task is 1-2 states, same team, same deployment | **LangGraph Subgraph** | Not worth the overhead of A2A; subgraph is simple and fast |
| Sub-task is a single stateless operation (call API, query DB) | **Direct API** | No state machine needed; API call is the simplest integration |
| Sub-task has 3+ states, needs its own info collection, same product | **LangGraph Subgraph** | Avoids state explosion in parent; subgraph handles its own collection |
| Sub-task is reusable across multiple products/workflows | **A2A** | Deploy once, invoke from any agent; independent versioning |
| Sub-task is maintained by a different team | **A2A** | Team boundary = service boundary; A2A provides the contract |
| Sub-task needs independent scaling or deployment | **A2A** | Rate-check service may need different scaling than lead-submission |
| Sub-task needs fault isolation (callee crash must not crash caller) | **A2A** | Process isolation prevents cascade failures |
| Sub-task is a third-party/external agent | **A2A** | Can't compile external code into your subgraph |

#### Concrete Example: `check_rates`

```
check_rates requires: collect loan_type → collect state → collect credit_score → call rate API
  (4 states, own info collection, potentially reusable)

  Same product, same team, same deployment:
    → LangGraph Subgraph (in-process)
    → Parent workflow invokes subgraph, passes intent, gets result
    → Subgraph handles its own state collection internally
    → No need for A2A protocol overhead

  check_rates becomes a shared rate-service used by 3 products:
    → A2A (independent service)
    → Each product's agent calls check_rates via A2A
    → check_rates has its own deployment, scaling, version
    → Caller agents only know: "send goal=check_rates, get back rate"
    → check_rates can evolve its internal flow without callers changing
```

#### The Decoupling Spectrum

```
Tight coupling                                              Loose coupling
←─────────────────────────────────────────────────────────────────────→

LangGraph Subgraph     Direct API          A2A (same framework)    A2A (external agent)
(in-process)          (stateless)         (deterministic)          (autonomous/3rd party)

Shared state          Params only         Goal + entities          Goal + entities
Same process          Caller controls     Callee controls          Callee controls
                      interface           own flow                 own flow
Same deployment       Any caller          Same framework           Any A2A caller
                                          Deterministic            May be non-deterministic

↑                                                                          ↑
Simplest, fastest                                      Most decoupled, most reusable
```

The framework supports all three modes. The choice is a deployment/architecture decision, not a protocol decision — the same sub-workflow YAML can be deployed as a subgraph (in-process) or as an A2A agent (cross-process) depending on operational needs.

---

## 4. Agent Discovery

### 4.1 Agent Registry

Parent workflows discover available A2A agents via a registry. The registry answers: *"Which agents are available, what can they do, and how do I talk to them?"*

```yaml
# Agent Registry entry for rag_faq
agent_registry:
  agents:
    - agent_id: rag_faq
      version: "1.0.0"
      description: "Answer user questions using RAG knowledge base"
      capability: faq_answering
      expected_inputs:
        - question_input                    # entity: question + conversation context
      expected_outputs:
        - answer_output                     # entity: answer + sources
      modes: [sync, async]
      max_concurrency: 50
      health_endpoint: "/a2a/health"
      invoke_endpoint: "/a2a/invoke"
      status: active                        # active | degraded | offline
```

### 4.2 Discovery Flow

```
Parent Workflow Boot
    │
    ├── 1. Query registry: "find agent for capability=faq_answering"
    │
    ├── 2. Registry returns: [rag_faq (active, v1.0.0)]
    │
    ├── 3. Framework validates:
    │       ✓ agent is active
    │       ✓ agent supports requested mode (sync/async)
    │       ✓ agent version is compatible
    │
    └── 4. Framework caches agent descriptor for workflow duration
```

### 4.3 Static vs Dynamic Discovery

```yaml
# framework.yaml
a2a:
  discovery:
    mode: dynamic                     # dynamic | static
    registry:                         # used when mode=dynamic
      backend: consul                 # consul | postgresql | etcd
      endpoint: "${CONSUL_HTTP_ADDR}"
      refresh_interval_sec: 30        # how often to re-sync agent list
    static_agents:                    # used when mode=static
      - agent_id: rag_faq
        endpoint: "http://localhost:8001"
        health_check_path: "/health"   # GET endpoint, must return 200
      - agent_id: lead_distribution_agent
        endpoint: "http://localhost:8002"
        health_check_path: "/health"
      - agent_id: lead_verification
        endpoint: "http://localhost:8003"
        health_check_path: "/health"
    health_check_interval_sec: 10      # how often to probe agent health
```

| Mode | Use Case | Trade-off |
|------|----------|-----------|
| **Dynamic** | Multi-service deployments; agents scale independently | Requires service discovery infra (Consul, etcd) |
| **Static** | Monolith / single-process; simple deployments | No dynamic scaling; manual reconfiguration |

---

## 5. Sync vs Async A2A

The canonical sub-workflow contract (inputs, outputs, timeout, retry budget) is defined in [Routing & Execution §5](./06-routing-execution-layer-design.md). This A2A section extends that contract with network-level concerns: agent discovery, protocol negotiation, message serialization, and transport.

### 5.1 Semantics

The same sync/async semantics defined in the sub-workflow spec (Routing & Execution §5.4) apply at the A2A protocol level — but now with full agent semantics:

```yaml
# Sync A2A invocation
states:
  answer_faq_question:
    executor: a2a_invoke
    agent: rag_faq
    mode: sync
    timeout_ms: 10000
    on_return: collect_lead_purpose

# Async A2A invocation
states:
  background_lead_check:
    executor: a2a_invoke
    agent: lead_verification
    mode: async
    on_complete: lead_result_received         # callback when async agent finishes
    on_timeout: proceed_without_lead_check    # fallback if async agent doesn't respond
```

### 5.2 Sync Flow

```
Agent A                        Agent B
  │                              │
  ├── A2A Request ──────────────→│
  │                              ├── Execute workflow
  │   (blocks, waits)            │   search → generate → validate
  │                              │
  │←── A2A Response ────────────┤
  │    status: completed          │
  ├── Resume parent workflow      │
```

### 5.3 Async Flow

```
Agent A                        Agent B
  │                              │
  ├── A2A Request ──────────────→│
  │   mode: async                 ├── Execute workflow
  │                              │   ...
  ├── Continue parent workflow    │
  │   ...                         │
  │                              ├── A2A Response (callback)
  │   [on_complete triggered] ←──┤
  ├── Process result              │
```

### 5.4 Async Callback Patterns

```yaml
# framework.yaml — async A2A callback configuration
a2a:
  async:
    callback:
      strategy: webhook | polling | message_queue
      webhook:
        endpoint: "/a2a/callback/{correlation_id}"
        retry_on_failure: true
        max_retries: 3
      polling:
        interval_ms: 1000
        max_polls: 30
      message_queue:
        backend: redis           # redis | rabbitmq | kafka
        channel: "a2a.responses"
```

---

## 6. A2A Execution Flow

### 6.1 Full Lifecycle

```
1. Parent workflow reaches a2a_invoke node
2. Framework resolves agent_id → queries registry → gets agent descriptor
3. Framework validates:
     ✓ Agent is active
     ✓ Agent supports requested mode
     ✓ Caller has permission to invoke this agent
4. Framework constructs A2A request:
     - Maps parent state → A2A request payload via input_mapping
     - Generates correlation_id
     - Sets deadline from constraints
5a. [Sync] Framework sends A2A request, blocks, waits for response
5b. [Async] Framework sends A2A request, continues parent workflow immediately
6. Target agent receives A2A request → executes its own state machine
7. Target agent returns A2A response
8a. [Sync] Parent receives response → resumes workflow at on_return
8b. [Async] Parent's on_complete callback fires → processes response
9. Audit: both sides log the A2A interaction with correlation_id
```

### 6.2 Permission Model for A2A

Agents may restrict which callers can invoke them:

```yaml
# Agent registry entry with caller allowlist
agent_registry:
  agents:
    - agent_id: lead_distribution_agent
      allowed_callers:
        - mortgage_lead_submission              # only this workflow can invoke
      deny_all_others: true
    - agent_id: rag_faq
      allowed_callers: ["*"]                # any agent can invoke
```

### 6.3 A2A Error Handling

When an A2A invocation fails, the error routes to `errorNode` following the same pattern as all other errors (Routing & Execution spec §6). A2A errors use the **structured FrameworkError schema** (see [Routing & Execution §6.5](./06-routing-execution-layer-design.md)) with **root_cause chain** for cross-agent tracing.

#### A2A Error Response with Root-Cause Chain

When an A2A agent (Agent B) fails because its own dependency (Agent C) failed, B's A2A response carries a structured error that preserves C's original error in the `root_cause` field:

```yaml
# A2A Response — Agent B returns error to Agent A
a2a_response:
  correlation_id: "conv-123"
  status: failed
  error:
    # FrameworkError (see Routing & Execution §6.5)
    error_id: "err-bbb"
    correlation_id: "conv-123"
    category: validation_error
    type: permanent
    error_code: "DEPENDENCY_FAILED"
    retryable: false                  # inherited from root_cause
    source:
      agent_id: "check_rates"        # this agent
      node_id: "eligibility_check"
      layer: "L2"
    message: "eligibility check rejected the input"
    details:
      my_context: "rate calculation requires eligibility first"
    root_cause:                       # Agent C's original error (read-only)
      error_id: "err-ccc"
      agent_id: "eligibility"
      error_code: "FIELD_OUT_OF_RANGE"
      message: "credit_score=7200 out of range 300-850"
      details:
        field: "credit_score"
        received_value: 7200
        expected: "300-850"
      root_cause: null
    suggested_strategies: ["ask_clarify"]
```

#### Root-Cause Chain Rules

The root-cause chain follows the same rules as [Routing & Execution §6.5](./06-routing-execution-layer-design.md) (Structured Error Schema). A2A-specific extensions:

1. **If an agent swallows the root_cause, it is a spec violation** — the framework validates that A2A error responses contain the full chain

#### Bidirectional Clarification (A2A-Specific)

In addition to `status: completed` and `status: failed`, A2A supports a third status: `clarification_needed`. This allows a callee agent to **ask the caller for more information** instead of reporting an error — something microservices cannot do but agent systems can.

```yaml
# A2A Response — Agent B asks Agent A for clarification
a2a_response:
  correlation_id: "conv-123"
  status: clarification_needed
  clarification:
    question: "credit_score=7200 is outside FICO range 300-850. Is this a user input error or a data source error?"
    options:
      - value: "user_input_error"
        label: "User input error — ask user for correct credit score"
      - value: "data_source_error"
        label: "Data source error — can handle with fallback logic"
      - value: "force_accept"
        label: "Force-accept 7200 (non-standard scenario)"
    my_context: "rate calculation paused, awaiting credit score clarification"
```

When the caller (Agent A) receives `clarification_needed`:
1. A may answer the question directly (if A has the information)
2. A may forward the question to the user (if A is the top-level agent talking to the user)
3. A may choose to cancel the A2A invocation and use a different strategy (e.g., `fallback_value`)

```yaml
# A2A Request — Agent A answers B's clarification
a2a_request:
  correlation_id: "conv-123"
  clarification_answer:
    selected: "user_input_error"
    corrected_data:
      credit_score: 720             # corrected value
```

**When to use `clarification_needed` vs `failed`:**
- Use `clarification_needed` when the error is likely a **user data issue** that the user can fix
- Use `failed` when the error is a **system error** (timeout, permission denied, unrecoverable)
- **Limit clarifications** with `max_a2a_clarifications: 2` to prevent infinite back-and-forth

#### A2A Error vs Clarification Decision

| Situation | A2A status | Why |
|-----------|-----------|-----|
| Callee's dependency timed out | `failed` | System error — user can't fix it |
| Callee's dependency returned bad data | `failed` | With root_cause chain |
| User input likely wrong (field out of range) | `clarification_needed` | User can fix it |
| Permission denied | `failed` | Not a user-fixable issue |
| Partial success (2 of 3 sub-tasks done) | `partial` | Caller decides whether to accept |
| Callee needs more context from caller | `clarification_needed` | Caller may have the info |

#### Per-Node A2A Error Configuration

```yaml
# Per-node A2A error configuration
states:
  handle_lead_distribution:
    executor: a2a_invoke
    agent: lead_distribution_agent
    mode: sync
    on_error:
      route_to: errorNode
      error_strategy: dead_letter_queue    # never lose a lead distribution
      max_retries: 2
      max_a2a_clarifications: 2            # max back-and-forth before treating as failed
    on_clarification:
      forward_to_user: true                # forward clarification questions to the user
      auto_respond: false                  # don't auto-respond; let the user decide
```

---

## 7. Comparison: MCP vs A2A

### 7.1 Side-by-Side

| Dimension | MCP | A2A |
|-----------|-----|-----|
| **Semantic level** | Tool ("execute operation") | Agent ("achieve goal") |
| **State** | Stateless | Stateful (agent has its own FSM) |
| **Input** | Tool name + parameters | Entities + goal + constraints |
| **Output** | ToolResult { success, data } | AgentResult { status, results, audit } |
| **Discovery** | `list_tools` via MCP handshake | Agent Registry query |
| **Retry** | Simple: retry tool call | Complex: agent-level retry within its own budget |
| **Permission** | Tool-level access_level | Agent-level + inherited UserContext |
| **Audit** | Tool invocation recorded | Full sub-workflow trace recorded |
| **Protocol version** | MCP spec version | A2A spec version |
| **Consumer** | External clients | Internal workflows |
| **Example** | `search_documents(query)` | "Answer this FAQ question → rag_faq agent" |

### 7.2 When to Use Which

```
Decision tree:

Is the consumer an external system (IDE, Claude Desktop, CLI)?
  └─ Yes → MCP
  └─ No → Continue

Does the task require its own state machine, permissions, and retry?
  └─ Yes → A2A (it's an agent)
  └─ No → Continue

Is the task a single operation with clear input/output?
  └─ Yes → MCP tool (simpler)
  └─ No → A2A (needs agent-level autonomy)
```

### 7.3 Coexistence

An agent can expose BOTH MCP tools AND A2A endpoints simultaneously:

```yaml
# rag_faq agent — dual protocol exposure
rag_faq:
  a2a:
    endpoint: "/a2a/invoke"
    capability: faq_answering
  mcp:
    tools:
      - search_knowledge_base
      - get_document
```

This means:
- **Parent workflows** invoke `rag_faq` via A2A (delegate the full FAQ workflow)
- **External tools (like Claude Desktop)** can also call `rag_faq.search_knowledge_base` via MCP (use its individual capabilities)

---

## 8. Sub-Workflow Spec Cross-Reference Update

The A2A protocol complements the existing sub-workflow spec (Routing & Execution §5) as follows:

| Sub-Workflow Spec § | A2A Relationship |
|---------------------|------------------|
| §5.1 Concept — "complete, standalone workflows" | A2A formalizes this as agent independence |
| §5.2 Full Workflow Structure — domain model, entities, states | These are the agent's internal definition (not exposed via A2A) |
| §5.3 Node Orchestration — serial, parallel, DAG | Internal execution — invisible to caller |
| §5.4 Sync vs Async | A2A protocol carries this as `mode` field |
| §5.5 Sub-Workflow Nesting | Recursive A2A: Agent A → Agent B → Agent C |
| §5.6 Invocation from Parent — input_mapping | Input_mapping generates A2A request payload |

**New: A2A adds to sub-workflow spec:**
- Wire format (A2A request/response envelope)
- Agent registry + discovery
- Caller permission model
- Async callback mechanisms
- Correlation ID across agent boundaries

---

## 9. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should A2A support streaming responses (agent streams partial results as they're produced), or only complete responses? | Long-running agent UX |
| 2 | Should the agent registry support version negotiation (caller requests agent v1.2, registry returns latest compatible)? | Agent evolution |
| 3 | For async A2A: if the parent workflow terminates before the async agent responds, what happens to the correlation? | Resource cleanup |
| 4 | Should A2A support bidirectional communication (agent B can ask agent A for clarification mid-execution)? | Complex agent interactions |
| 5 | How should the agent registry handle agent health (heartbeats, degraded status propagation)? | Production resilience |
| 6 | Should A2A messages be persisted to an event log for replay/debugging (event sourcing pattern)? | Audit and debugging |
| 7 | Can A2A agents be deployed as separate services (microservices), and if so, what is the service mesh integration surface? | Deployment architecture |
| 8 | Should A2A support a "conversation" pattern where agents exchange multiple messages before completing (not just request/response)? | Complex multi-step delegation |

---

## References

- [High-Level Design](./01-deterministic-workflow-framework-design.md) — framework architecture, permission model
- [Routing & Execution Layer](./06-routing-execution-layer-design.md) — sub-workflow spec (§5), retry (§6), permission (§7)
- [Tool Ecosystem](./13-tool-ecosystem.md) — MCP server integration (§7), tool registration
- [Auth Token Verification](./16-auth-token-verification.md) — UserContext injection
- [MCP API Protocol](./11-mcp-api-protocol.md) — §1.3 Exposure Granularity (coarse-grained `send_message` vs fine-grained tools), §6.8 LLM-as-Component positioning
- [VISION.md §6.8](../VISION.md) — LLM Positioning: Component, Not Orchestrator (deterministic core + LLM as component)
- [Google A2A Protocol](https://github.com/google/A2A) — Google's Agent-to-Agent protocol (conceptual reference; note: A2A v1.0 donated to Linux Foundation, 150+ organizations)
