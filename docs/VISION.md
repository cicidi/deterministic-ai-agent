# Project Vision & Requirements — Master Reference

> **Source:** All user prompts across sessions, consolidated into a single reference document.
> **Purpose:** Authoritative source for checking all spec documents against the user's actual vision, requirements, and constraints.
> **Last updated:** 2026-06-18

---

## 1. What We Are Building

**A deterministic workflow framework for enterprise AI agents in regulated industries.**

It is NOT a pre-built product. It is a **reference architecture + design pattern framework** that provides:
- Clean interfaces for developers to implement business logic
- Pre-injected patterns (state-aware prompting, deterministic fallback, sticky mode, sub-workflow reuse) that handle the "dirty work"
- Comprehensive spec documents that serve as both technical reference AND interview templates for a downstream skill

The downstream skill loads these specs and, through guided Q&A, helps a developer produce a complete product-specific deterministic AI agent specification — ready for code implementation planning.

---

## 2. Project Deliverables

| Deliverable | Type | Description |
|-------------|------|-------------|
| **Framework Specs** | Design documents | Comprehensive specs for a deterministic AI agent framework |
| **Spec Generator Skill** | Downstream tool | AI skill that interviews a developer and outputs a product-specific spec |
| **Python Reference Implementation** | Code (future) | Proves feasibility; not yet started |

---

## 3. What To Do

### 3.1 Spec Documents (current phase)

- [x] High-Level Design (3-layer architecture, per-node control, framework principles)
- [x] Intent Classification (Layer 1, LLM-first + keyword fallback)
- [x] State Machine Design (transitions + LangGraph fusion, state metadata, intent+state resolution)
- [x] Extraction Layer (Extract/Validate/Transform pipeline, per-interface options)
- [x] Domain Model (Entity + State + Transition schemas, single source of truth, cross-workflow reuse)
- [x] Routing & Execution (code executors, decision nodes, sticky mode, sub-workflow, retry/errorNode, permission, tools)
- [x] Response Generation (goal setting, response modes, goal check, PII scrubbing, loop-back)
- [x] Tool Ecosystem (LangFlow, LangGraph CLI, LangSmith, rule engines, MCP servers)
- [x] Environment Configuration (dev / e2e / prod)
- [x] RAG Interface
- [x] Agent Types

### 3.2 Spec Content Requirements

Every spec document MUST:
1. **Define interfaces only** — not lock into a single solution
2. **Provide at least 2 implementation options per interface** — with comparison matrix
3. **Separate WHAT from HOW** — domain model defines what, workflow config defines how
4. **Include changelog** — version + date + changes
5. **Cross-reference parent/child docs** — maintain document tree
6. **Include open questions** — not solved upfront, deferred for architect discussion
7. **Contain schemas + samples only** — no implementation code
8. **Include decision rationale** — document WHY each design decision was made (e.g., accuracy vs cost vs latency trade-offs); decisions are recorded both in the architecture decisions table (Section 5) and inline in the reasoning sections of relevant specs

### 3.3 After Specs Complete

- Build the downstream **Spec Generator Skill** that loads these specs and interviews developers
- Add interview templates / decision point markers to specs
- Start Python reference implementation (when requested)

---

## 4. What NOT To Do

### 4.1 Never

- ❌ **No implementation code yet.** Spec-first. Schemas + sample code only — sample code is illustrative (shows shape/intent), not production-ready implementation. Full implementation deferred.
- ❌ **No Framework API spec.** 7 specs define all interfaces. AI can derive assembly from them. No need for a separate "how to boot" doc.
- ❌ **No premature solving.** Open questions are deferred for architect-level discussions during adoption.
- ❌ **No single-industry lock-in.** Framework is generic — configurable for any regulated industry.

### 4.2 Avoid

- ❌ **Don't duplicate.** If a concept is defined in one spec, reference it; don't redefine.
- ❌ **Don't over-specify implementation.** "LLM calls OpenAI" is too specific. "LLM provider (configurable)" is correct.
- ❌ **Don't reinvent the wheel.** Before defining a custom interface, check whether mature OSS already solves the problem. Reference the OSS as a recommended implementation option; don't rebuild what the ecosystem provides. See §6.7.
- ❌ **Don't lose the skill vision.** Every spec should be usable as an interview template by a downstream AI.

---

## 5. Architecture Decisions (Chronological)

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-06-15 | Python + LangGraph | LangGraph provides state graph, checkpoint, streaming; Python has strongest ecosystem |
| 2 | 2026-06-15 | Generic framework (not single-industry) | Configurable for any regulated industry |
| 3 | 2026-06-15 | LLM-assisted NLU + deterministic core | LLM excels at understanding; execution must be auditable |
| 4 | 2026-06-15 | Pip-installable Python library | Framework only, no frontend |
| 5 | 2026-06-16 | Per-node LLM/deterministic switch | Not per-layer binary; granularity at node level |
| 6 | 2026-06-16 | Sub-workflow reuse | Shared capabilities defined once, invoked from any state |
| 7 | 2026-06-16 | Spec-first + Python reference impl | Language-agnostic interfaces; Python proves feasibility |
| 8 | 2026-06-17 | Extract/Validate/Transform pipeline | Three interfaces with pluggable strategies |
| 9 | 2026-06-17 | Domain Model as single source of truth | Entity + State + Transition, separate from HOW config |
| 10 | 2026-06-17 | durable_rules as default rule engine | Closest Python Drools equivalent, but pluggable |
| 11 | 2026-06-17 | All LLM output = JSON + framework guardrails | Structured output always; free text only in Layer 3 |
| 12 | 2026-06-17 | Two-level permission model | Config-level (YAML allowlists) + OAuth/role-based (runtime) |
| 13 | 2026-06-17 | Phase-aware routing with return stack | agentState.phase + intent → next node; question → return to previous phase |
| 14 | 2026-06-17 | Goal-driven workflow | Async goal set at start; parallel goal check at end; 422 on large gap |
| 15 | 2026-06-17 (revised 2026-06-25) | All errors → errorNode unified + 3-type classification + 8 strategies | **Original:** All errors → errorNode unified; errorNode strategies: ask_clarify, escalate_to_human, terminate, fallback_value, retry_with_context. **Revised:** Added error classification layer (transient/permanent/partial) required before strategy selection. Expanded strategies from 5 to 8: added `retry_with_backoff`, `graceful_degradation`, `dead_letter_queue`. Added structured FrameworkError schema with root_cause chain for cross-agent tracing. Added strategy decision matrix (error type → valid strategies). See routing-execution §6.3–§6.10. |
| 16 | 2026-06-17 | LLM +1 extra retry | Compensates for LLM non-determinism |
| 17 | 2026-06-17 | Serial + parallel + mixed sub-workflow nodes | LangGraph Send API + conditional edges |
| 18 | 2026-06-17 | Two response modes | Pure message (LLM + prompt eval) + Widget (deterministic logic) |
| 19 | 2026-06-17 | Node loop-back | Self-correction: detect incomplete → return to earlier node |
| 20 | 2026-06-17 | Tool ecosystem integration | LangFlow (drag-drop editor), LangGraph CLI (dev), LangSmith (debug) |
| 21 | 2026-06-17 | 3 environments: dev, e2e, prod | Per-env thresholds, models, retry configs |
| 22 | 2026-06-18 | Two-stage classify+extract (separate nodes) | Accuracy > latency: scoped schema per extract call prevents cross-intent field confusion; single combined prompt with all schemas causes LLM to misroute fields between intents |
| 23 | 2026-06-18 | Multi-intent per message + complex flag | Single user message can carry multiple intents; `complex` flag on IntentDef prevents incompatible multi-turn intents from being processed together |
 | 24 | 2026-06-18 | A2A + SDK as tool types (not just executor-level) | Nodes can call other agents as tools (`type: a2a`) alongside API/MCP/command tools; SDK tools (`type: sdk`) for OpenCode/Claude as tools; multi-turn A2A conversations with turn budget; all tool failures route to errorNode |
| 25 | 2026-06-18 | Spec deduplication & version alignment | Guard expression syntax delegated to state-machine §3.4 (domain-model now cross-references); HLD ToolMeta.type enum synced with child specs; remaining Groovy code removed from CI/CD spec; PII tool catalog entries trimmed to cross-reference response-generation §8 |
| 26 | 2026-06-18 | Option C (Hybrid) as default + auto-generated Mermaid graph | YAML as single source of truth for workflow definition; Python functions (guards, validators, actions) registered by name and referenced from YAML; framework startup validates all name bindings resolve (drift detection); LangGraph's draw_mermaid_png() auto-generates visual graph snapshot; CI enforces YAML ↔ PNG consistency; non-technical reviewers use PNG for visual audit |
| 27 | 2026-06-18 | Declarative field mutations (on_entry/on_exit/on_take.set_field) | Every agentState field write is declared in YAML via lifecycle hooks — no hidden code mutations. set_field supports literals, function calls (now(), uuid4()), and field references. Execution order: on_exit → guard eval → on_take → checkpoint → on_entry → main executor. Simple assignments stay in YAML; complex computation stays in Python action functions via output_schema merger. |
| 28 | 2026-06-18 (revised 2026-06-25) | UML Statechart Semantics (revised from SCXML) | **Original:** SCXML as semantic standard. **Revised:** The state machine follows UML statechart semantics (states, transitions, guards, entry/exit actions, parallel regions) — the conceptual vocabulary shared by XState, SCXML, `python-statemachine`, and `transitions`. YAML is the canonical artifact; LangGraph is the runtime. SCXML is NOT adopted because: (1) its executable content (`<script>`, `<foreach>`) was never used — Python guards replace it; (2) no SCXML file is produced or validated; (3) no specific regulator requiring SCXML was named; (4) 2026 industry (XState v5, Rust scxml crate) moved away from SCXML. The SCXML↔YAML mapping table is retained as an informative reference for teams needing SCXML interchange. |
| 29 | 2026-06-18 | OpenAPI 3.1 Schema as data model standard | Domain model entities defined using OpenAPI Schema Objects (JSON Schema) instead of custom FieldDef format. $ref enables schema composition (HomeInsurance aggregates UserInfo, Address, PropertyInfo, CoverageInfo). Industry-standard tooling: validators, code generators, Swagger UI. Downstream API contracts (QuoteRequest, QuoteResponse) defined in same format. x-state-bindings maps states to entity fields for per-state extraction scope. |
| 30 | 2026-06-18 | Multi-pass per-state extraction scope | Extract node uses per-state scope (from domain model x-state-bindings) instead of full domain schema. Pass 1: two parallel LLMs (narrow scope + broad scope). Pass 2: merge, cross-validate, and user confirmation (never silently merge guessed data). Scope never includes future states' fields. |
| 31 | 2026-06-18 (revised 2026-06-25) | Two-Layer Escalation: Reliability + Quality | **Original:** Progressive model escalation on LLM failure — single cascade chain. **Revised:** Two independent layers: (1) Reliability Layer — provider failover (timeout/5xx/rate-limit → same-tier model on different provider, no retry on dead provider); (2) Quality Layer — model escalation (schema-violation/low-confidence → retry same model, then escalate to more capable model same provider). Rationale: conflating reliability failover with cost-quality routing is "the most common architectural mistake" (2026 industry guidance, 4 independent sources). Two layers have different goals (availability vs quality), different triggers, different escalation targets, and produce distinct audit events. Minimum 2 providers, each with ≥2 models. The default is always the cheapest model. |
| 32 | 2026-06-18 | Cheap model by default | The framework is designed to work with inexpensive small models (gpt-4o-mini, claude-haiku, deepseek-chat) as the primary engine. Larger models exist only as escalation fallback. Every design decision — extraction scoping, parallel LLM merge, tier-aware retry, sticky tier — is optimized for extracting maximum accuracy from the cheapest model tier. |
| 33 | 2026-06-18 | Daily token budget + cost calculator | The gateway enforces a daily token limit and cost cap per server. Each model declares price per 1K tokens (input/output). Cumulative daily usage is tracked. Exceeding budget → HTTP 500, service stop. `on_budget_exceeded: warn_only` option for dev/testing bypass. |
| 34 | 2026-06-25 | LLM-as-Component, Not LLM-as-Orchestrator | The framework uses a deterministic state machine as the orchestrator; the LLM is a component that does NLU (intent classification + entity extraction) and response generation only. Internal tools are NOT exposed to external LLM clients via MCP — only coarse-grained `send_message` is exposed. This enables: cheap models as default (AD #32), deterministic/auditable execution (AD #3), per-node permission enforcement (AD #12), and model replaceability. See §6.8 for full rationale. |
| 35 | 2026-06-25 | MCP protocol upgraded to 2025-11-25 (Streamable HTTP) | MCP transport upgraded from deprecated HTTP+SSE (2024-11-05) to Streamable HTTP (2025-11-25 stable). Protocol version pinned explicitly. The framework exposes coarse-grained conversation-level tools (`send_message`), NOT fine-grained internal tools — see MCP API Protocol §1.3 for the exposure granularity design decision. |

---

## 6. Design Principles

### 6.1 Code Conventions

- Every method ≤ **50 lines**
- Every file ≤ **1000 lines**
- Executors are small, composable, single-responsibility
- Complex workflows split across files and sub-workflows
- All docs/comments in English; team discussion in Chinese

### 6.2 Interface Philosophy

- Framework = clean interfaces + injected patterns
- Developer implements business logic; framework absorbs the dirty work:
  - LLM guardrails (JSON schema validation, field presence, type coercion)
  - Permission enforcement (per-node tool + transition allowlists)
  - Retry budgets (per-node retry + escalation)
  - Audit trail (every decision, extraction, transition logged)
  - Deterministic fallback (regex/keyword for every extractable field)
  - State awareness (current FSM state injected into every LLM prompt)
  - Sticky mode (phase-aware routing with return stack)
  - Sub-workflow reuse (shared capabilities defined once)

### 6.3 LLM Rules

- **All LLM output is JSON** — framework enforces output validation guardrails
- **Free-text limited to Layer 3 (Response)**
- **LLM decisions need evals** — input/output test cases, ≥95% pass rate
- **LLM nodes get +1 extra retry** on top of node retry budget
- **Temperature = 0** for extraction/classification/decision; 0.3 for response generation

### 6.4 Permission Rules

- **Config-level** — per-node YAML allowlists: `allowed_tools`, `allowed_transitions`
- **OAuth / Role-based** — runtime enforcement based on authenticated user scopes
- **Tool categories** — read, write, sensitive_data_read, dangerous_operation_write
- **`dangerous_operation_write`** requires human approval gate

### 6.5 Error Handling

- **All errors → errorNode** — unified handling; no per-category *routing* (classification happens, routing is always to errorNode)
- **Error classification required** — before strategy selection, errors are classified as transient / permanent / partial (see AD #15 revision, routing-execution §6.3)
- **LLM +1 extra retry** — then errorNode on exhaustion
- **All timeouts → errorNode** after retry exhaustion
- **8 recovery strategies** — `retry_with_backoff`, `retry_with_context`, `ask_clarify`, `fallback_value`, `graceful_degradation`, `dead_letter_queue`, `escalate_to_human`, `terminate` (see routing-execution §6.6 for canonical definitions)
- **Structured error schema** — FrameworkError with root_cause chain for cross-agent tracing (see routing-execution §6.5)

### 6.6 Environment Awareness

- **3 environments**: dev, e2e, prod
- **dev**: cheap model (gpt-4o-mini), relaxed thresholds, mock APIs
- **e2e**: prod model, mock APIs, same thresholds as prod
- **prod**: full guardrails, real APIs, hard protection

### 6.7 OSS-First Implementation

The framework defines **interfaces**, not implementations. For every interface, specs MUST:

1. **Survey existing OSS first.** Before designing a custom mechanism, check whether a mature, widely-adopted library already solves the problem (e.g., Instructor for structured LLM output, Temporal for durable execution, Presidio for PII detection, official A2A SDKs for agent-to-agent communication).
2. **Reference OSS as implementation options.** Each interface spec MUST list at least one mature OSS library as a recommended production implementation, alongside any custom/framework-native option. The OSS option is the **default recommendation** unless there is a documented reason it is insufficient.
3. **Give multiple options with honest trade-offs.** Per §7, every interface has ≥2 options with a comparison matrix. When an OSS option exists, it MUST appear in the matrix — not only framework-native options.
4. **Framework value-add stays above the OSS layer.** The framework's job is the *policy* layer (budget enforcement, escalation, audit trail, permission gates, retry budgets), not the *mechanism* layer (JSON validation, provider routing, state graph execution). Wrap the OSS; don't replace it.
5. **Document the boundary.** Each spec that references an OSS library MUST state clearly: what the OSS does vs. what the framework adds on top.

**Anti-pattern:** Building a custom structured-output validation pipeline (retry-on-violation, type coercion, multi-provider support) when Instructor (3M+ monthly downloads, 15+ providers, 108 releases) already does this — and only listing it as a fourth option. The framework should wrap Instructor and add budget/escalation/audit, not reimplement its core.

### 6.8 LLM Positioning: Component, Not Orchestrator

#### The Two Architectural Camps

There are two fundamentally different ways to build AI agents in 2026:

| | Camp A: LLM-as-Orchestrator | Camp B: LLM-as-Component (This Framework) |
|---|---|---|
| **Who decides tool call order** | The LLM | A deterministic state machine |
| **What the LLM sees** | All available tools (via `tools/list`) | Only the current node's context |
| **What the LLM does** | Understands + decides + orchestrates + generates | Understands (NLU) + generates (response) |
| **Workflow logic lives in** | LLM prompts + tool descriptions | YAML state machine + Python executors |
| **Model requirements** | Needs the strongest, most expensive model to reason well | Works with the cheapest model (gpt-4o-mini, claude-haiku, deepseek-chat) |
| **Determinism** | Non-reproducible — same input may produce different tool sequences | Reproducible — same input + same state = same execution path |
| **Auditability** | "The LLM decided to call X" — hard to prove correctness | "The state machine routed to X because guard Y passed" — provable |
| **Cost per turn** | High (large context with all tool schemas + reasoning) | Low (narrow context, no tool listing, no reasoning about what to call) |
| **Latency** | Higher (LLM must reason about tool selection before acting) | Lower (state machine routes in <1ms; LLM only does NLU + generation) |
| **Best for** | Open-ended tasks (coding, research, creative work) | Regulated workflows (lending, insurance, healthcare, legal, government) |

#### Why This Framework Chooses Camp B

**1. Regulated industries require deterministic, auditable execution.**

A loan approval workflow has a legal sequence: KYC → credit check → eligibility → rate calculation → offer → acceptance. An LLM skipping KYC because "the user seems trustworthy" is a compliance violation. The state machine enforces the sequence; the LLM cannot override it.

**2. Simple models are sufficient — and sufficient is better.**

When the LLM only does NLU (intent classification + entity extraction) and response generation, a cheap model (gpt-4o-mini at $0.15/1M tokens) performs as well as gpt-4o at $2.50/1M tokens. The deterministic core handles all decision logic that would otherwise require expensive model reasoning. This delivers:

- **Higher accuracy** — the state machine never hallucinates a wrong tool call; the LLM's only job (understanding user input) is what small models do best
- **Lower cost** — 10-20x cheaper per turn vs. LLM-as-orchestrator with frontier models
- **Lower latency** — no LLM reasoning about "which tool should I call?" — the state machine routes instantly
- **Full auditability** — every transition, every tool call, every field extraction is logged with its deterministic cause

**3. The LLM is replaceable; the workflow logic is not.**

In Camp B, switching from OpenAI to Anthropic to DeepSeek only affects NLU quality and response tone — the workflow correctness is guaranteed by the state machine. In Camp A, switching models may break the tool-call reasoning that the entire system depends on. **Model replaceability is a feature, not a limitation** — it means cost, latency, and vendor risk are all under your control.

#### Why the Industry Pushes Camp A

The dominant narrative from model providers (OpenAI, Anthropic, Google) is Camp A: "expose all tools, let the LLM orchestrate." This is promoted through MCP's canonical usage, agent SDKs, and documentation. The reasons are not purely technical:

- **LLM centrality**: If the LLM is the orchestrator, the quality of the most expensive model directly determines system quality. This creates dependency on frontier models.
- **Token consumption**: Exposing N tools means every LLM call carries N tool schemas in context. More tools = more tokens = more revenue for token-priced APIs.
- **Ecosystem lock-in**: Tool-call reasoning is model-specific. A system optimized for GPT-4o's tool-calling behavior may not work with a cheaper model. This raises switching costs.
- **Product simplicity for providers**: Building an orchestration engine (state machines, guards, permissions, audit trails) is hard. Selling an API that "does it all" is easy. Camp A minimizes provider product complexity by outsourcing orchestration to the model.

This framework does not dispute that Camp A is valid for open-ended tasks. It disputes the implicit claim that Camp A is the *only* way — and that more expensive models are always needed. **For regulated industries, Camp B is architecturally superior: deterministic, auditable, cheap, fast, and model-agnostic.**

#### The MCP Exposure Decision (see MCP API Protocol §1.3)

This philosophical positioning has a direct consequence for MCP integration: the framework exposes **coarse-grained conversation-level tools** (`send_message`) to external AI clients, NOT fine-grained internal tools. Claude/ChatGPT see one tool — "send a message to this agent" — and the framework's state machine handles everything inside. This is Camp B applied to protocol design: the LLM is a message relay, not an orchestrator.

---

## 7. What Every Spec Must Contain (Checklist)

- [ ] Interface definitions (not implementations)
- [ ] At least 2 options per interface
- [ ] Comparison matrix for options
- [ ] OSS-first: at least one mature OSS library referenced as a recommended implementation option (per §6.7)
- [ ] YAML schema examples (not Python code)
- [ ] Cross-reference to parent/child specs
- [ ] Open questions section
- [ ] Changelog
- [ ] References section
- [ ] Design decision rationale (WHY, trade-off analysis) recorded in Architecture Decisions table AND inline in spec

---

## 8. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    LAYER 1: UNDERSTAND                        │
│  Intent Classification → Entity Extraction (E→V→T pipeline)  │
├──────────────────────────────────────────────────────────────┤
│                    LAYER 2: DECIDE                            │
│  Code Executors | Decision Nodes | Sticky Mode | Sub-Workflow│
│  Retry + errorNode | Permission Enforcer | Tool System       │
├──────────────────────────────────────────────────────────────┤
│                    LAYER 3: RESPOND                           │
│  Goal Setter (async) | Pure Message / Widget | Goal Checker  │
│  PII Scrubbing | Loop-Back                                   │
├──────────────────────────────────────────────────────────────┤
│                    CROSS-CUTTING                              │
│  Domain Model (single source of truth)                        │
│  3 Environments (dev / e2e / prod)                            │
│  Tool Ecosystem (LangFlow, LangGraph, LangSmith)               │
│  Rule Engines (durable_rules / business-rules / pyknow)       │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Document Tree

```
docs/specs/
├── 2026-06-16-deterministic-workflow-framework-design.md    ← HLD (root)
├── 2026-06-16-intent-classification-design.md               ← child of HLD
├── 2026-06-16-state-machine-design.md                       ← child of HLD
├── 2026-06-17-extraction-layer-design.md                    ← child of HLD
├── 2026-06-17-domain-model-design.md                        ← child of HLD
├── 2026-06-17-routing-execution-layer-design.md             ← child of HLD
├── 2026-06-17-response-generation-layer-design.md           ← child of HLD
├── 2026-06-17-tool-ecosystem.md                             ← child of HLD
├── 2026-06-17-a2a-protocol.md                               ← child of HLD
├── 2026-06-17-mcp-api-protocol.md                           ← child of HLD
├── 2026-06-17-environment-config.md                         ← child of HLD
├── 2026-06-17-auth-token-verification.md                    ← child of HLD
├── 2026-06-17-conversation-lifecycle.md                     ← child of HLD
├── 2026-06-17-observability-monitoring.md                   ← child of HLD
├── 2026-06-17-cicd-jenkins-pipeline.md                      ← child of HLD
├── 2026-06-17-llm-gateway.md                                ← child of HLD
├── 2026-06-17-rate-limiting.md                              ← child of HLD
├── 2026-06-17-widget-templates.md                           ← child of HLD
├── 2026-06-18-rag-interface.md                           ← child of HLD
├── 2026-06-18-agent-types.md                             ← child of HLD
└── 2026-06-19-three-tier-agent-testing-methodology.md     ← child of HLD

docs/examples/home-insurance/
├── README.md
├── workflow.yaml
├── intent-definitions.md
├── e2e-scenarios.md
└── audit-log-sample.json

docs/examples/mortgage-lead/
├── README.md
├── workflow.yaml
├── intent-definitions.md
└── e2e-scenarios.md
```
