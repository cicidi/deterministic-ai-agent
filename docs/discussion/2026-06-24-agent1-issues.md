# Agent 1 — Web-Searching Contrarian Review

**Date:** 2026-06-24
**Reviewer:** Agent 1 (Web-searching contrarian)
**Scope:** Key architectural decisions across 12 spec documents (HLD, state-machine, domain-model, intent-classification, extraction-layer, routing-execution, response-generation, llm-gateway, tool-ecosystem, a2a-protocol, mcp-api-protocol, three-tier-testing)
**Method:** For each major design decision, performed live web searches (2026 sources) to find industry patterns, standards, and tools the specs miss or get wrong. Every issue cites at least one URL.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 7 |
| MEDIUM | 6 |
| LOW | 3 |
| **TOTAL** | **20** |

The framework is well-reasoned for its stated goal (reference architecture for regulated industries). The issues below are not "the design is broken" — they are places where the specs either (a) adopt a standard the industry has already moved past, (b) build custom infrastructure that mature OSS tools now provide, or (c) miss a 2026 industry pattern that would change the recommendation. Several findings recur across specs (e.g., the reliability-vs-cost-routing conflation surfaces in both the LLM Gateway and the model-escalation design), which suggests they are architectural, not local.

---

## CRITICAL

### ISSUE-1: weak_rationale — SCXML adopted as semantic standard, but industry moved to XState v5 JSON; SCXML is ceremonial compliance theater with no tooling payoff
- **Type:** weak_rationale / outdated_pattern
- **Section:** state-machine-design §1.0 (AD 28); VISION.md AD 28
- **Problem:** The spec adopts "W3C SCXML 1.0 Recommendation" as the state machine semantic standard and claims "regulated industries generally can reference a W3C standard to justify state machine correctness." But the spec simultaneously admits: *"YAML workflow definition is a YAML expression of SCXML semantics… No XML file is generated — the YAML is the canonical artifact."* This means SCXML is never produced, never validated, and never consumed by any tool. The "compliance & audit" benefit is asserted, not demonstrated — no auditor is named, no SCXML validator is referenced, and no regulated-industry compliance framework actually requires SCXML.

  The deeper problem: the industry standard for statechart formalism in 2026 is **XState v5** (TypeScript) with its JSON dialect, not SCXML. XState v5 *deliberately* dropped strict SCXML conformance because SCXML mandates embedding an ECMAScript interpreter and acting as an execution environment — which every modern implementation rejects. Even the Rust `scxml` crate (the most recent SCXML tooling) explicitly states: *"Why not full W3C SCXML compliance? The W3C spec includes ECMAScript evaluation, `<invoke>` for spawning child sessions, and a runtime interpreter model. These imply embedding a JavaScript engine… we want neither. SCXML is an interchange format here."* XState uses **guards as named string references** (the same pattern our YAML uses), not SCXML's executable expressions.

  The spec's own SCXML↔YAML mapping table (§1.0) quietly admits the mismatch: `<script>` → "not supported", `<foreach>` → "not supported", `<if>/<elseif>/<else>` → "Python guards". SCXML's executable content — the part that makes it a *semantic* standard rather than just a notation — is explicitly rejected. What remains is just a vocabulary of state/transition/onentry/onexit, which is UML statechart terminology that predates SCXML and is shared by every state machine library.

- **Evidence:**
  - https://jovanipink.com/posts/state-machines-03-python-xstate-langgraph-contribution (2026-04-23): *"LangGraph is a graph runtime, not a statechart formalism… For workflows that also need that formalism, the right shape is to combine the two: an XState-style machine that names the states, transitions, and guards, and a LangGraph runtime."* Notes `xstate-python` is pre-1.0 and `transitions`/`python-statemachine` are "more polished" for Python-only teams.
  - https://crates.io/crates/scxml (2026-04-17): *"Why not full W3C SCXML compliance? The W3C spec includes ECMAScript evaluation, `<invoke>`… These imply embedding a JavaScript engine and acting as an execution environment; we want neither. SCXML is an interchange format here: parse it, validate the structure, let the calling code decide what guards mean."*
  - https://statecharts.online/chapters/09-tools-and-frameworks.html (2025-09): *"Does SCXML support matter in practice? It matters if you need model interchange, standards-based semantics, or to load/modify machines at runtime. If your workflow is tool-specific or code-only, SCXML may not be a requirement."*
  - https://regularhuman.dev/docs/comparison-with-xstate/: XState conforms to SCXML spec; Robot deliberately does not, because "reusing machines across languages is not very compelling."
- **Proposed Fix:** Drop the SCXML "semantic standard" claim (AD 28). Replace with: "The state machine follows UML statechart semantics (states, transitions, guards, entry/exit actions, parallel regions) — the conceptual vocabulary shared by XState, SCXML, and `transitions`. YAML is the canonical artifact. For teams that need standards-based interchange, the YAML→XState-JSON export is a future option; SCXML is not adopted because its executable-content model conflicts with our Python-guards approach." This removes the ceremonial compliance claim while keeping the (perfectly valid) statechart vocabulary. If compliance reference is genuinely required for a specific regulator, name the regulator and the specific control that SCXML satisfies — otherwise the claim is unfalsifiable.
- **Severity:** CRITICAL (the rationale is the *only* justification for AD 28; if it's weak, the entire "SCXML as standard" decision collapses to "we use statechart words," which needs no W3C reference)

### ISSUE-2: wrong_approach — Progressive model escalation conflates reliability failover with cost-quality routing; industry calls this "the most common architectural mistake"
- **Type:** wrong_approach
- **Section:** llm-gateway §4 (AD 31, 32); routing-execution §6
- **Problem:** The gateway's escalation flow (§4.2) escalates on **both** `provider_error` (timeout, 5xx, rate limit) AND `schema_violation` (JSON parse, missing fields) using a single chained cascade: `gpt-4o-mini → gpt-4o → claude-haiku → claude-sonnet`. The default `trigger_on` includes both categories. This mixes two concerns that 2026 industry guidance explicitly separates:

  - **Reliability failover** — triggered by provider outage/rate-limit; goal is *availability*; should escalate fast to any healthy model.
  - **Cost-quality routing** — triggered by quality rejection (schema violation, low confidence); goal is *cost optimization*; should escalate slowly to a *more capable* model.

  The cost shape is fundamentally different. A reliability failover to a *cheaper* model may silently degrade quality (and should be recorded as "fell back because primary was down"). A quality escalation to a *more capable* model is a deliberate cost decision. Putting both in the same cascade means: (a) a rate-limit on gpt-4o-mini escalates to gpt-4o for *quality* reasons that don't exist, paying 2x; (b) a schema violation on gpt-4o-mini is retried on gpt-4o-mini (correct) but then "escalates" to gpt-4o which may be a *different provider's* cheap model during an outage — conflating the two failure modes.

  The spec's `failures_before_escalation: 2` default also pays the cheap model's full cost on every escalated request (`0.6·C₁ + 0.4·(C₁ + C₂)`), which industry analysis shows loses to predictive routing once escalation rate exceeds ~30%. The spec's own "sticky tier" (§4.9) is a band-aid for the cost waste this conflation creates.

- **Evidence:**
  - https://jatinbansal.com/ai-engineering/model-routing/ (2026-05-26): *"Conflating the two routing layers — using the same router for both reliability and cost optimization — is the most common architectural mistake teams make in this space, because the policies are different (reliability wants fast escalation on any failure; cost-optimization wants to suppress escalation as much as possible) and putting both in the same logic surface creates the worst of both."*
  - https://www.truefoundry.com/blog/llm-routing-cost-quality-aware-model-selection (2026-06-08): *"Routing is optimization… Failover is availability… Keep the two policies separate and separately observable: 'routed to X for cost' and 'fell back to Y because X was unhealthy' are different events that should look different in your traces."*
  - https://www.genaipatterns.dev/compare/model-router-vs-cascading (2026-04-19): Cascade cost formula `cheapest + (escalation_prob * next) + (double_escalation * top)`; *"Cascades win when the cheap model handles a large majority of traffic and the escalation rate stays under ~30%; they lose when the workload is hard enough that escalations dominate."*
  - https://www.alexcloudstar.com/blog/llm-router-model-routing-fallbacks-2026/ (2026-05-01): *"The fallback model has to be capable enough to actually substitute for the primary. Falling back from a frontier model to a tiny one because it is 'available' produces outputs that are worse than just retrying the primary."*
- **Proposed Fix:** Split the gateway into two explicit, separately-observable layers:
  1. **Reliability layer** (LiteLLM-style): provider outage/rate-limit → fast failover to a *same-tier* model on a different provider. Tracked as `failover_reason: provider_unhealthy`.
  2. **Quality layer** (cascade): schema-violation/low-confidence → slow escalation to a *more capable* model in the same or next provider. Tracked as `escalation_reason: quality_rejection`.
  The two layers must produce distinct audit events. Default `trigger_on` should separate them. Document the cost formula explicitly and add an `escalation_rate` SLO alert (industry: alert on escalation rate, not just errors — "the failure here is silent and shows up only on the invoice").
- **Severity:** CRITICAL (this is the framework's central cost-control mechanism; getting it wrong silently inflates every adopter's LLM bill and the spec explicitly incentivizes the anti-pattern)

### ISSUE-3: outdated_pattern — MCP spec documents the obsolete HTTP+SSE transport and predates the 2026-07-28 MCP v2 release candidate (stateless core, Streamable HTTP, Tasks extension)
- **Type:** outdated_pattern
- **Section:** mcp-api-protocol §2.3, §4; tool-ecosystem §7.1
- **Problem:** The MCP spec (dated 2026-06-17) documents `transport: sse | stdio` and references "SSE (HTTP)" as the remote transport, with `endpoint: /mcp` and CORS config. This is the **2024-11-05** protocol version's HTTP+SSE transport, which the MCP maintainers have **deprecated and replaced** in the 2026-07-28 release candidate (published May 21, 2026 — one week before this spec's nominal context). The new transport is **Streamable HTTP**, the protocol core is now **stateless**, and `tasks/list` has been removed because "it can't be scoped safely without sessions."

  The spec also describes MCP resources (`conversation://{id}/state`) and a stateful session model that the v2 release candidate explicitly moves away from. The spec's §6.1 "Why MCP Over REST" comparison table claims MCP has "State management — Conversation state exposed as MCP Resources" — but v2's stateless core means the stateful resource subscription model is being deprecated in favor of server-rendered UIs (MCP Apps) and the Tasks extension.

  More fundamentally: the spec treats MCP as a stable foundation ("One protocol, universal access") when in mid-2026 MCP is in the middle of its largest breaking revision since launch. The v2 pre-release is explicitly "not for production" (`2.0.0aN`, breaking changes expected), and the maintainers flag that "v1.x remains the stable production line." A regulated-industry framework adopting MCP now needs an explicit version pin and a migration plan, neither of which the spec provides.

- **Evidence:**
  - https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ (2026-05-21): *"The release candidate for MCP `2026-07-28` is now available. It is the largest revision of the protocol since launch… a stateless core that scales on ordinary HTTP infrastructure… Streamable HTTP replaces the older HTTP+SSE transport from the 2024-11-05 protocol version… `tasks/list` is removed because it can't be scoped safely without sessions."*
  - https://www.contextstudios.ai/blog/mcp-v2-alpha-the-july-28-protocol-shift-to-plan-for (2026-06-14): *"MCP v2 Alpha is therefore a testing lane, not a casual upgrade… v1.x remains the stable line recommended for production (PyPI JSON). A team that leaves `mcp` unbounded may not break immediately… A team that wants to test v2 should pin the exact pre-release and run it in a branch."*
  - https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol (2026-04-19): *"Transport guidance has also matured. The current MCP specification lists two standard transports: stdio and Streamable HTTP. It states that Streamable HTTP replaces the older HTTP+SSE transport from the 2024-11-05 protocol version."*
  - https://cordum.io/blog/mcp-model-context-protocol-guide (2026-04-16): *"MCP adoption without contract ownership is just new plumbing on old governance debt."*
- **Proposed Fix:**
  1. Pin the MCP protocol version explicitly in the spec (`mcp.protocol_version: "2025-06-18"` or whichever v1.x stable is targeted). Remove the `sse` transport references; replace with `streamable_http` as the remote transport.
  2. Add a "MCP Versioning" subsection: the framework targets v1.x stable for production; v2 (2026-07-28) is on a watch list with a migration plan covering stateless core, Tasks extension, and MCP Apps.
  3. Re-evaluate the "MCP Resources for conversation state" pattern (§7.2) against v2's stateless model — this may need to move to the Tasks extension or a REST sidecar.
  4. Add the formal deprecation policy (v2 introduces a 12-month deprecation-to-removal window) to the framework's own compatibility commitments.
- **Severity:** CRITICAL (adopters building MCP servers per this spec today will ship a deprecated transport and need to rewrite for v2 within 12 months; for a "regulated industry" framework targeting long-lived deployments, this is a foundation-on-quicksand problem)

### ISSUE-4: missing_alternative — LLM Gateway builds custom structured-output infrastructure and ignores Instructor (3M+ monthly downloads) / PydanticAI, the de-facto Python standard
- **Type:** missing_alternative
- **Section:** llm-gateway §2-§5 (AD 11); tool-ecosystem §10
- **Problem:** The gateway spec defines a custom `LLMCall`/`LLMResult` interface, custom validation pipeline (§3.1), custom retry-on-violation (§3.3), custom type coercion (§3.2), and four "Gateway Validation Strategies" (§5: Native, Post-Process, Hybrid, Validator-Enhanced). This is a from-scratch reimplementation of what **Instructor** does — and Instructor is, per 2026 sources, *"the most popular structured-output library in Python as of 2026"* with **3M+ monthly downloads** and 250 contributors.

  The spec's "Option D: Validator-Enhanced Post-Process" (§5) describes the Instructor/Guardrails pattern almost exactly — *"field-level content quality checks (Instructor + Guardrails pattern)"* — but lists it as a fourth option rather than the default. The spec's `max_retries` + validation-error-injection-into-prompt (§3.3) is Instructor's core mechanism. The spec's Pydantic support (§6.3) is described as a gateway feature, when in reality Pydantic-→-JSON-Schema-→-provider + retry-on-`ValidationError` is precisely what Instructor wraps.

  Building this custom means: (a) every adopter learns a framework-specific structured-output API instead of the widely-documented Instructor API; (b) the framework re-implements multi-provider support (Instructor already supports "OpenAI, Anthropic, Google, Mistral, Cohere, Ollama, DeepSeek, and 15+ LLM providers"); (c) the framework's retry/coercion logic competes with a battle-tested library with 108 releases. For a "reference architecture" whose principle #4 is "Actionable & Extensible" and whose tool ecosystem spec already integrates LangFlow/LangGraph/LangSmith, omitting Instructor is inconsistent.

- **Evidence:**
  - https://python.useinstructor.com/ (2026): *"Instructor is the most popular structured-output library in Python as of 2026… 3M+ monthly downloads… Built on Pydantic for validation, type safety, and IDE support… Works with OpenAI, Anthropic, Google, Mistral, Cohere, Ollama, DeepSeek, and 15+ LLM providers."*
  - https://ai-tldr.dev/learn/production-llmops/guardrails-reliability/llm-output-schema-validation/ (2026-06-12): *"Instructor wraps the OpenAI, Anthropic, and 15+ other SDKs with a thin layer that automatically converts your Pydantic model to a JSON Schema, injects it into the API call, and runs validation + retry in a loop. With `max_retries=3`, Instructor will feed validation errors back to the model automatically, creating a self-healing call."*
  - https://github.com/567-labs/instructor: *"Use Instructor for fast extraction, reach for PydanticAI when you need agents… Instructor keeps schema-first flows simple and cheap."* 108 releases, latest v1.15.1 (2026-04-03).
  - https://github.com/guardrails-ai/guardrails/: Guardrails AI (Apache-2.0) provides the Input/Output Guards + Guardrails Hub validator ecosystem the spec's §5 Option D describes.
- **Proposed Fix:** Reframe the LLM Gateway as a **thin policy layer over Instructor** (or PydanticAI for agent runs). The gateway's job becomes: (a) enforce `output_schema` is always passed (Instructor does this), (b) inject the framework's retry-budget/escalation policy (Instructor supports `max_retries` + Tenacity), (c) add the confidence-threshold gate (§3.5) as a Pydantic `BeforeValidator`, (d) add audit/coercion recording as Instructor callbacks. Replace §5's four custom options with: "Default: Instructor (Pydantic + auto-retry). Optional: Guardrails AI for content validators (PII, toxicity). Custom: plug in any Pydantic-compatible validator." This reduces framework code, adopts the industry standard, and keeps the framework's value-add (budget, escalation, audit) where it belongs.
- **Severity:** CRITICAL (the gateway is the single chokepoint for "All LLM output is JSON" — the framework's hardest constraint; reimplementing the wheel here is the highest-leverage place to adopt OSS instead of building)

---

## HIGH

### ISSUE-5: wrong_approach — Two-pass parallel extraction (LLM 1 narrow + LLM 2 full schema) is a novel dual-scope pattern not found in industry; industry multi-pass is for RECALL, not scope-division
- **Type:** wrong_approach / weak_rationale
- **Section:** extraction-layer §2.5, §2.6 (AD 30)
- **Problem:** The Extract node runs **two LLMs in parallel** on every user turn: LLM 1 with the current state's narrow scope, LLM 2 with the **FULL OpenAPI `components/schemas/`** (all entities, all fields). The spec's rationale (§2.6) claims this "keeps latency equal to a single LLM call, at 2x token cost" and "catches fields user mentioned out of order."

  The problem: this is **not the industry multi-pass pattern**. Every 2026 source describing multi-pass extraction (Google LangExtract, Chaos Cypher, Neo4j Agent Memory, MuSEE) uses multiple passes over the **same** schema to improve **recall** — running N independent extractions and merging non-overlapping results, because "LLMs exhibit stochastic behavior — a single pass might miss entities that another pass catches." The spec's dual-scope pattern instead runs two *different* schemas simultaneously, which:

  1. **Doubles token cost on every turn** for a benefit (recovering out-of-order fields) that the spec itself says is rare ("fields user mentioned out of order").
  2. **Reintroduces cross-field confusion for LLM 2** — the exact problem AD 30 claims to solve. LLM 2 sees "ALL fields across ALL entities" which the spec elsewhere (§7.3) calls the anti-pattern causing the LLM to "Confuse field boundaries — extract `interest_rate` into a `submit_lead` payload."
  3. **Requires user confirmation for LLM 2-only fields** (§2.6: "Fields found ONLY by LLM 2 require user confirmation"), adding a clarifying turn for every broad-scope hit — a latency cost the spec doesn't budget.
  4. **Has no industry precedent.** No cited source implements dual-scope parallel extraction. The spec's own reference implementation (mfangdai-agent `src/executors/extract.py`) uses single-pass hybrid LLM+regex, not dual-LLM parallel.

  The cost/accuracy trade-off is asserted, not measured: "Token cost is low (small model, small schemas)" — but LLM 2 uses the *full* schema, which is the opposite of small. For a 30-field domain, LLM 2's prompt is 30 fields × descriptions + examples, on every turn, forever.

- **Evidence:**
  - https://upaspro.com/googles-langextract-just-solved-llm-hallucinations/ (2026-02-23): *"When `extraction_passes > 1`, the library runs N independent single-pass extractions over the same document and merges results using a first-pass-wins strategy… This is a recall optimization. LLMs exhibit stochastic behavior — a single pass might miss entities that another pass catches. Rather than increasing temperature (which hurts precision), multiple independent passes at the same temperature increase recall."* — Multiple passes, **same schema**, for recall.
  - https://chaoscypher.com/docs/architecture/extraction-pipeline/entity-extraction (2026-06-12): 2-pass approach is **entities-then-relationships** (sequential, different task per pass), not dual-scope-same-task.
  - https://www.intraview.ai/explore/juanceresa/sift-kg/tours/pipeline/ (2026-05-05): *"One combined prompt per chunk… Cost halves and consistency improves, because the model picks relations from the same entity list it just produced, instead of re-identifying entities on a second pass."* — Industry is consolidating passes, not splitting them.
  - https://neo4j.com/labs/agent-memory/explanation/extraction-pipeline/: Multi-stage pipelines use **different extractor types** (spaCy → GLiNER → LLM) for speed/cost tiering, not dual-LLM-same-tier-different-scope.
- **Proposed Fix:** Replace the dual-scope parallel design with one of:
  - **(A) Single-scope + multi-pass recall (industry standard):** Run LLM 1 (narrow scope) once. If confidence < threshold or required fields missing, run a second pass over the *same narrow scope* (recall boost). Drop LLM 2 entirely. Recover out-of-order fields via the conversation context window (last 3+3 messages) which already lets the LLM see prior turns.
  - **(B) Single-scope + deferred broad scan:** Only run the broad-scope scan when the narrow-scope extraction is *incomplete* (missing required fields), not on every turn. This bounds the 2x cost to the incomplete-extraction case.
  - **(C) If dual-scope is kept:** Move LLM 2 to a cheaper tier explicitly (per AD 32), document the per-turn token cost of the full schema, and make LLM 2 opt-in per node (default off). Add an eval measuring whether LLM 2 actually recovers enough out-of-order fields to justify 2x cost on every turn.
  In all cases, stop claiming this is "industry standard" — it isn't.
- **Severity:** HIGH (doubles LLM cost on every turn for the framework's primary use case; the rationale misrepresents industry practice)

### ISSUE-6: outdated_pattern — A2A spec predates A2A v1.0 + IBM ACP merger under Linux Foundation; uses custom Agent Registry instead of the standard Agent Card at /.well-known/agent-card.json
- **Type:** outdated_pattern / missing_alternative
- **Section:** a2a-protocol §2, §4 (AD 24)
- **Problem:** The A2A spec (dated 2026-06-17) references "Google A2A Protocol" as a "conceptual reference" and invents a custom `Agent Registry` with `backend: postgresql | file | consul` and a custom `agent_registry` YAML schema (§4.1). But A2A was **donated to the Linux Foundation in June 2025**, reached **v1.0 in early 2026**, and as of mid-2026 has **150+ organizations** adopting it (AWS, Microsoft, Salesforce, SAP, IBM, ServiceNow) with production SDKs in 5 languages. The standard discovery mechanism is **Agent Cards served at `/.well-known/agent-card.json`** — a well-known URL pattern, *not* a centralized registry.

  Critically, in **August 2025 IBM Research and Google announced that IBM's Agent Communication Protocol (ACP) joined A2A** under the LF AI & Data umbrella. The spec's custom A2A message format (§2.2) and custom registry predate this consolidation and do not reference the unified spec. The spec's `a2a_request`/`a2a_response` envelope (§2.2) is a custom dialect, not the A2A v1.0 `message/send` + `tasks/get` + Task lifecycle (`submitted/working/completed/failed`) that the official SDKs implement.

  The result: an adopter following this spec builds a custom A2A dialect that doesn't interop with the 150+ organizations on the official spec. For a framework whose stated principle is "industry-agnostic" and whose tool ecosystem integrates universal tools (LangFlow, MCP), inventing a parallel A2A dialect is inconsistent.

- **Evidence:**
  - https://zylos.ai/research/2026-05-16-agent-to-agent-communication-protocols-a2a-mcp/ (2026-05-16): *"A2A was announced by Google in April 2025… contributed to the Linux Foundation in June 2025, and reached v1.0 in early 2026. As of mid-2026, 150+ organizations — including AWS, Microsoft, Salesforce, SAP, IBM, and ServiceNow — have adopted it in production. The GitHub repository has surpassed 22,000 stars, with production-ready SDKs in Python, JavaScript, Java, Go, and .NET."*
  - https://tyk.io/learning-center/agent-protocols-a-complete-guide-to-mcp-a2a-and-acp/ (2026-06-04): *"In August 2025, IBM Research and Google announced that IBM's Agent Communication Protocol (ACP) would join forces with Google's Agent2Agent Protocol (A2A) under the Linux Foundation's LF AI & Data umbrella."*
  - https://github.com/google/A2A: *"Originally developed by Google and now donated to the Linux Foundation, A2A provides the definitive common language for agent interoperability… Agent Discovery: Via 'Agent Cards' detailing capabilities and connection info."*
  - https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/ (2026-03-18): *"Each A2A agent publishes an Agent Card at a well-known URL (`/.well-known/agent-card.json`) that describes its name, capabilities, and endpoint."*
- **Proposed Fix:**
  1. Replace the custom `Agent Registry` (§4) with **Agent Card discovery at `/.well-known/agent-card.json`** per A2A v1.0. The "registry" becomes an optional catalog of known Agent Card URLs (a list of URLs, not a custom schema).
  2. Replace the custom `a2a_request`/`a2a_response` envelope (§2.2) with the A2A v1.0 `message/send` + `Task` lifecycle (`submitted/working/completed/failed`). The spec's `status: completed | failed | partial | timeout` maps to A2A's task states.
  3. Reference the official Python/Go SDKs rather than defining a custom wire format. The framework's value-add is the YAML sub-workflow→A2A mapping (§2.3), not the protocol itself.
  4. Note that A2A complements MCP (agent↔agent vs agent↔tool) — the spec already gets this right (§3) but should cite the official "MCP for tools, A2A for agents" framing now that both are LF-hosted.
- **Severity:** HIGH (adopters following this spec build a non-interoperable A2A dialect; the official spec is 5 months older than this doc and has 22k stars + 5 official SDKs)

### ISSUE-7: missing_alternative — State machine spec mandates LangGraph-only runtime and ignores Temporal for durable execution; regulated industries with side-effecting workflows need both
- **Type:** missing_alternative
- **Section:** state-machine-design §4; VISION.md AD 1; routing-execution §5 (sub-workflow async), §6 (retry)
- **Problem:** AD 1 commits to "Python + LangGraph" as the runtime, and the state-machine spec (§4) says "The framework auto-generates a LangGraph StateGraph from the YAML." LangGraph is treated as the complete execution substrate. But the framework's own use cases include **side-effecting workflows** (lead distribution, payment collection, dangerous_operation_write tools) with **async sub-workflows** (§5.4), **human-in-the-loop approval gates** (§7.5), and **retry budgets** that may span minutes.

  2026 industry guidance is emphatic that **LangGraph alone is insufficient for side-effecting production agents**. LangGraph's checkpointer provides durability *within a thread*, but it does not provide: event-history-backed replay, activity-level idempotency, multi-day pause/resume, or saga-pattern compensating transactions. The Temporal team shipped an official LangGraph integration in 2026 specifically because *"For side-effecting production agents, the winning pattern is often LangGraph for reasoning plus Temporal for orchestration."* LangChain's own comparison page now lists "LangGraph + Temporal" as the recommended stack for "workflows with 3+ tool calls or external API retries" and "production side effects (deploy, delete, payments)."

  The framework's async sub-workflow (§5.4: "Parent fires sub-workflow and continues immediately; result delivered via callback") is exactly the case Temporal handles natively (continue-as-new, durable callbacks) and LangGraph handles only with custom callback plumbing that the spec hand-waves as "webhook | polling | message_queue" (a2a-protocol §5.4). For a *regulated-industry* framework where "distribute lead" is a `dangerous_operation_write` requiring an audit trail and idempotent retries, the absence of Temporal (or an equivalent durable-execution layer) is a structural gap.

- **Evidence:**
  - https://cordum.io/blog/temporal-vs-langgraph (2026-04-29): *"LangGraph helps you model agent reasoning and tool flow. Temporal keeps multi-step execution durable when workers restart or networks fail. You usually need both once real side effects enter the workflow… For side-effecting production agents, the winning pattern is often LangGraph for reasoning plus Temporal for orchestration."* Table explicitly: "Workflow with 3+ tool calls or external API retries → LangGraph + Temporal"; "Production side effects (deploy, delete, payments) → LangGraph + Temporal + pre-dispatch governance gate."
  - https://www.langchain.com/resources/langgraph-vs-temporal (2026-06-06): *"Many teams run both, keeping Temporal for what it was designed for and using LangGraph for their agent work."* Capability table: Temporal has durable execution ✔️, LangGraph ✔️ — but Temporal adds saga patterns with compensating transactions.
  - https://docs.temporal.io/develop/python/integrations/langgraph: Official Temporal-LangGraph plugin supports both Graph API and Functional API; *"Long-running graphs can hit Temporal's per-Event history size limit. Use continue-as-new."*
  - https://www.alongside.team/blog/temporal-vs-langgraph-long-running-ai-workflows (2026-05-04): *"Temporal is usually the better choice than LangGraph when a team needs a more defensible production path, stronger control, and clearer operational trade-offs."*
- **Proposed Fix:** Do NOT drop LangGraph — it remains the right tool for the agent reasoning graph. But:
  1. Revise AD 1 to "Python + LangGraph (agent reasoning) + optional Temporal (durable orchestration for side-effecting workflows)." Make Temporal an *opt-in* layer for workflows that include `dangerous_operation_write` tools or async sub-workflows with multi-minute/multi-day pause.
  2. In routing-execution §5.4 (async sub-workflow), add a "Durable Execution" subsection: async sub-workflows involving side effects SHOULD be wrapped in a Temporal activity (or equivalent) so that worker restarts don't lose in-flight lead distributions.
  3. In the retry section (§6), distinguish *within-node* retries (LangGraph checkpointer is fine) from *cross-workflow* retries (need durable orchestration). The current "all errors → errorNode" handles within-node; it doesn't handle "the lead distribution API was called, the worker crashed, did the call happen?"
  4. Add Temporal to the tool ecosystem spec (§1.1) under "Runtime Engine."
- **Severity:** HIGH (the framework's flagship use cases — lead distribution, payment collection — are exactly the side-effecting cases where LangGraph-only durability is risky; this is a foundation decision that's expensive to reverse post-adoption)

### ISSUE-8: wrong_approach — Daily token budget with HTTP 500 hard service-stop is operationally naive; industry uses staged warn→throttle→reject with per-user/per-team granularity
- **Type:** wrong_approach / missing_alternative
- **Section:** llm-gateway §4.1a (AD 33)
- **Problem:** AD 33 specifies: *"Exceeding budget → HTTP 500, service stop."* The gateway enforces a **single daily token limit and cost cap per server**. When exceeded, the *entire service* returns HTTP 500 and stops processing all users.

  This is an operational anti-pattern. Industry LLM cost-control tools (LiteLLM, TokenLens, costfuse, Fairvisor, Archestra, LLM0) all implement **staged actions** (warn → throttle → reject) with **per-user/per-team/per-tenant granularity**, not a global kill switch:
  - Fairvisor: "At 80% of budget: warning header. At 95%: throttle with 200–500ms delay. At 100%: reject with 429."
  - costfuse: per-actor (per-client) caps with `CostfuseBlocked` exception the app catches and degrades gracefully.
  - LLM0: "per-end-user daily/monthly USD spend caps" with auto-downgrade to a cheaper model on limit (`default_on_limit_behavior=downgrade`).
  - Archestra: "token-cost limits scoped to organization, team, user, agent, LLM proxy, or virtual API key."

  A single server-wide HTTP 500 means: (a) one noisy user exhausts the budget and *all* users are denied service (availability incident); (b) there's no graceful degradation (downgrade to cheaper model, queue, etc.); (c) the error is HTTP 500 (server error) when it's actually a 402/429 (client/budget) — misleading for clients; (d) `on_budget_exceeded: warn_only` for dev is the only escape hatch, meaning prod has no middle ground between "spend unlimited" and "hard stop."

- **Evidence:**
  - https://fairvisor.com/for/finops/: *"Don't just observe overspend — prevent it. Set budgets per org, team, user, or endpoint. Fairvisor enforces them at the edge with staged actions: warn → throttle → reject… At 80% of budget: warning header. At 95%: throttle with 200–500ms delay. At 100%: reject with 429."*
  - https://github.com/costfuse/costfuse (2026-04-27): *"maxSpendPerHour / maxSpendPerDay… If any rule trips before the call, costfuse throws `CostfuseBlocked` — your code can catch this, fall back to a cheaper model, queue for later, or surface 'rate limit hit' to your end-user. Tokens are never spent."*
  - https://github.com/llm0ai/llm0 (2026-04-13): *"Hard caps that actually stop spend… per-end-user daily/monthly USD spend caps… auto-downgrades to a cheaper model if you set `default_on_limit_behavior=downgrade`."* Returns 402/429, not 500.
  - https://archestra.ai/docs/platform-costs-and-limits (2026-06-09): *"Limits scoped to the organization, team, user, agent, LLM proxy, or virtual API key… Rolling intervals reset after elapsed time."*
  - https://github.com/stephenlthorn/token-lens (2026-03-11): *"Budget Caps: Global daily and monthly spend limits with automatic request blocking… Cost Anomaly Detection: Rolling mean + 2σ detection."*
- **Proposed Fix:**
  1. Replace the single server-wide budget with **per-user + per-workflow + per-server** budget tiers (the framework already has `user_id` in AgentState — use it).
  2. Replace HTTP 500 hard-stop with **staged actions**: 80% → warn (response header + audit log); 95% → throttle (inject delay or downgrade to cheaper tier per AD 32); 100% → reject with **429** (not 500) + structured error so the caller can queue/escalate.
  3. Add `on_budget_exceeded: downgrade_to_cheaper_model` as the recommended prod default (not `stop_service`), consistent with AD 32's "cheap model by default" philosophy.
  4. Add cost-anomaly detection (rolling mean + 2σ) — a spike from a runaway loop should trip before the daily cap.
  5. Reference LiteLLM's budget/rate-limit primitives (the tool-ecosystem spec already lists LiteLLM-adjacent tools) rather than building custom.
- **Severity:** HIGH (a single global kill switch is an availability footgun; for a multi-tenant "regulated industry" framework, per-tenant isolation is a security requirement, not a nice-to-have)

### ISSUE-9: weak_rationale — Goal-driven workflow's async LLM goal-setting with 1-second timeout is underspecified and contradicts the 2026 goal-engineering pattern (deterministic verifier + external persistent state)
- **Type:** weak_rationale / missing_alternative
- **Section:** response-generation §2, §4 (AD 14)
- **Problem:** AD 14 specifies "Async goal set at start; parallel goal check at end; 422 on large gap." The implementation (§2.3): goal is "dispatched asynchronously at workflow start" by an LLM, with `timeout_ms: 1000` (1 second). §2.4: "If the async goal setter has not completed by then, the framework waits (1-second timeout max). If the goal setter fails → a default goal is derived from the intent + collected entities." The goal checker (§4) is an LLM node that runs in parallel with response generation.

  Two problems:
  1. **The 1-second timeout is unrealistic for an LLM call.** Even gpt-4o-mini routinely exceeds 1s under load; the framework's own LLM Gateway specifies `timeout_ms: 30000` per attempt (§6.2). A 1s async timeout means the goal setter will *almost always* fall back to the default `derive_from_intent` goal — making the LLM goal setter dead code in practice. The spec doesn't reconcile this.
  2. **The pattern diverges from the 2026 goal-engineering state of the art.** xAI's `/goal` mode (June 2026) and the AgentFlow runtime use **deterministic verifiers** + **external persistent goal state** (GOAL.md), not async LLM with timeout. The verifier "does not call an LLM" — it checks artifact evidence (non-empty output, file/URL/JSON artifacts). The goal survives context compaction and pause/resume because it lives outside the LLM context. The spec's goal lives in `agentState.goal` (in-context, checkpointed) and is verified by an LLM — the implementer grades its own homework.

  The spec's gap_threshold (0.3) and 422-on-gap are reasonable, but the *mechanism* (LLM goal setter + LLM goal checker, both in-context, 1s timeout) is the weak part.

- **Evidence:**
  - https://cobusgreyling.medium.com/goal-engineering-788b5ca00e7f (2026-06-23): *"`/goal` persists an objective across turns, but the chat context does not. Without external state… GOAL.md is the external memory file for goal mode… a verifier that does not let the implementer grade its own homework."*
  - https://github.com/Yupoer/agentFlow: *"Deterministic verification layer. It does not call an LLM. It checks executor results and artifact evidence such as: non-empty output for completed steps, file artifacts, URL artifacts, JSON/Markdown artifacts."*
  - https://arxiv.org/html/2604.02375 (KAIJU): *"A structured graph-based LLM workflow enables composable, verifiable execution units… a lightweight reflector evaluates the evidence gathered so far against the original query."*
- **Proposed Fix:**
  1. Either raise the async timeout to a realistic value (5–10s) OR make the goal setter *synchronous at workflow start* (the workflow can't meaningfully proceed without a goal — the "async" benefit is ~1 turn of latency, not worth a default-goal fallback).
  2. Make the goal verifier **deterministic by default** (check `expected_outputs` presence in outcomes, `expected_entities` presence in collectedFields, `success_criteria` as boolean expressions) — the LLM goal checker should be an *opt-in* for soft criteria, not the default. This aligns with the framework's own "deterministic core" principle (AD 3).
  3. Persist the goal *outside* agentState (a dedicated goal store) so it survives checkpoint compaction and is auditable independently — this matters for regulated industries where "what was the agent's goal?" is a compliance question.
  4. Cite the xAI `/goal` / AgentFlow pattern as prior art for the goal-engineering layer.
- **Severity:** HIGH (the goal checker is the framework's correctness backstop — "did we actually achieve what we set out to do?"; an LLM grading its own work with a 1s timeout that effectively disables the LLM goal setter is a weak backstop for regulated industries)

### ISSUE-10: missing_alternative — PII scrubbing spec only references Presidio and misses OpenAI Privacy Filter (April 2026) which catches ~38% more contextual PII; the spec's regex-only domain-model pii_rules is insufficient for contextual PII
- **Type:** missing_alternative
- **Section:** response-generation §8; tool-ecosystem §9; domain-model §3 (pii_rules)
- **Problem:** The PII design (response-generation §8.2) defines `pii_rules` in the domain model as **regex patterns + field-masking strategies**: `pattern: "\\b[0-9]{16}\\b"` (credit card), `fields: [phone, email, id_number]` with `partial_mask`. The tool ecosystem (§9) names Presidio as the PII engine.

  Two gaps:
  1. **Regex-only rules miss contextual PII.** "Schedule a meeting with Sarah from legal" — "Sarah" is PII but won't match any regex. Presidio's spaCy NER catches *some* of this, but the spec's `pii_rules` (domain model) are regex-only and don't invoke NER. The response-generation §8.3 "prompt entity filter" masks known sensitive *fields* but does nothing for PII that appears *in the user's free text* and is then echoed by the LLM in the response.
  2. **OpenAI Privacy Filter (released April 2026) is not mentioned.** It's a bidirectional token-classification model (Apache-2.0, on-premises, 128k context) that catches ~38% more contextual names than Presidio 2.2 with default settings. For a framework targeting regulated industries where "the LLM echoed the user's address back" is a GDPR/HIPAA violation, the PII layer is the wrong place to skimp.

  The spec's layered approach (regex → Presidio NER → contextual LLM) is the *right* architecture (per sovergate.com's 3-layer guide) — but the spec only implements layer 1 (regex) in the domain model and names Presidio as the engine; it doesn't specify the NER layer configuration or mention the contextual layer at all.

- **Evidence:**
  - https://privacyfilter.run/blog/openai-privacy-filter-vs-presidio (2026-04-28): *"OpenAI Privacy Filter uses the full LLM context window… 'my colleague Alex', 'the patient mentioned above', and 'her home address in Milan' all register correctly as PII. In internal testing with 500 support-ticket snippets, the hosted model caught ~38% more contextual names than Presidio 2.2 with default settings."* Table: Presidio = self-hosted, custom recognizers, English-primary; OpenAI Privacy Filter = on-prem, 30+ languages, contextual.
  - https://github.com/openai/privacy-filter (2026-04-17): *"OpenAI Privacy Filter is a bidirectional token-classification model for PII detection and masking… pretrained autoregressively… 128,000-token context window… Fine-tunable… Apache 2.0."*
  - https://sovergate.com/blog/llm-pii-scrubbing-guide (2026-06-02): *"Layer 1: Regex (0.1–0.5ms). Layer 2: NER with Presidio (5–20ms). Layer 3: Contextual LLM (50–200ms, high-risk only). For most production pipelines, Layer 1 + Layer 2 is the right starting point."*
  - https://predictionguard.com/blog/pii-detection-redaction-llm-pipelines-regulated-industries (2026-05-06): *"Presidio is an open-source library, not a service… Before Presidio can satisfy a HIPAA or GDPR audit, you need to build: authentication, audit logging, access control, monitoring, custom recognizers."*
- **Proposed Fix:**
  1. Extend the domain-model `pii_rules` to support a third strategy beyond regex/field-mask: `contextual_ner` (invoke Presidio's spaCy/transformers recognizer) and `contextual_llm` (invoke OpenAI Privacy Filter or equivalent for high-risk nodes).
  2. In response-generation §8, specify the 3-layer pipeline explicitly: Layer 1 (regex, always) → Layer 2 (Presidio NER, default on for response text) → Layer 3 (contextual model, opt-in for `sensitive_data_read` nodes).
  3. Add OpenAI Privacy Filter to the tool-ecosystem PII catalog (§9) alongside Presidio, with the trade-off table (self-hosted vs on-prem model, latency, contextual accuracy).
  4. Add a note: for HIPAA/GDPR audit readiness, Presidio alone is insufficient — the framework should document the auth/audit/access-control layers that wrap the PII engine (per PredictionGuard's analysis).
- **Severity:** HIGH (PII leakage in regulated industries is a reportable breach; the spec's regex-only domain rules + single-engine reference under-protects the highest-risk case)

### ISSUE-11: weak_rationale — Intent classification removed keyword fallback entirely (v0.6.0), contradicting the framework's own "deterministic fallback" principle and the 2026 cost-optimization consensus
- **Type:** weak_rationale / wrong_approach
- **Section:** intent-classification §2.4, §3.4 (changelog v0.6.0)
- **Problem:** The intent spec changelog (v0.6.0) states: *"Remove keyword fallback entirely: delete §3.4 (Keyword Matching)… simplify to LLM-only flow with `unrecognized_intent` as the sole fallback."* §3.4: *"There is no keyword fallback. A low-confidence result and a failed LLM call produce the same outcome: `unrecognized_intent`."*

  This directly contradicts:
  1. **The framework's own principle** (VISION.md §6.2: "Deterministic fallback (regex/keyword for every extractable field)") and AD 3 ("LLM excels at understanding; execution must be auditable"). The extraction layer *kept* deterministic fallback (`x-fallback` in domain model); intent classification dropped it.
  2. **The 2026 industry consensus** that deterministic-first cascade is the single biggest LLM cost lever. The pattern: regex/keyword handles 60–70% of inputs at $0 and microseconds; LLM handles the 30% tail. The spec's own Option B (§2.4 "Cascade") documents this correctly *with a comparison matrix* showing 0 LLM cost for obvious intents — then the changelog removes it as the default.
  3. **The cost rationale (AD 32: "cheap model by default").** Every "hello" / "yes" / "help" / "what's my status" now costs an LLM call (~500ms, $0.001+) when a keyword match would handle it in <5ms at $0. For a high-volume customer-facing chatbot (the framework's primary use case), this is the *worst* place to remove deterministic handling.

  The stated reason — "avoids keyword collision across 17+ intents" — is a maintenance argument, not a correctness argument. Industry tools (PARSELY-DIP, MicroResolve) solve collision with cascading layers (regex first, NLP second, LLM last) where each layer only fires if the one above didn't match.

- **Evidence:**
  - https://tianpan.co/blog/2026-04-16-minimum-viable-baseline-ai-feature (2026-04-16): *"Build the simplest deterministic system that could possibly solve the problem… Keyword and regex matching handles classification, routing, and extraction for a large fraction of real-world inputs… the signal is explicit in the text and a pattern match will find it. The failure mode is that engineers estimate coverage will be 20% when it is actually 70%."*
  - https://github.com/gbutiri/parsely-dip: *"Deterministic intent parser — RegEx and NLP pipeline that intercepts known commands before they reach your LLM… A regex handles it in microseconds. An LLM spends tokens guessing what you already know."*
  - https://github.com/gladius/microresolve (2026-03-03): *"System 1 relay for LLM apps… sub-millisecond reflex layer… 50–200× cheaper, 3–5× faster. When confidence is low, the LLM gets the full catalog as fallback."*
  - https://www.genaipatterns.dev/compare/model-router-vs-cascading: *"Cascading can achieve better cost savings than routing because it always starts with the cheapest model. If 70% of queries are genuinely simple, the cheap model handles them and the expensive model is never called."*
- **Proposed Fix:** Restore keyword/regex as **Layer 0** (deterministic pre-filter), consistent with the spec's own Option B and the framework's deterministic-fallback principle. Cascade: Layer 0 (keyword/regex, confidence ≥ 0.95 → return, $0) → Layer 1 (LLM, the current default flow) → `unrecognized_intent`. The 17-system-intent keyword lists already exist in the spec (§2.1) — they're currently "metadata only." Make them the Layer 0 matcher. This is *cascading* (deterministic-first), not *fallback* (LLM-first + deterministic salvage) — the spec conflated the two when it removed keyword matching.
- **Severity:** HIGH (every customer-facing adopter pays an LLM call per greeting/confirmation/help — the highest-volume, lowest-value intents; contradicts the framework's own cost-optimization rationale)

---

## MEDIUM

### ISSUE-12: missing_alternative — Testing methodology doesn't reference 2026 state-of-the-art: stochastic test semantics (AgentAssay), mutation testing (TDAD), or layer-isolated regression harnesses
- **Type:** missing_alternative
- **Section:** three-tier-agent-testing-methodology (entire)
- **Problem:** The three-tier methodology (Tier 1 mock, Tier 2 scripted LLM, Tier 3 persona LLM) is reasonable and well-validated against mfangdai-agent (65/65, 88.1%, 100%). But it doesn't reference the 2026 academic/industry state of the art for agent testing, which has matured significantly:

  1. **Stochastic test semantics with provable guarantees** (AgentAssay, arXiv 2603.02601): defines `(α,β,n)`-test triples with confidence-interval-grounded verdicts and Wald's SPRT for cost-efficient reruns. The spec's "run N≥3 times" is a heuristic; AgentAssay provides the formal foundation for *how many* runs are needed for a given confidence level.
  2. **Mutation testing for agents** (TDAD, arXiv 2603.08806): generates plausible faulty prompt variants and measures whether the test suite detects them (86–100% mutation scores). The spec has no equivalent — a passing Tier 2 suite that passes faulty behavior too provides no signal.
  3. **Layer-isolated regression harnesses** (arXiv 2606.11686): decomposes the agent into architectural layers, each asserted in a no-LLM pure mode, gated per-PR against a locked baseline. The spec's Tier 1 is close but doesn't formalize *per-layer* slice gates or regression injection.
  4. **Structural testing with OpenTelemetry traces** (arXiv 2601.18827): uses traces + mocking + assertions for automated root-cause analysis — the spec's `LayerTrace` is a simpler version.

  The spec's 85% Tier 2 intent-accuracy target is also low relative to what's achievable: TDAD reports 97% mean hidden pass rate; the spec's own mfangdai validation hit 88.1% strict (83% + 5.1% soft).

- **Evidence:**
  - https://arxiv.org/pdf/2603.02601 (AgentAssay): *"Stochastic Test Semantics… `$(\alpha,\beta,n)$-test triple… Wald's Sequential Probability Ratio Test (SPRT) for cost-efficient agent testing… behavioral fingerprints… Hotelling's T² test with provably higher power per sample than univariate pass-rate testing."*
  - https://arxiv.org/pdf/2603.08806 (TDAD): *"92% v1 compilation success with 97% mean hidden pass rate… semantic mutation testing via a post-compilation agent that generates plausible faulty prompt variants, with the harness measuring whether the test suite detects them."*
  - https://arxiv.org/html/2606.11686 (Layer-Isolated Evaluation): *"a single-layer regression that an aggregate pass-rate barely registers (-3 to -8 pp)… lands as a -25 to -91 pp crater on the responsible slice."*
  - https://www.arxiv.org/pdf/2601.18827: *"structural testing of LLM-based agents: traces (OpenTelemetry), mocking for reproducible LLM behavior, assertions for automated verification."*
- **Proposed Fix:**
  1. Add a "Theoretical Foundation" subsection referencing AgentAssay for the run-count question (replace "N≥3" with "N per SPRT for target α,β").
  2. Add a Tier 2.5 "Mutation Testing" step: after a prompt change, generate faulty prompt variants and verify the Tier 2 suite catches them (cite TDAD).
  3. Formalize Tier 1 as a *layer-isolated* harness with per-layer slice gates (NLU / routing / response) and regression injection, not just "mock L1, test L2+L3."
  4. Raise the Tier 2 intent-accuracy target to 90% strict (the spec's own soft-match data shows 83% strict + 5.1% soft = 88.1%; TDAD shows 97% is achievable with test-driven prompt compilation).
- **Severity:** MEDIUM (the methodology is sound; these are refinements that make it defensible to a rigorous auditor rather than just practical)

### ISSUE-13: wrong_approach — Sub-workflow reuse spec claims LangGraph Send API supports parallel sub-workflow invocation, but LangGraph docs explicitly warn against per-thread subgraph parallel calls
- **Type:** wrong_approach
- **Section:** routing-execution §5.3 (Pattern B Parallel), §5.7; a2a-protocol §5
- **Problem:** The spec's sub-workflow parallel pattern (§5.3 Pattern B) uses `parallel_nodes: fan_out` and claims "LangGraph `Send` API fans out to multiple nodes simultaneously." §5.7 marks "Parallel fan-out/fan-in | `Send()` API | ✅ (v0.2+)". The async sub-workflow (§5.4) has parent continue while sub-workflow runs.

  LangGraph's own docs (2026) explicitly warn:
  - *"Per-thread subgraphs do not support parallel tool calls. When an LLM has access to a per-thread subagent as a tool, it may try to call that tool multiple times in parallel… This causes checkpoint conflicts because both calls write to the same namespace."*
  - *"If you need multiple subgraph runs, don't imperatively invoke a subgraph multiple times in one node when checkpointing; use `Send` fanout instead. Otherwise you may hit `MULTIPLE_SUBGRAPHS` naming/namespace limits."*
  - Per-invocation mode (recommended) supports parallel calls; per-thread does not.

  The spec's async sub-workflow + parent concurrent write scenario (routing-execution §1.2 "Conflict scenario — parallel sub-workflow + parent") is *exactly* the conflict case LangGraph warns about. The spec acknowledges the conflict and resolves it with "append-only" reducers — but this means two parallel sub-workflows writing to `collectedFields` produce a `[value_a, value_b]` conflict list, which the spec itself admits requires "downstream node or human reviewer decides which to use." For a *deterministic* framework, "human reviewer decides" is a failure of determinism.

- **Evidence:**
  - https://docs.langchain.com/oss/python/langgraph/use-subgraphs: *"Per-thread subgraphs do not support parallel tool calls… This causes checkpoint conflicts because both calls write to the same namespace."*; *"If you're building with pure LangGraph `StateGraph`, you need to prevent parallel tool calls yourself."*
  - https://forum.langchain.com/t/best-practices-for-parallel-nodes-fanouts/1900 (2025-10-22): *"Prefer `Send` over imperative subgraph calls inside a single node… Otherwise you may hit `MULTIPLE_SUBGRAPHS` naming/namespace limits."*; *"Default `recursion_limit` is 25 super-steps; increase per-run if your workflow loops over many barrier synchronizations."*
  - https://markaicode.com/langgraph-subgraphs-composable-agent-architecture/ (2026-03-10): *"Checkpointing works at the parent level… Subgraph-internal state is not checkpointed separately unless you compile subgraphs with their own checkpointers."*
- **Proposed Fix:**
  1. In §5.3, distinguish **per-invocation subgraphs** (support parallel via `Send`, recommended) from **per-thread subgraphs** (no parallel — the spec's async pattern defaults to this). Make per-invocation the default for parallel sub-workflows.
  2. In §5.4 async sub-workflow, add an explicit constraint: "Async sub-workflows MUST write to disjoint state keys; the framework's load-time reducer check (§1.3) rejects workflows where async sub-workflows and parents write the same key with `last_write_wins`." The current "append-only for everything" produces conflict lists that break determinism.
  3. Add the `recursion_limit` (default 25) to the sub-workflow nesting limit (§5.1 `max_sub_workflow_depth: 3`) — these are separate limits and both can fire.
  4. Cite LangGraph's `Send` fanout as the *only* supported parallel-subgraph mechanism; imperative subgraph invocation in a single node is forbidden.
- **Severity:** MEDIUM (the spec's append-only workaround "works" but silently breaks the determinism guarantee the framework is built to provide)

### ISSUE-14: missing_alternative — LLM Gateway "Hybrid" default doesn't account for OpenAI Structured Outputs' hard schema constraints that conflict with the OpenAPI 3.1 schemas the domain model uses
- **Type:** missing_alternative / weak_rationale
- **Section:** llm-gateway §5 (Option C Hybrid), §6.4 (preprocessing); domain-model §2 (OpenAPI 3.1)
- **Problem:** AD 29 adopts OpenAPI 3.1 Schema Objects for the domain model, which uses `$ref`, `oneOf`+`discriminator`, `allOf`, `if`/`then`/`else`, `additionalProperties: false`. AD 11 + the gateway's "Option C: Hybrid (Default Recommendation)" (§5) says "Try Option A [provider-native structured output] first." §6.4 acknowledges the mismatch: *"OpenAI Structured Outputs does not support `$ref` or `$defs`… Remove `$comment`, `examples`, `default`… `oneOf`/`anyOf` (Anthropic limited support)."*

  But the architectural decision doesn't reconcile this: the domain model *requires* `oneOf`+`discriminator` (§2.3 polymorphism), `if`/`then`/`else` (§2.3 conditional validation), and `$ref` composition — **none of which OpenAI Structured Outputs supports**. So the "Hybrid default" means: for every extraction node, the framework must flatten/rewrite the OpenAPI schema into a provider-compatible subset, losing the polymorphism and conditional validation that justified OpenAPI 3.1 in the first place. The spec's §6.4 `on_exceed_limit: warn_and_flatten` silently flattens — which means the LLM sees a degraded schema and the validation that the domain model encodes (`if mortgage_product == adjustable then interest_rate required`) is not enforced at generation time.

  Industry guidance (2026) is explicit: *"Not all JSON Schema features are supported in strict mode… Unsupported keywords (`if/then`, `not`, `contains`) are silently ignored or cause a validation error at request time. Always test your schema against the provider's supported keyword list before shipping to production."* The spec doesn't require this test.

- **Evidence:**
  - https://ai-tldr.dev/learn/llm-apis/streaming-structured-outputs/json-mode-vs-structured-outputs/ (2026-06-12): *"Not all JSON Schema features are supported in strict mode. OpenAI's grammar-based enforcement requires `additionalProperties: false`… all fields in `required`. Unsupported keywords (like `if/then`, `not`, `contains`) are silently ignored or cause a validation error at request time."*
  - https://www.kommunicate.io/blog/openai-structured-output-guide/ (2026-05-06): *"Root objects cannot be anyOf type — OpenAI supports a subset of JSON Schema, not the full spec… Keep the schema small: only fields your backend actually uses."*
  - https://folarin.dev/blog/structured-outputs-and-function-calling (2026-06-20): *"Keep schemas flat and shallow. Deeply nested schemas with many optional-via-null fields are slower to generate and more error-prone. Flatten where you can."*
  - https://developers.openai.com/api/docs/guides/structured-outputs: *"We recommend always using Structured Outputs instead of JSON mode when possible."*
- **Proposed Fix:**
  1. In the gateway §5 Option C, add an explicit constraint: "OpenAI/Anthropic Structured Outputs support a *subset* of JSON Schema. The framework's schema preprocessor (§6.4) MUST flatten `$ref`/`oneOf`/`if-then-else` into a provider-compatible schema *and* retain the original OpenAPI schema for post-process validation. The LLM sees the flattened schema; the gateway validates against the *original* schema."
  2. Make `on_exceed_limit: error` the default (not `warn_and_flatten`) for regulated industries — silent flattening that drops `if/then/else` validation is a correctness risk.
  3. Add a CI check (per industry guidance): "Every `output_schema` MUST be tested against the target provider's supported keyword list before deployment."
  4. In the domain-model spec, note that `oneOf`+`discriminator` and `if/then/else` are *domain-model* features enforced by the Validate node (post-LLM), *not* by the LLM's structured output — set expectations that the LLM may produce a value that passes the flattened schema but fails the full OpenAPI validation.
- **Severity:** MEDIUM (the spec is aware of the constraint but the default `warn_and_flatten` + the Hybrid default quietly degrade the validation the architecture promised)

### ISSUE-15: outdated_pattern — Rule engine choices (durable_rules, business-rules, pyknow) include essentially-unmaintained libraries; modern alternatives not considered
- **Type:** outdated_pattern
- **Section:** tool-ecosystem §5; extraction-layer §4.3; VISION.md AD 10
- **Problem:** AD 10 picks `durable_rules` as the default rule engine. The tool ecosystem §5 lists `durable_rules`, `business-rules`, `pyknow` as the three options. These are all old, low-activity Python libraries:
  - `durable_rules` (jruizgit/rules): last meaningful release years ago; the repo is not actively maintained.
  - `pyknow`: a pyknow/pyknow fork; minimal recent activity.
  - `business-rules`: very simple, no inference, unmaintained.

  For a 2026 framework, the rule-engine layer has better options: `python-rule-engine` (actively maintained, JSON-schema-based rules), `durable-rules` alternatives, or simply **Pydantic validators + `@model_validator`** (which the gateway spec §6.3 already adopts for schemas). The extraction-layer §4.3 even admits Pydantic as "Option C" with `root_validator` for cross-field rules — and Pydantic is already a framework dependency (via the gateway). Maintaining a *separate* rule-engine dependency for validation that Pydantic already handles is redundant.

  The deeper issue: the framework's validation needs (per-field type/regex/enum/range + cross-field) are modest. A full forward-chaining inference engine (durable_rules' `when/then`) is overkill for "loan_amount in [10000, 10000000] AND state in licensed_states." Industry 2026 guidance for LLM pipelines converges on Pydantic validators + Instructor's `llm_validator` for semantic checks.

- **Evidence:**
  - https://github.com/567-labs/instructor/blob/main/docs/concepts/validation.md: Pydantic `@field_validator` + `@model_validator` for cross-field rules; `llm_validator` for semantic checks — covers the spec's validation rule types (§4.2) without a separate rule engine.
  - https://ai-tldr.dev/learn/production-llmops/guardrails-reliability/llm-output-schema-validation/ (2026-06-12): *"Pydantic's `@field_validator` and `@model_validator` let you encode business rules inside the schema itself — `amount >= 0`, `end_date > start_date`, `status in ('pending','approved','rejected')`."*
  - https://github.com/guardrails-ai/guardrails: Guardrails AI Hub provides validators (PII, toxicity, regex, format) as a composable layer over Pydantic.
- **Proposed Fix:**
  1. Demote `durable_rules` from "default" (AD 10) to "optional for complex cross-field inference." Make **Pydantic validators** the default validation engine (the gateway already uses Pydantic).
  2. Replace `business-rules`/`pyknow` in §5 with **Guardrails AI** (for content validators beyond schema) and `python-rule-engine` (if a declarative JSON rule layer is needed).
  3. Update AD 10's rationale: "Pydantic validators handle 90% of validation (type/regex/enum/range/cross-field). A forward-chaining rule engine is opt-in for inference-heavy domains."
- **Severity:** MEDIUM (adopters following AD 10 install an unmaintained dependency for a job Pydantic already does)

### ISSUE-16: missing_alternative — "All LLM output is JSON" principle doesn't explicitly handle OpenAI refusals (a non-schema branch) or provider-native structured-output's `refusal` field
- **Type:** missing_alternative
- **Section:** llm-gateway §3; HLD §4.3 (AD 11)
- **Problem:** AD 11 + gateway §3 enforce "all LLM output is JSON matching `output_schema`." The validation pipeline (§3.1) handles: success → parse JSON → schema match → confidence check; failure → retry → errorNode. But this doesn't account for **refusals**: when using OpenAI Structured Outputs with `response_format`, the model can refuse (safety, or it genuinely cannot extract the data), and the API returns a `refusal` field *instead of* a schema-conformant response. A refusal is not malformed output — it's a different branch.

  Industry guidance (2026): *"Handle refusals as a real case. The model can refuse to produce the structure (safety, or it genuinely cannot extract the data). A refusal is not malformed output, it is a different branch. Check for it explicitly rather than letting it fall through your parsing code."*

  The gateway spec's retry-on-violation logic would treat a refusal as a schema violation and retry — but retrying a safety refusal is pointless (the model will refuse again) and may compound the issue. The spec needs an explicit `refusal` branch: detect it, do NOT retry, route to errorNode with `error_category: CONTENT_REFUSAL` and a `fallback_value` or `escalate_to_human` strategy.

  Separately, the spec's `temperature: 0` for extraction (AD 11) doesn't eliminate refusals — refusals are safety-policy-driven, not temperature-driven.

- **Evidence:**
  - https://folarin.dev/blog/structured-outputs-and-function-calling (2026-06-20): *"Handle refusals as a real case. The model can refuse to produce the structure (safety, or it genuinely cannot extract the data). A refusal is not malformed output, it is a different branch. Check for it explicitly rather than letting it fall through your parsing code."*
  - https://developers.openai.com/cookbook/examples/structured_outputs_intro: *"When using Structured Outputs with user-generated input, the model may occasionally refuse to fulfill the request for safety reasons. Since a refusal does not follow the schema… the API has a new field `refusal` to indicate when the model refused to answer."*
  - https://www.flowverify.co/blog/llm-function-calling-vs-structured-outputs (2026-05-07): Notes that structured-output guarantees "schema conformance is not data correctness" — refusals are a correctness edge case the schema can't catch.
- **Proposed Fix:**
  1. In gateway §3.1 validation pipeline, add a **refusal detection step** before JSON parse: if the provider response includes a `refusal` field (OpenAI) or equivalent safety signal, do NOT retry — route directly to errorNode with `error_category: CONTENT_REFUSAL`.
  2. Add `CONTENT_REFUSAL` to the error_category enum (§8).
  3. In the per-error-type retry policy (§3.3), add `ContentRefusal: { max_attempts: 0 }` (no retry — like auth failure).
  4. Document that refusals are more likely with `temperature: 0` + strict safety content; for regulated industries, a refusal on a `sensitive_data_read` node should default to `escalate_to_human`, not `fallback_value`.
- **Severity:** MEDIUM (a refusal treated as a schema violation wastes the retry budget and may loop; for regulated industries, mis-handling a safety refusal is an audit finding)

### ISSUE-17: weak_rationale — OpenAPI 3.1 chosen over JSON Schema Draft 2020-12 with the rationale "less mature tooling," but Draft 2020-12 is the canonical JSON Schema and is what LLM providers actually support
- **Type:** weak_rationale
- **Section:** domain-model §1.1 (AD 29)
- **Problem:** AD 29 picks OpenAPI 3.1 Schema Objects over JSON Schema Draft 2020-12, with the rationale: *"JSON Schema Draft 2020-12: Less mature tooling than OpenAPI 3.1 subset; no native Swagger UI integration."* The domain-model spec §1.1 repeats this.

  Two issues:
  1. **The rationale is backwards for the LLM-provider use case.** OpenAI/Anthropic Structured Outputs support a *subset* of JSON Schema that is closest to **Draft 2020-12**, not OpenAPI 3.1. OpenAPI 3.1's `Schema Object` is "a superset of JSON Schema Draft 2020-12" but adds OpenAPI-specific keywords (`discriminator`, `xml`, `externalDocs`, `example`) that LLM providers don't understand and the gateway §6.4 must strip. By choosing OpenAPI 3.1, the framework imports keywords that are useless for LLM output and must be filtered.
  2. **The "Swagger UI" benefit is thin for an LLM framework.** The domain model's primary consumers are: (a) the extraction/validation/transform code generators, (b) the LLM Gateway's `output_schema`, (c) the checkpoint persistence schema. None of these benefit from Swagger UI. Swagger UI is for REST API docs — the framework's downstream API contracts (QuoteRequest, QuoteResponse) are a side benefit, not the main use case.

  JSON Schema Draft 2020-12 is the *canonical* JSON Schema (OpenAPI 3.1 references it), has mature validators (`jsonschema` library, `python-jsonschema-tools`), and is what the LLM providers' structured-output docs are written against.

- **Evidence:**
  - https://ai-tldr.dev/learn/llm-apis/streaming-structured-outputs/json-mode-vs-structured-outputs/ (2026-06-12): OpenAI Structured Outputs accepts "a JSON Schema" — the docs are written against JSON Schema, not OpenAPI Schema Objects.
  - https://spec.openapis.org/oas/latest.html: OpenAPI 3.1 Schema Object is "a superset of the JSON Schema Specification Draft 2020-12" — meaning OpenAPI 3.1 *inherits* Draft 2020-12, not the reverse.
  - https://json-schema.org/: Draft 2020-12 is the current stable standard.
- **Proposed Fix:**
  1. Either: (a) keep OpenAPI 3.1 but fix the rationale — "OpenAPI 3.1 is chosen because the domain model also defines downstream REST API contracts (QuoteRequest, QuoteResponse) in the same file; the LLM-relevant subset is JSON Schema Draft 2020-12, which OpenAPI 3.1 is a superset of." Stop claiming Draft 2020-12 has "less mature tooling" (it's the canonical spec).
  2. Or: (b) adopt JSON Schema Draft 2020-12 as the domain-model format, and use OpenAPI 3.1 *only* for the downstream API contracts section. This aligns the LLM-facing schemas with what providers support natively.
  3. In §2.3, note that `discriminator` and `oneOf` are OpenAPI extensions that the gateway must strip for LLM providers anyway.
- **Severity:** MEDIUM (the choice is defensible but the rationale misrepresents the tooling landscape; adopters may be surprised that their "OpenAPI 3.1" schemas need stripping to work with LLMs)

---

## LOW

### ISSUE-18: weak_rationale — Context Hydration's "selective load" is asserted without a mechanism; risks becoming "load everything" in practice
- **Type:** weak_rationale
- **Section:** HLD §2.2 (Context Hydration)
- **Problem:** Context Hydration claims to "selectively refresh `AgentState` with data the current task actually needs" and "does NOT call all APIs blindly." The mechanism: `on_phase_entry` declares which sources to load per phase. But the spec doesn't define *how* the framework knows which fields a "task needs" — it relies on the workflow author declaring `always_load` and `on_phase_entry` lists. There's no static analysis ensuring the declared hydration covers the fields the phase's guards/executors will read. In practice, risk-adopters will over-hydrate (load everything) to avoid "field not loaded" errors, negating the selectivity benefit.
- **Evidence:** No direct source; this is a design-completeness observation. The pattern is analogous to RAG context selection: https://aivoid.dev/langextract-guide-2026/10-multi-pass-extraction/ notes that "schema for a later pass expects information that wasn't adequately extracted or prepared in an earlier pass" — the same dependency-tracking problem.
- **Proposed Fix:** Add a load-time check: for each phase, the framework scans the phase's guards/executors for field references and verifies each referenced field is covered by `always_load` or `on_phase_entry`. Missing coverage → startup warning. This makes the selectivity enforceable rather than aspirational.
- **Severity:** LOW (the design is sound; the gap is in enforcement)

### ISSUE-19: missing_alternative — LangGraph Functional API (@entrypoint/@task) not mentioned as an alternative to the Graph API for simpler workflows
- **Type:** missing_alternative
- **Section:** state-machine §1.1 (Implementation Approaches)
- **Problem:** The state-machine spec offers three options (A: YAML-Only, B: Code-First LangGraph, C: Hybrid) — all based on the **Graph API** (`StateGraph` with nodes/edges). LangGraph now has a **Functional API** (`@entrypoint` / `@task` decorators) for "minimal code changes to existing procedural code… standard control flow (if/else, loops, function calls)… rapid prototyping with less boilerplate." The Functional API shares the same runtime and can be combined with the Graph API. For the framework's "Option B: Code-First" and for simple linear workflows, the Functional API is lower-boilerplate than constructing a `StateGraph`. The Temporal-LangGraph integration supports both.
- **Evidence:**
  - https://docs.langchain.com/oss/javascript/langgraph/choosing-apis: *"Use the Functional API when you want: minimal code changes to existing procedural code… function-scoped state without explicit state management… linear workflows with simple branching logic."*
  - https://docs.temporal.io/develop/python/integrations/langgraph: *"The plugin supports both the LangGraph Graph API (`StateGraph` with nodes and edges) and the Functional API (`@entrypoint` / `@task` decorators)."*
- **Proposed Fix:** Add a note in §1.1 Option B: "For simple linear workflows, LangGraph's Functional API (`@entrypoint`/`@task`) is a lower-boilerplate alternative to `StateGraph` construction; it shares the same runtime and can be mixed with Graph-API sub-workflows. The framework's auto-generation targets the Graph API (Option C default); the Functional API is available for hand-written code-first workflows."
- **Severity:** LOW (expands developer ergonomics; doesn't change the default recommendation)

### ISSUE-20: weak_rationale — "English-only" deferral (intent spec §5.6) is reasonable for v1 but the framework gives no migration path; multilingual PII patterns (Chinese ID, EU GDPR) are already half-supported
- **Type:** weak_rationale
- **Section:** intent-classification §5.6; response-generation §8 (PII); domain-model §2.2
- **Problem:** Intent §5.6 defers cross-lingual support ("English is the only supported input language"). This is a reasonable v1 scope decision. But the PII rules (response-generation §8.2) already include a Chinese ID pattern (`\\b[0-9]{18}\\b` — Chinese ID number) and the domain-model examples use both US and Canadian patterns. So the framework *already* handles multilingual PII at the regex layer while claiming English-only NLU. This inconsistency means: a Chinese-language utterance would fail intent classification (English-only) but if it contained a Chinese ID number, the PII scrubber would catch it. There's no migration path from "English-only NLU + multilingual PII" to "multilingual NLU" — the intent spec doesn't reference multilingual embeddings or translation pipelines.
- **Evidence:**
  - https://privacyfilter.run/blog/openai-privacy-filter-vs-presidio (2026-04-28): OpenAI Privacy Filter supports "30+ languages (multilingual)" vs Presidio "English primary" — the multilingual PII gap is an active industry concern.
  - https://sovergate.com/blog/llm-pii-scrubbing-guide (2026-06-02): *"Multilingual support — detection and per-language models for regulated industries."*
- **Proposed Fix:** Add a "Multilingual Roadmap" subsection to intent §5.6: (a) v1: English-only NLU, multilingual PII regex (already supported); (b) v1.1: Presidio multilingual NER for PII (spaCy `zh_core_web_sm` etc.); (c) v2: cross-lingual intent classification via multilingual embeddings or translate-to-English pipeline. Note that the OpenAI Privacy Filter (30+ languages) is the natural upgrade for the PII layer. This makes the deferral a staged plan rather than a dead end.
- **Severity:** LOW (scope deferral is fine; the gap is the missing migration path and the existing inconsistency)

---

## Web Searches Performed

| # | Query | Key Finding |
|---|--------|-------------|
| 1 | LangGraph state machine SCXML Python 2026 vs XState statechart comparison | XState v5 (JSON, not SCXML) is the de-facto standard; SCXML's ECMAScript-in-XML model is rejected even by XState; `scxml` Rust crate explicitly disclaims full W3C compliance. LangGraph is a graph runtime, not a statechart formalism. |
| 2 | OpenAI structured outputs vs function calling JSON schema 2026 best practices | Structured Outputs (constrained decoding) guarantees schema at generation time; JSON mode is legacy; `additionalProperties: false` + all fields required; `if/then/not` unsupported; handle refusals as a separate branch. |
| 3 | LLM entity extraction multi-pass parallel pipeline 2026 best practices | Industry multi-pass = same schema, N independent passes, merge for RECALL (Google LangExtract, MuSEE). No source implements dual-scope parallel extraction. Industry is consolidating passes (Sifter: one combined prompt). |
| 4 | LLM model escalation fallback cheap to expensive model routing 2026 cost optimization | Cascading saves 45–85% at ~95% quality BUT conflating reliability-failover with cost-quality routing is "the most common architectural mistake." Cascade loses above ~30% escalation rate. Alert on escalation rate. |
| 5 | Model Context Protocol MCP 2026 maturity adoption alternatives function calling | MCP 2026-07-28 RC: stateless core, Streamable HTTP replaces HTTP+SSE, Tasks extension, formal deprecation policy. v1.x stable, v2 pre-release. 97M+ SDK downloads, 10k+ servers. |
| 6 | Google A2A protocol agent-to-agent communication 2026 vs MCP multi-agent orchestration | A2A donated to Linux Foundation (June 2025), v1.0 early 2026, 150+ orgs, 5-language SDKs. IBM ACP merged into A2A (Aug 2025). Agent Cards at `/.well-known/agent-card.json`. A2A complements MCP (agent↔agent vs agent↔tool). |
| 7 | LLM deterministic fallback regex hybrid rule-based NLU 2026 pattern enterprise | "Your AI Feature Should Lose to a Regex First" — deterministic baseline covers 60–70% at $0. PARSELY-DIP, MicroResolve: cascading regex→NLP→LLM. Hybrid symbolic-neural routing is the 2026 enterprise standard. |
| 8 | LLM token budget management API cost cap daily limit monitoring tools 2026 | Industry tools (LiteLLM, TokenLens, costfuse, Fairvisor, Archestra, LLM0) use staged warn→throttle→reject with per-user/per-team granularity, not global HTTP 500 kill switch. Auto-downgrade to cheaper model on limit. |
| 9 | Microsoft Presidio PII detection redaction 2026 alternatives LLM scrubbing | OpenAI Privacy Filter (April 2026, Apache-2.0, on-prem, 128k context) catches ~38% more contextual PII than Presidio 2.2. 3-layer pipeline: regex → Presidio NER → contextual LLM. Presidio alone insufficient for HIPAA/GDPR audit (needs auth/audit/access-control layers). |
| 10 | goal-driven AI agent workflow async goal verification LLM 2026 pattern | xAI `/goal` (June 2026): external persistent goal state (GOAL.md), deterministic verifier ("does not call an LLM"), survive context compaction. AgentFlow: 5-stage with deterministic verifier checking artifact evidence. KAIJU: intent-gated execution, LLM not observing gate decisions. |
| 11 | LangGraph subgraph reuse Send API parallel 2026 sub-workflow pattern | Per-thread subgraphs do NOT support parallel tool calls (checkpoint conflicts). Use `Send` fanout for parallel subgraphs. Per-invocation is the recommended mode. `recursion_limit` default 25. Subgraph state is private by default. |
| 12 | AI agent testing methodology 2026 LLM evaluation framework deterministic agent testing | AgentAssay: stochastic test semantics with SPRT for run-count. TDAD: mutation testing for prompts (97% hidden pass rate). Layer-Isolated Evaluation: per-layer slice gates localize regressions aggregate metrics miss. Structural testing with OpenTelemetry traces. |
| 13 | Instructor Guardrails AI Pydantic structured output LLM validation 2026 | Instructor = "most popular structured-output library in Python as of 2026," 3M+ monthly downloads, 15+ providers, auto-retry on Pydantic ValidationError. PydanticAI for agent runs. Guardrails AI for content validators. |
| 14 | Temporal durable execution workflow vs LangGraph 2026 long-running agent | "LangGraph for reasoning + Temporal for orchestration" is the 2026 recommended stack for side-effecting agents. Temporal adds event-history replay, activity idempotency, saga patterns. Official Temporal-LangGraph plugin exists. |
| 15 | LiteLLM LLM gateway proxy fallback model routing 2026 production | LiteLLM = unified gateway for 100+ LLMs, 8ms P95, fallbacks/context-window-fallbacks/cost-based-routing. Separates reliability (failover) from cost (routing). Industry standard for the gateway layer the spec builds custom. |

---

## Cross-Cutting Observations

1. **The "build custom" bias.** The framework builds custom versions of things mature OSS now provides: LLM Gateway (Instructor/LiteLLM), rule engine (Pydantic validators), PII (Presidio + OpenAI Privacy Filter), A2A protocol (official A2A v1.0 SDKs). For a "reference architecture" this is defensible (illustrative), but the specs should at minimum *reference* the OSS equivalents as the recommended production path. Several specs (tool-ecosystem) already do this for LangFlow/LangGraph/LangSmith — the inconsistency is that the *gateway* and *A2A* specs don't.

2. **The reliability/cost conflation (ISSUE-2) is architectural.** It surfaces in the LLM Gateway (escalation), the token budget (hard stop vs downgrade), and the async sub-workflow (callback vs durable). All three would be fixed by adopting the industry pattern: separate reliability layer (LiteLLM/Temporal) from cost/quality layer (cascade/Pydantic validation).

3. **Several "standards" adopted are pre-consolidation.** SCXML (pre-XState-v5), MCP HTTP+SSE (pre-2026-07-28), custom A2A (pre-A2A-v1.0 + ACP merger). The specs were written in a narrow window (June 2026) when these standards were mid-revision. A "last reviewed against <standard version>" date on each spec would make this maintainable.

4. **The strongest parts of the framework** (per-state extraction scope, E/V/T pipeline, phase-aware routing + return stack, errorNode unification, per-node LLM/deterministic switch, the three-tier testing methodology) are *not* challenged by these findings — they are either novel or well-aligned with industry. The issues concentrate in the infrastructure-layer specs (gateway, A2A, MCP, PII) where the framework reinvents what the 2026 OSS ecosystem now provides.
