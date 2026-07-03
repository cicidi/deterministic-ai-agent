# Debate Coordinator + Judge — Cross-Review, Resolutions & Rulings

**Date:** 2026-06-24
**Coordinator:** Agent 3 (Debate Coordinator)
**Judge:** Agent 4 (Judge)
**Inputs:** Agent 0 (50 issues), Agent 1 (20 issues), Agent 2 (66 issues) = **136 total findings**

---

## Step 1: Overlap Analysis

### Unanimous Agreements (found independently by 2+ agents)

These issues are accepted unanimously and modifications should be applied. No debate needed.

| # | Issue | Agent 0 | Agent 1 | Agent 2 | Action |
|---|-------|---------|---------|---------|--------|
| U1 | Chinese `举一反三` in English-only specs | C-2 | — | H-11 | ACCEPT (severity: CRITICAL) |
| U2 | intent-classification keyword fallback self-contradiction | C-3 | H-11 | C-1 | CONTESTED → Debate-1 |
| U3 | PII rules circular ownership (response-gen ↔ domain-model) | C-1 | — | M-28 | CONTESTED → Debate-2 |
| U4 | Two incompatible IntentDef schemas (missing `complex`) | H-4 | — | C-2 | ACCEPT (severity: CRITICAL) |
| U5 | Widget-templates insurance/mortgage domain mix | H-6 | — | H-6 | ACCEPT (severity: HIGH) |
| U6 | llm-gateway §4.7/4.8 duplicate sections + orphaned fragment | H-5 | — | H-13 | ACCEPT (severity: HIGH) |
| U7 | Mortgage-lead `submit_lead` marked non-complex | H-8 | — | H-12 | ACCEPT (severity: HIGH) |
| U8 | Home-insurance example outdated IntentDef schema | H-9 | — | (rel. H-12) | ACCEPT (severity: HIGH) |
| U9 | Intent naming drift: `small_talk`/`greeting`/`greet` vs canonical | H-10 | — | H-19 | ACCEPT (severity: HIGH) |
| U10 | Testing methodology non-canonical intent names | H-11 | — | (H-19) | ACCEPT (merge with U9) |
| U11 | MCP `get_status` enum missing `archived` | H-12 | — | M-34 | ACCEPT (severity: HIGH) |
| U12 | Routing append-only vs configurable reducers contradiction | H-13 | — | C-3 | CONTESTED → Debate-3 |
| U13 | extraction-layer §2.6→§2.5 broken cross-reference | H-15 | — | M-25 | ACCEPT (severity: HIGH) |
| U14 | HLD document tree stale (missing 4 specs + home-insurance) | H-16 | — | L-51 | ACCEPT (severity: HIGH) |
| U15 | llm-gateway duplicate `floor_area` key | M-24 | — | H-9 | ACCEPT (severity: HIGH) |
| U16 | observability duplicate `llm_retry_total` metric | M-27 | — | H-10 | ACCEPT (severity: HIGH) |
| U17 | environment-config duplicate workflow + "legacy" label | M-25,26 | — | M-39 | ACCEPT (severity: MEDIUM) |
| U18 | cicd References section split | M-28 | — | M-36 | ACCEPT (severity: MEDIUM) |
| U19 | rate-limiting "Claims operations" leftover | M-29 | — | M-31 | ACCEPT (severity: MEDIUM) |
| U20 | Home-insurance e2e numeric inconsistencies | M-30 | — | H-17 | ACCEPT (severity: HIGH) |
| U21 | Domain-model undefined `QuoteDetails` $ref | L-50 | — | M-24 | ACCEPT (severity: MEDIUM) |
| U22 | State-machine duplicate return line | M-19 | — | M-22 | ACCEPT (severity: MEDIUM) |
| U23 | Domain-model changelog malformed cell | M-21 | — | L-54 | ACCEPT (severity: MEDIUM) |
| U24 | Model name drift (gpt-4.1, claude-opus) | M-36 | — | M-40 | ACCEPT (severity: MEDIUM) |
| U25 | three-tier-testing §7 checklist failures | H-14 | — | — | ACCEPT (severity: HIGH, Agent 0 only but clear) |
| U26 | rag-interface missing Open Questions + comparison matrix | M-33 | — | — | ACCEPT (severity: MEDIUM) |
| U27 | agent-types missing Open Questions | M-34 | — | — | ACCEPT (severity: MEDIUM) |
| U28 | Home-insurance stale year 2024 | L-41 | — | (H-17) | ACCEPT (severity: LOW) |
| U29 | Response-gen goal example data errors | M-22,23 | — | L-57,58 | ACCEPT (severity: MEDIUM) |
| U30 | tool-ecosystem §7.6 heading missing | H-7 | — | — | ACCEPT (severity: HIGH) |
| U31 | HLD personal filesystem path + name inconsistency | H-17 | — | — | ACCEPT (severity: HIGH) |
| U32 | Mortgage-lead IntentDef "Type" column non-canonical | L-43 | — | — | ACCEPT (severity: LOW) |
| U33 | submit_mortgage_lead vs submit_lead naming drift | M-38 | — | — | ACCEPT (severity: MEDIUM) |
| U34 | Mortgage-lead chitchat→errorNode contradicts lifecycle | M-39 | — | — | ACCEPT (severity: MEDIUM) |
| U35 | Auth §2.5 commits real production hostname | L-44 | — | — | ACCEPT (severity: LOW→upgrade HIGH) |
| U36 | Agent-types malformed docstring | M-31 | — | — | ACCEPT (severity: MEDIUM) |
| U37 | Agent-types changelog order | M-32 | — | L-60 | ACCEPT (severity: LOW) |
| U38 | extraction Options B/C undocumented | M-18 | — | H-15 | ACCEPT (severity: HIGH) |
| U39 | Auth §2.5 Spring/Java concepts in Python framework | — | — | M-44 | ACCEPT (severity: MEDIUM) |
| U40 | Auth `verification_order` list vs enum inconsistency | — | — | M-43 | ACCEPT (severity: MEDIUM) |
| U41 | Auth §5 "RBAC deferred" contradicts routing/tool-ecosystem | — | — | M-45 | ACCEPT (severity: MEDIUM) |
| U42 | errorNode strategy short names vs canonical enum | — | — | H-16 | ACCEPT (severity: HIGH) |
| U43 | `check_rates` routed 4 mutually-exclusive ways | — | — | C-4 | ACCEPT (severity: CRITICAL) |
| U44 | `phase_stack` missing from canonical AgentState | — | — | H-5 | ACCEPT (severity: HIGH) |
| U45 | `transitions` library contradicts LangGraph-only runtime | — | — | H-7 | ACCEPT (severity: HIGH) |
| U46 | Boolean `False` treated as empty breaks confirm/decline | — | — | H-8 | ACCEPT (severity: HIGH) |
| U47 | Two example workflow.yaml incompatible schemas | — | — | H-14 | ACCEPT (severity: HIGH) |
| U48 | Home-insurance uses custom error states not errorNode | — | — | H-20 | ACCEPT (severity: HIGH) |
| U49 | `general_inquiry` not a system intent but used in evals | — | — | H-18 | ACCEPT (severity: HIGH) |
| U50 | Intent-classification §3.3 single-intent prompt vs §4.2 multi-intent contract | — | — | M-50 | ACCEPT (severity: MEDIUM) |
| U51 | Domain-model §11.2 reverts to custom FieldDef syntax | — | — | M-23 | ACCEPT (severity: MEDIUM) |
| U52 | Conversation-lifecycle §2.1 paused→timeout vs §2.2 paused→archived | — | — | M-29 | ACCEPT (severity: MEDIUM) |
| U53 | Conversation-lifecycle metrics don't match observability taxonomy | — | — | M-30 | ACCEPT (severity: MEDIUM) |
| U54 | Rate-limiting tier names differ (free/pro vs default/premium) | — | — | M-32 | ACCEPT (severity: MEDIUM) |
| U55 | MCP Claude Desktop config mixes stdio + SSE | — | — | M-33 | ACCEPT (severity: MEDIUM) |
| U56 | MCP §1.1 claims streaming but send_message non-streaming | — | — | M-35 | ACCEPT (severity: MEDIUM) |
| U57 | CI/CD error-rate thresholds inconsistent (5% vs 10%) | — | — | M-37 | ACCEPT (severity: MEDIUM) |
| U58 | A2A response naming inconsistency (AgentResult vs a2a_response) | — | — | M-38 | ACCEPT (severity: MEDIUM) |
| U59 | Environment-config e2e mock+real contradiction | — | — | M-41 | ACCEPT (severity: MEDIUM) |
| U60 | Environment-config Option B naming inconsistency | — | — | M-42 | ACCEPT (severity: MEDIUM) |
| U61 | Tool-ecosystem casbin action `transition` not in model | — | — | M-46 | ACCEPT (severity: MEDIUM) |
| U62 | Observability HighErrorRate two different formulas | — | — | M-47 | ACCEPT (severity: MEDIUM) |
| U63 | LLM-gateway audit ignores +1 LLM retry rule | — | — | M-48 | ACCEPT (severity: MEDIUM) |
| U64 | LLM-gateway "min 2 providers" violated by dev/e2e defaults | — | — | M-49 | ACCEPT (severity: MEDIUM) |
| U65 | State-machine SCXML mapping wrong open-question number | — | — | M-21 | ACCEPT (severity: MEDIUM) |
| U66 | Response-gen gap threshold two config keys | — | — | M-27 | ACCEPT (severity: MEDIUM) |
| U67 | Extraction type naming inconsistent (int/float/enum vs integer/number) | — | — | M-26 | ACCEPT (severity: MEDIUM) |
| U68 | Domain-model §5.3 stale multi-intent description | M-37 | — | — | ACCEPT (severity: MEDIUM) |
| U69 | A2A references "Google A2A Protocol" without context | L-49 | H-6 | — | CONTESTED → Debate-4 |
| U70 | HLD duplicate A.5 numbering | — | — | L-52 | ACCEPT (severity: LOW) |
| U71 | HLD §5 missing home-insurance examples | — | — | L-53 | ACCEPT (severity: LOW) |
| U72 | State-machine "Current Approach" label misleading | — | — | L-55 | ACCEPT (severity: LOW) |
| U73 | State-machine mixes home-insurance + mortgage examples | — | — | L-56 | ACCEPT (severity: LOW) |
| U74 | Response-gen Chinese-ID PII pattern in English-only framework | — | — | L-59 | ACCEPT (severity: LOW) |
| U75 | RAG-interface RAGResult before definition + consumer ambiguity | — | — | L-61 | ACCEPT (severity: LOW) |
| U76 | Widget-templates `loan_amount_amount` doubled word | — | — | L-62 | ACCEPT (severity: LOW) |
| U77 | LLM-gateway §5.4 with no §5.1-5.3 + confidence minimum:0 | — | — | L-63 | ACCEPT (severity: LOW) |
| U78 | A2A error.category missing `unrecoverable_error` | — | — | L-64 | ACCEPT (severity: LOW) |
| U79 | Extraction guardrail conflates AgentState fields with collectedFields keys | — | — | L-65 | ACCEPT (severity: LOW) |
| U80 | Three-tier-testing hardcoded mfangdai DB names + undefined "payment gate" | — | — | L-66 | ACCEPT (severity: LOW) |
| U81 | Conversation-lifecycle §1.2 message history tension | L-45 | — | — | ACCEPT (severity: LOW) |
| U82 | Example state name drift (distribute_lead/assign_lead/submit_lead) | L-46 | — | — | ACCEPT (severity: LOW) |
| U83 | CICD hetzner-jenkins DB cleanup inconsistency | L-47 | — | — | ACCEPT (severity: LOW) |
| U84 | Mortgage-lead README "18 intents" claim misleading | L-48 | — | — | ACCEPT (severity: LOW) |
| U85 | Widget-templates welcome message awkward phrasing | L-42 | — | — | ACCEPT (severity: LOW) |
| U86 | Routing §6.7 ASCII misalignment | L-40 | — | — | ACCEPT (severity: LOW) |

### Agent 1 Unique Findings (web-evidence based — no cross-agent overlap)

These need Judge ruling since no other agent independently validated them. However, Agent 1 provides URL evidence.

| # | Issue | Agent 1 | Type | Judge Action |
|---|-------|---------|------|--------------|
| A1-1 | SCXML as ceremonial compliance theater | C-1 | weak_rationale | CONTESTED → Debate-5 |
| A1-2 | Progressive model escalation conflates reliability + cost | C-2 | wrong_approach | CONTESTED → Debate-6 |
| A1-3 | MCP obsolete HTTP+SSE transport | C-3 | outdated_pattern | ACCEPT (URL evidence, clear) |
| A1-4 | LLM Gateway ignores Instructor/PydanticAI | C-4 | missing_alternative | CONTESTED → Debate-7 |
| A1-5 | Dual-scope parallel extraction not industry standard | H-5 | wrong_approach | CONTESTED → Debate-8 |
| A1-6 | A2A spec predates v1.0 + ACP merger | H-6 | outdated_pattern | Merge with U69 → Debate-4 |
| A1-7 | Missing Temporal for durable execution | H-7 | missing_alternative | CONTESTED → Debate-9 |
| A1-8 | Token budget HTTP 500 naive | H-8 | wrong_approach | ACCEPT (URL evidence, clear) |
| A1-9 | Goal-driven 1s timeout unrealistic | H-9 | weak_rationale | ACCEPT (URL evidence, clear) |
| A1-10 | PII missing OpenAI Privacy Filter | H-10 | missing_alternative | ACCEPT (URL evidence, clear) |
| A1-11 | Testing methodology lacks 2026 SOTA | M-12 | missing_alternative | ACCEPT (URL evidence, valuable) |
| A1-12 | LangGraph subgraph parallel warning | M-13 | wrong_approach | ACCEPT (URL evidence, clear) |
| A1-13 | OpenAPI 3.1 vs JSON Schema rationale backwards | M-17 | weak_rationale | CONTESTED → Debate-10 |
| A1-14 | Rule engines unmaintained; Pydantic suffices | M-15 | outdated_pattern | ACCEPT (URL evidence, clear) |
| A1-15 | LLM refusal handling missing | M-16 | missing_alternative | ACCEPT (URL evidence, clear) |
| A1-16 | LangGraph Functional API not mentioned | L-19 | missing_alternative | ACCEPT (URL evidence, low-impact) |
| A1-17 | Context hydration mechanism weak | L-18 | weak_rationale | ACCEPT (low-impact) |
| A1-18 | Multilingual roadmap missing | L-20 | weak_rationale | ACCEPT (low-impact) |
| A1-19 | Structured Outputs schema constraints vs OpenAPI 3.1 | M-14 | missing_alternative | ACCEPT (URL evidence, clear) |

---

## Step 2: Debates on Contested Issues

### Debate-1: intent-classification keyword fallback resolution

**Positions:**
- **Agent 0 (ISSUE-3):** Keep Option B, soften the absolute "removed" language. "If Option B is intentionally retained as a deployment option, then the v0.6.0 changelog entry and §3.4's 'There is no keyword fallback' must be softened."
- **Agent 1 (ISSUE-11):** Restore keyword as **Layer 0** (deterministic pre-filter cascade). "Layer 0 (keyword/regex, confidence ≥ 0.95 → return, $0) → Layer 1 (LLM) → `unrecognized_intent`." Cites 2026 industry consensus that deterministic-first cascade is the biggest LLM cost lever. Notes the spec conflated *cascading* (deterministic-first) with *fallback* (LLM-first + deterministic salvage).
- **Agent 2 (ISSUE-1):** Either delete Option B entirely OR restore it with clear "Decision: NOT recommended — removed in 0.6.0; retained only as a documented alternative" note. Points out the `source` enum can't represent keyword results (`"keyword"` was removed).

**Round 1 — Case & Response:**

*Agent 1 states:* The framework's own principle (VISION §6.2: "Deterministic fallback for every extractable field") and AD 3 ("LLM excels at understanding; execution must be auditable") require deterministic handling. The extraction layer kept deterministic fallback (`x-fallback`); intent classification dropped it inconsistently. Every "hello"/"yes"/"help" now costs an LLM call (~500ms, $0.001+) when keyword match handles it in <5ms at $0. Industry tools (PARSELY-DIP, MicroResolve) solve keyword collision with cascading layers. The spec's own Option B matrix documents this correctly — then the changelog removes it.

*Agent 0 responds:* Agree the contradiction must be resolved. The v0.6.0 decision to remove keyword fallback was likely motivated by keyword collision across 17+ intents. But removing it entirely contradicts the framework's deterministic-fallback principle. Softening the absolute language and keeping Option B as a documented alternative is the minimal fix.

*Agent 2 responds:* The `source` enum issue is real — if Option B is kept, `"keyword"` must be restored to the enum. Either commit to keeping it (restore enum + §3.4) or delete it (remove Option B + matrix). Half-measures create confusion.

**Round 2 — Rebuttal with Evidence:**

*Agent 1 rebuts:* Agent 0's "softening" approach doesn't fix the core issue — it keeps a contradiction in the spec. Agent 2's "delete entirely" approach removes a valid cost-optimization path. The correct resolution is **cascade** (deterministic-first), not **fallback** (LLM-first + deterministic salvage). The spec's v0.6.0 changelog conflated these two concepts. The 17-system-intent keyword lists already exist (§2.1) — they're currently "metadata only." Making them Layer 0 is minimal code change. Web evidence: 60-70% of inputs can be handled by regex/keyword at $0 (tianpan.co, PARSELY-DIP, MicroResolve, genaipatterns.dev).

*Agent 0 concedes:* Agent 1's cascade approach is more principled and aligns with both the framework's deterministic-fallback principle and 2026 industry practice. I withdraw my "soften the language" proposal in favor of the cascade approach.

*Agent 2 concedes:* The cascade approach is the most complete resolution. I withdraw "delete entirely" and support restoring keyword as Layer 0 with the `source` enum fix.

**Round 3 — Final Positions:**

*All three agents agree:* Restore keyword/regex as **Layer 0** (deterministic cascade pre-filter), restore `"keyword"` to the `source` enum, update §3.4 to describe the cascade flow, and update the changelog to acknowledge the v0.6.0 removal was an over-correction.

---

### Debate-2: PII rules canonical ownership

**Positions:**
- **Agent 0 (ISSUE-1):** response-generation §8 owns PII *processing* (scrubbing pipeline), domain-model owns PII *declaration* (`x-pii` extension in entity schemas).
- **Agent 2 (ISSUE-28):** response-generation §8.2 should be the authoritative home for both declaration and processing; domain-model cross-references it.

**Round 1:**
*Agent 0:* Separating declaration (domain-model, where entities live) from processing (response-generation, where the scrubbing pipeline runs) follows the framework's "separate WHAT from HOW" principle (VISION §3.2.3). The domain model already uses `x-` extensions (`x-state-bindings`, `x-fallback`); adding `x-pii` is consistent.

*Agent 2:* The `pii_rules` YAML already lives in response-generation §8.2. Making domain-model own declarations adds a new extension (`x-pii`) that doesn't exist yet. Simpler to make response-gen the single owner and have domain-model point to it.

**Round 2:**
*Agent 0 rebuts:* Agent 1 (ISSUE-10) found that the current regex-only `pii_rules` in response-gen are insufficient — PII needs contextual NER (Presidio) and contextual LLM (OpenAI Privacy Filter). The domain model is where entity fields are defined; PII declarations belong with the field definitions (a `phone` field in `Borrower` should declare `x-pii: { strategy: partial_mask }` next to its type). The processing pipeline (which engine to use, 3-layer architecture) belongs in response-gen.

*Agent 2 concedes:* The separation is cleaner. Domain-model owns `x-pii` declarations on entity fields; response-gen owns the 3-layer scrubbing pipeline that consumes them. Both specs cross-reference each other.

**Round 3:**
*Agreement:* Agent 0's split ownership model accepted. Domain-model adds `x-pii` extension; response-gen §8 owns the processing pipeline.

---

### Debate-3: Routing append-only vs configurable reducers

**Positions:**
- **Agent 0 (ISSUE-13):** Audit fields (`messages`, `audit_log`, `llm_calls`) are append-only and not configurable. Business fields (`collectedFields`, `response`, `goal_check_result`) are configurable via `state_reducers`.
- **Agent 2 (ISSUE-3):** Keep configurable reducers (the useful design). Append is the **default**; `last_write_wins`/`conflict_detect` are opt-in per field. Remove "not configurable"/"single strategy: append" language.

**Round 1:**
*Agent 0:* The spec's §1.2 deep-merge and conflict-wrap behavior is already not pure append. Audit fields genuinely need append-only (compliance). Business fields need flexibility. Splitting the policy by field category resolves the contradiction.

*Agent 2:* Agreed. The absolute "not configurable" claim is wrong. Both audit and business fields should be in the schema; audit fields default to append and are locked; business fields default to append but can override.

**Round 3:**
*Agreement:* Both proposals are compatible. Audit fields = append-only, locked. Business fields = configurable, append default. Remove the absolute "not configurable" language. Update conversation-lifecycle §4.4 to match.

---

### Debate-4: A2A protocol — custom dialect vs official A2A v1.0

**Positions:**
- **Agent 0 (ISSUE-49):** The A2A spec references "Google A2A Protocol" without context. Minor issue (LOW).
- **Agent 1 (ISSUE-6):** The A2A spec predates A2A v1.0 + IBM ACP merger. Custom Agent Registry should be replaced with Agent Cards at `/.well-known/agent-card.json`. Custom `a2a_request`/`a2a_response` envelope should be replaced with official `message/send` + Task lifecycle. 150+ organizations on official spec, 22k GitHub stars, 5 official SDKs.

**Round 1:**
*Agent 1:* The spec (dated 2026-06-17) references "Google A2A Protocol" as "conceptual reference" but invents a custom registry and message format. A2A was donated to Linux Foundation (June 2025), reached v1.0 (early 2026), and merged with IBM ACP (August 2025). The standard discovery is Agent Cards at well-known URLs, not a centralized registry. An adopter following this spec builds a non-interoperable dialect.

*Agent 0:* I flagged the missing context as LOW. Agent 1's finding elevates this significantly — it's not just a missing reference, it's a foundation-on-outdated-standard problem. I upgrade my severity assessment to HIGH.

**Round 3:**
*Agreement:* Agent 1's evidence is authoritative (Linux Foundation, 150+ orgs, official SDKs). The spec should adopt A2A v1.0 patterns (Agent Cards, official task lifecycle) and reference the official SDKs rather than defining a custom wire format. The framework's value-add remains the YAML sub-workflow→A2A mapping.

---

### Debate-5: SCXML as semantic standard

**Positions:**
- **Agent 1 (ISSUE-1):** SCXML is ceremonial compliance theater. Industry moved to XState v5 JSON. The spec itself admits "no XML file is generated." SCXML's executable content is explicitly rejected in the mapping table. The compliance benefit is asserted, not demonstrated — no auditor is named.

**Round 1 (single-agent debate — Agent 1 vs the spec's own rationale):**
*Agent 1:* The spec's SCXML↔YAML mapping table quietly admits the mismatch: `<script>` → "not supported", `<foreach>` → "not supported", `<if>/<elseif>/<else>` → "Python guards". SCXML's executable content — the part that makes it a *semantic* standard — is explicitly rejected. What remains is just statechart vocabulary (states, transitions, guards, entry/exit) shared by every state machine library. The Rust `scxml` crate explicitly disclaims full W3C compliance. XState v5 deliberately dropped SCXML conformance. The "compliance & audit" benefit is unfalsifiable — no specific regulator or control is named.

*Counter-argument (from the spec's own AD 28 rationale):* SCXML provides a W3C standard reference for regulated industries that need to justify state machine correctness. YAML is a YAML expression of SCXML semantics.

*Agent 1 rebuts:* "Justify correctness to a regulator" requires either (a) a formal verifier that consumes SCXML, or (b) a named regulator that requires SCXML. Neither exists. The YAML→SCXML mapping is manual and unverified. If a regulator asks "prove your state machine is correct," pointing to a W3C standard you don't actually produce or validate against is not proof.

**Judge ruling needed.** See Step 3.

---

### Debate-6: Progressive model escalation — reliability vs cost conflation

**Positions:**
- **Agent 1 (ISSUE-2):** The gateway's single escalation cascade conflates reliability failover (provider outage) with cost-quality routing (schema violation). Industry calls this "the most common architectural mistake." Should split into two layers.

**Round 1:**
*Agent 1:* The default `trigger_on` includes both `provider_error` AND `schema_violation`. A rate-limit on gpt-4o-mini escalates to gpt-4o for quality reasons that don't exist, paying 2x. A schema violation escalates to gpt-4o which may be a different provider's cheap model during an outage. The cost shape is fundamentally different: reliability wants fast escalation to any healthy model; cost-quality wants slow escalation to a more capable model. The sticky tier (§4.9) is a band-aid for the cost waste this conflation creates. Evidence: jatinbansal.com, truefoundry.com, genaipatterns.dev, alexcloudstar.com.

*Counter-argument (from the spec):* The gateway's progressive escalation (AD 31) is designed as a safety net, not a feature. The default is always the cheapest model. Escalation only fires on failure.

*Agent 1 rebuts:* "Failure" is overloaded. A provider timeout is not the same failure as a schema violation. The spec treats them identically in one cascade. The industry evidence is unanimous: separate the two. This is the framework's central cost-control mechanism; getting it wrong silently inflates every adopter's LLM bill.

**Judge ruling needed.** See Step 3.

---

### Debate-7: LLM Gateway — custom infrastructure vs Instructor/PydanticAI

**Positions:**
- **Agent 1 (ISSUE-4):** The gateway reimplements what Instructor does (3M+ monthly downloads, 15+ providers, auto-retry on Pydantic ValidationError). Should reframe gateway as thin policy layer over Instructor.

**Round 1:**
*Agent 1:* The gateway's custom `LLMCall`/`LLMResult`, custom validation pipeline, custom retry-on-violation, custom type coercion, and four "Gateway Validation Strategies" are a from-scratch reimplementation of Instructor. The spec's "Option D: Validator-Enhanced Post-Process" describes the Instructor/Guardrails pattern almost exactly but lists it as fourth option. Building custom means every adopter learns a framework-specific API instead of the widely-documented Instructor API.

*Counter-argument (from the spec):* The framework defines interfaces, not implementations. The gateway spec defines what the gateway must do; the implementation can use Instructor under the hood.

*Agent 1 rebuts:* The spec never mentions Instructor as an option. The "2+ options per interface" requirement (VISION §7) means the spec should at minimum list Instructor as a recommended implementation option. The tool-ecosystem spec already integrates LangFlow/LangGraph/LangSmith — omitting Instructor from the gateway is inconsistent. This is a "missing alternative" not a "wrong approach" — the spec should reference Instructor as the industry standard.

**Judge ruling needed.** See Step 3.

---

### Debate-8: Dual-scope parallel extraction — novel pattern vs industry standard

**Positions:**
- **Agent 1 (ISSUE-5):** The two-LLM parallel extraction (narrow scope + full schema) is not an industry pattern. Industry multi-pass is for recall (same schema, N passes), not scope division. Doubles token cost on every turn. Reintroduces cross-field confusion for LLM 2 (the exact problem AD 30 claims to solve).

**Round 1:**
*Agent 1:* Every 2026 source (Google LangExtract, Chaos Cypher, Neo4j Agent Memory, MuSEE, Sifter) uses multi-pass over the SAME schema for recall. No source implements dual-scope parallel extraction. LLM 2 sees ALL fields across ALL entities — the anti-pattern the spec itself warns about (§7.3: "Confuse field boundaries"). The spec's own reference implementation uses single-pass hybrid, not dual-LLM parallel. The cost/accuracy trade-off is asserted, not measured.

*Counter-argument (from AD 30):* Multi-pass per-state extraction scope. Pass 1: two parallel LLMs (narrow scope + broad scope). Pass 2: merge, cross-validate, user confirmation. Rationale: catches fields user mentioned out of order.

*Agent 1 rebuts:* The rationale ("fields user mentioned out of order") is rare and doesn't justify 2x cost on EVERY turn. The conversation context window (last 3+3 messages) already lets the LLM see prior turns. A broad-scope scan should only fire when narrow-scope extraction is incomplete (missing required fields), not on every turn.

**Judge ruling needed.** See Step 3.

---

### Debate-9: Missing Temporal for durable execution

**Positions:**
- **Agent 1 (ISSUE-7):** LangGraph alone is insufficient for side-effecting workflows (lead distribution, payment collection). The framework's async sub-workflow + dangerous_operation_write tools need Temporal for durable execution. Industry: "LangGraph for reasoning + Temporal for orchestration."

**Round 1:**
*Agent 1:* LangGraph's checkpointer provides durability within a thread, but not event-history-backed replay, activity-level idempotency, multi-day pause/resume, or saga-pattern compensating transactions. The framework's async sub-workflow (§5.4: "parent fires sub-workflow and continues; result delivered via callback") is exactly what Temporal handles natively. For a regulated-industry framework where "distribute lead" is a dangerous_operation_write requiring audit trail and idempotent retries, the absence of Temporal is a structural gap.

*Counter-argument (from AD 1):* Python + LangGraph. LangGraph provides state graph, checkpoint, streaming.

*Agent 1 rebuts:* AD 1 doesn't say "LangGraph ONLY." It says "Python + LangGraph." Temporal is Python-native. LangChain's own comparison page lists "LangGraph + Temporal" as the recommended stack for side-effecting workflows. The official Temporal-LangGraph plugin exists (2026). This is not "drop LangGraph" — it's "add Temporal as an optional layer for side-effecting workflows."

**Judge ruling needed.** See Step 3.

---

### Debate-10: OpenAPI 3.1 vs JSON Schema Draft 2020-12 rationale

**Positions:**
- **Agent 1 (ISSUE-17):** The rationale "JSON Schema Draft 2020-12 has less mature tooling" is backwards. Draft 2020-12 is the canonical JSON Schema. OpenAPI 3.1 is a superset that adds keywords LLM providers don't understand. The LLM-relevant subset is Draft 2020-12.

**Round 1:**
*Agent 1:* OpenAI/Anthropic Structured Outputs support a subset of JSON Schema closest to Draft 2020-12, not OpenAPI 3.1. OpenAPI 3.1's `discriminator`, `xml`, `externalDocs` are useless for LLM output and must be stripped (gateway §6.4). The "Swagger UI" benefit is thin — the domain model's primary consumers are extraction code, LLM Gateway, and checkpoint persistence, none of which benefit from Swagger UI.

*Counter-argument (from AD 29):* OpenAPI 3.1 provides industry-standard tooling (validators, code generators, Swagger UI). Downstream API contracts (QuoteRequest, QuoteResponse) defined in same format.

*Agent 1 rebuts:* The downstream API contracts are a side benefit, not the main use case. The choice is defensible (OpenAPI 3.1 for API contracts + LLM subset) but the rationale should be fixed — stop claiming Draft 2020-12 has "less mature tooling" when it's the canonical spec.

**Judge ruling needed.** See Step 3.

---

## Step 3: Judge Rulings

### JUDGE RULING-1: intent-classification keyword fallback (Debate-1)

**Ruling: ACCEPT Agent 1's cascade approach (unanimous after debate)**

The court rules that keyword/regex should be restored as **Layer 0** (deterministic cascade pre-filter), not as "fallback." The v0.6.0 removal was an over-correction that:
1. Contradicts VISION §6.2 ("Deterministic fallback for every extractable field") and AD 3
2. Contradicts 2026 industry consensus (60-70% of inputs handleable at $0)
3. Conflated *cascading* (deterministic-first) with *fallback* (LLM-first + deterministic salvage)

**Required modifications:**
- Restore `"keyword"` to `ClassifiedIntent.source` enum
- Rewrite §3.4 to describe the cascade: Layer 0 (keyword/regex, confidence ≥ 0.95 → return) → Layer 1 (LLM) → `unrecognized_intent`
- Update changelog: acknowledge v0.6.0 removal was an over-correction; v0.7.0 restores keyword as Layer 0 cascade
- Keep Option B in §2.4 as the documented cascade strategy (now the default)
- Add Agent 1's web evidence as rationale references

### JUDGE RULING-2: PII rules ownership (Debate-2)

**Ruling: ACCEPT Agent 0's split ownership model (agreed after debate)**

Domain-model owns PII *declaration* (`x-pii` extension on entity fields); response-generation §8 owns PII *processing* (3-layer scrubbing pipeline). This follows VISION §3.2.3 "Separate WHAT from HOW."

**Required modifications:**
- Domain-model §2/§3: document `x-pii` extension (e.g., `x-pii: { fields: [phone, email], strategy: partial_mask }`)
- Response-gen §8.1/§8.2: change heading to "PII Processing Pipeline (consumes `x-pii` declarations from Domain Model)"
- Domain-model §10.3: remove "authoritative PII rules definition is in Response Generation §8"; replace with "PII rule declarations: see Domain Model §3 (`x-pii`). Processing: see Response Generation §8."
- Add Agent 1's 3-layer pipeline recommendation (regex → Presidio NER → contextual LLM) to response-gen §8

### JUDGE RULING-3: Routing append-only model (Debate-3)

**Ruling: COMPROMISE — both proposals are compatible (agreed after debate)**

Audit fields (`messages`, `audit_log`, `llm_calls`) = append-only, framework-locked, not configurable. Business fields (`collectedFields`, `response`, `goal_check_result`) = configurable via `state_reducers`, append is default.

**Required modifications:**
- Rewrite routing §1.2/§1.3 to remove "not configurable"/"single strategy: append" absolute language
- Add explicit field-category table: which fields are locked append-only vs configurable
- Update conversation-lifecycle §4.4 to match

### JUDGE RULING-4: A2A protocol (Debate-4)

**Ruling: ACCEPT Agent 1's recommendation (Agent 0 upgraded severity)**

The spec must align with A2A v1.0 (Linux Foundation, 150+ orgs). Custom dialect is non-interoperable.

**Required modifications:**
- Replace custom Agent Registry with Agent Card discovery at `/.well-known/agent-card.json`
- Replace custom `a2a_request`/`a2a_response` envelope with A2A v1.0 `message/send` + Task lifecycle
- Reference official Python/Go SDKs
- Note A2A complements MCP (agent↔agent vs agent↔tool)
- Add A2A v1.0 + IBM ACP merger to References

### JUDGE RULING-5: SCXML as semantic standard (Debate-5)

**Ruling: COMPROMISE**

The court finds that Agent 1's evidence is persuasive: SCXML's executable content is explicitly rejected in the mapping table, no SCXML file is produced or validated, and no specific regulator requiring SCXML is named. The "compliance & audit" benefit is asserted but unfalsifiable. However, the statechart *vocabulary* (states, transitions, guards, entry/exit) is valid and useful.

**Required modifications:**
- Revise AD 28 rationale: drop "W3C SCXML Recommendation as semantic standard" claim
- Replace with: "The state machine follows UML statechart semantics (states, transitions, guards, entry/exit actions) — the conceptual vocabulary shared by XState, SCXML, and `transitions`. YAML is the canonical artifact. SCXML is not adopted because its executable-content model conflicts with Python guards. For teams needing standards-based interchange, YAML→XState-JSON export is a future option."
- Keep the SCXML↔YAML mapping table as an informative reference (not a compliance claim)
- If a specific regulator requires SCXML, name it; otherwise remove the compliance assertion

### JUDGE RULING-6: Progressive model escalation (Debate-6)

**Ruling: ACCEPT Agent 1's recommendation**

The court finds that conflating reliability failover with cost-quality routing is an architectural defect. Agent 1's URL evidence is authoritative and unanimous across 4 independent sources. This is the framework's central cost-control mechanism.

**Required modifications:**
- Split gateway §4.2 escalation into two explicit layers:
  1. **Reliability layer**: provider outage/rate-limit → fast failover to same-tier model on different provider. Tracked as `failover_reason: provider_unhealthy`.
  2. **Quality layer**: schema-violation/low-confidence → slow escalation to more capable model. Tracked as `escalation_reason: quality_rejection`.
- Default `trigger_on` must separate the two categories
- Document the cost formula explicitly
- Add `escalation_rate` SLO alert
- Update AD 31 to reflect the split

### JUDGE RULING-7: LLM Gateway vs Instructor (Debate-7)

**Ruling: COMPROMISE**

The court finds that the spec should reference Instructor as the recommended implementation, but the framework's interface definitions are valid as framework-level abstractions. The spec should add Instructor as an explicit option, not replace the entire gateway design.

**Required modifications:**
- In llm-gateway §5, add "Option E: Instructor (Recommended Production Default)" — Pydantic + auto-retry + 15+ providers, 3M+ monthly downloads
- In tool-ecosystem §10, add Instructor and PydanticAI to the tool catalog
- Reframe the gateway as "thin policy layer over Instructor" — the framework's value-add is budget/escalation/audit, not structured-output validation
- Keep existing Options A-D as framework interface definitions (they describe what the gateway does, not how to implement it)

### JUDGE RULING-8: Dual-scope parallel extraction (Debate-8)

**Ruling: COMPROMISE**

The court finds that Agent 1's evidence is correct: dual-scope parallel extraction is not an industry pattern and doubles cost on every turn. However, the spec's rationale (catching out-of-order fields) is a real concern. The compromise: make the broad-scope scan **conditional** (only when narrow-scope is incomplete), not parallel-on-every-turn.

**Required modifications:**
- Rewrite extraction §2.5/§2.6: LLM 1 (narrow scope) runs on every turn. LLM 2 (broad scope) runs ONLY when LLM 1 is incomplete (missing required fields) or confidence < threshold.
- Stop claiming this is "industry standard" — it's a framework-specific optimization
- Document the per-turn token cost of the broad scan
- Add an eval measuring whether LLM 2 recovers enough out-of-order fields to justify the conditional cost
- Update AD 30 to reflect the conditional (not parallel) design

### JUDGE RULING-9: Temporal for durable execution (Debate-9)

**Ruling: ACCEPT Agent 1's recommendation (as optional layer)**

The court finds that LangGraph alone is insufficient for side-effecting workflows. The framework's flagship use cases (lead distribution, payment collection) are exactly the cases where durable execution matters. Temporal should be an optional layer, not a replacement for LangGraph.

**Required modifications:**
- Revise AD 1: "Python + LangGraph (agent reasoning) + optional Temporal (durable orchestration for side-effecting workflows)"
- In routing §5.4 (async sub-workflow), add "Durable Execution" subsection: async sub-workflows involving side effects SHOULD be wrapped in a Temporal activity
- In routing §6 (retry), distinguish within-node retries (LangGraph) from cross-workflow retries (durable orchestration)
- Add Temporal to tool-ecosystem §1.1 under "Runtime Engine"
- Add Temporal-LangGraph plugin to References

### JUDGE RULING-10: OpenAPI 3.1 rationale (Debate-10)

**Ruling: COMPROMISE**

The court finds that the choice of OpenAPI 3.1 is defensible (downstream API contracts benefit), but the rationale misrepresents the tooling landscape. Draft 2020-12 is the canonical JSON Schema, not "less mature."

**Required modifications:**
- Fix AD 29 rationale: "OpenAPI 3.1 is chosen because the domain model also defines downstream REST API contracts in the same file; the LLM-relevant subset is JSON Schema Draft 2020-12, which OpenAPI 3.1 is a superset of. `discriminator` and `oneOf` are OpenAPI extensions that the gateway must strip for LLM providers."
- Remove "JSON Schema Draft 2020-12: Less mature tooling" claim
- In domain-model §2.3, note that `discriminator`/`oneOf`/`if-then-else` are domain-model features enforced by the Validate node (post-LLM), not by LLM structured output
- Add Agent 1's ISSUE-14 (Structured Outputs schema constraints) as a related modification to gateway §5/§6.4

---

## Step 4: Summary of All Rulings

| Ruling | Type | Issue Count | Status |
|--------|------|-------------|--------|
| R1 | ACCEPT (unanimous) | intent-classification keyword cascade | Apply |
| R2 | ACCEPT (agreed) | PII split ownership | Apply |
| R3 | COMPROMISE (agreed) | Routing append-only model | Apply |
| R4 | ACCEPT (Agent 0 upgraded) | A2A v1.0 alignment | Apply |
| R5 | COMPROMISE | SCXML rationale revision | Apply |
| R6 | ACCEPT | Model escalation split | Apply |
| R7 | COMPROMISE | Instructor as recommended option | Apply |
| R8 | COMPROMISE | Conditional broad-scope extraction | Apply |
| R9 | ACCEPT (optional layer) | Temporal for durable execution | Apply |
| R10 | COMPROMISE | OpenAPI 3.1 rationale fix | Apply |

### Unanimously Accepted Issues (apply immediately, no debate)

**86 issues** accepted from the overlap analysis (U1-U86) plus Agent 1's evidence-backed unique findings (A1-3, A1-8, A1-9, A1-10, A1-11, A1-12, A1-14, A1-15, A1-16, A1-17, A1-18, A1-19).

### Total Issue Count

| Source | Total | Accepted | Debated | Rejected |
|--------|-------|----------|---------|----------|
| Agent 0 | 50 | 48 | 2 (Debate-1, Debate-2) | 0 |
| Agent 1 | 20 | 12 | 8 (Debates 4-10, 5-9) | 0 |
| Agent 2 | 66 | 66 | 0 (all overlapped with Agent 0/1) | 0 |
| **Total** | **136** | **126** | **10** | **0** |

All 10 debated issues were resolved (7 ACCEPT, 3 COMPROMISE). Zero rejections.
