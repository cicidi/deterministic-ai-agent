# Agent 2 — Cross-Model Review

**Date:** 2026-06-24
**Reviewer:** Agent 2 (Cross-model reviewer)
**Scope:** 21 spec documents + 7 example files (+ `workflow.yaml`/`audit-log-sample.json` and `docs/domain-models/*.yaml` referenced by specs, verified to exist)
**Method:** Independent adversarial pass. No access to Agent 0 / Agent 1 output. Every finding cites a section/line and a concrete fix.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 16 |
| MEDIUM | 30 |
| LOW | 16 |
| **TOTAL** | **66** |

The dominant failure mode is **cross-spec contradiction on shared concepts** (IntentDef, AgentState, errorNode, intent→agent routing, type/strategy enums) and **stale/duplicated content** left over from the insurance→mortgage domain unification and incremental edits. Several "canonical / single source of truth" claims are violated by the very specs that reference them. Examples mostly follow spec patterns, but the two `workflow.yaml` files use incompatible schema styles and the mortgage-lead intent catalog contradicts the `complex` flag semantics.

---

## Per-Spec Quality Scores

| Spec File | Correctness | Completeness | Clarity | Consistency | Trade-off | Overall |
|-----------|-------------|--------------|---------|-------------|-----------|---------|
| HLD (framework-design) | 7 | 7 | 8 | 6 | 8 | 7.2 |
| state-machine | 6 | 8 | 7 | 6 | 8 | 7.0 |
| domain-model | 6 | 7 | 7 | 5 | 7 | 6.4 |
| intent-classification | 5 | 8 | 7 | 4 | 6 | 6.0 |
| extraction-layer | 5 | 6 | 7 | 5 | 6 | 5.8 |
| routing-execution | 5 | 8 | 7 | 4 | 7 | 6.2 |
| response-generation | 6 | 7 | 7 | 6 | 7 | 6.6 |
| llm-gateway | 5 | 8 | 6 | 5 | 8 | 6.4 |
| tool-ecosystem | 5 | 8 | 6 | 5 | 7 | 6.2 |
| environment-config | 6 | 7 | 7 | 5 | 7 | 6.4 |
| observability-monitoring | 6 | 8 | 8 | 6 | 8 | 7.2 |
| rate-limiting | 7 | 8 | 8 | 6 | 8 | 7.4 |
| a2a-protocol | 7 | 8 | 8 | 6 | 8 | 7.4 |
| mcp-api-protocol | 6 | 8 | 8 | 6 | 8 | 7.2 |
| auth-token-verification | 6 | 7 | 7 | 6 | 7 | 6.6 |
| conversation-lifecycle | 6 | 8 | 8 | 5 | 7 | 6.8 |
| widget-templates | 4 | 7 | 6 | 3 | 6 | 5.2 |
| agent-types | 5 | 7 | 7 | 4 | 6 | 5.8 |
| rag-interface | 7 | 7 | 8 | 6 | 7 | 7.0 |
| cicd-jenkins-pipeline | 6 | 8 | 7 | 5 | 7 | 6.6 |
| three-tier-testing | 5 | 8 | 7 | 4 | 7 | 6.2 |
| Examples (home-insurance) | 5 | 7 | 7 | 5 | n/a | 6.0 |
| Examples (mortgage-lead) | 5 | 7 | 7 | 4 | n/a | 5.8 |
| Examples (cicd) | 7 | 7 | 8 | 7 | n/a | 7.3 |

---

## CRITICAL

### ISSUE-1: consistency / correctness — Intent classification offers a keyword-cascade option (Option B) that the same spec explicitly removed
- **Type:** consistency / correctness / trade_off_gap
- **Section:** intent-classification §2.4 (lines 263-285), §3.4 (lines 325-335), Changelog 0.6.0 (line 17), `ClassifiedIntent.source` enum (line 345)
- **Problem:** §2.4 presents "Option B: Cascade (Keyword-First, LLM-Second)" as a supported strategy with a favorable comparison matrix (zero LLM cost, <5ms latency). But the 0.6.0 changelog states *"Remove keyword fallback entirely … simplify to LLM-only flow with `unrecognized_intent` as the sole fallback; remove `"keyword"` from `ClassifiedIntent.source` enum."* §3.4 reinforces: *"There is no keyword fallback."* So Option B is documented as available while the decision history and flow section say it was deleted. If Option B were supported it would emit `source: "keyword"`, but the enum is now only `"llm" | "unrecognized"` — Option B has no valid source value. The matrix also fails trade-off honesty: it presents Option B favorably for high-volume deployments while the actual decision removed it.
- **Proposed Fix:** Either (a) delete Option B + its matrix column and state LLM-first is the only strategy (align with changelog + §3.4), or (b) if the "≥2 options per interface" VISION rule forces keeping it, restore `"keyword"` to the `source` enum, re-add keyword fallback to §3.4, and add an explicit "Decision: NOT recommended — removed in 0.6.0; retained only as a documented alternative" note. Pick one.
- **Severity:** CRITICAL

### ISSUE-2: consistency — Two incompatible `IntentDef` schemas for the same concept across two specs
- **Type:** consistency
- **Section:** domain-model §5.1 (lines 453-491) vs intent-classification §2.3 (lines 211-246)
- **Problem:** Both specs define `IntentDef` with different fields:
  - intent-classification §2.3: `name, description, complex, keywords, examples` (keywords = metadata only).
  - domain-model §5.1: `name, description, confidence_threshold, entry_state, examples, fallback_intent` (no `complex`, no `keywords`; adds `entry_state` + `fallback_intent`).
  Two different contracts for one concept. A developer cannot tell which schema an intent definition must satisfy. Downstream code (extraction `INTENT_PAYLOAD_MAP`, agent dispatch, state routing) depends on fields that exist in only one.
- **Proposed Fix:** Define `IntentDef` once (intent-classification owns it) and have domain-model cross-reference it. Unified schema must include `complex`, `keywords` (metadata), `examples`, `entry_state`, `fallback_intent`, `confidence_threshold`. Remove the duplicate from domain-model §5.1.
- **Severity:** CRITICAL

### ISSUE-3: consistency / correctness — AgentState concurrency model contradicts itself (append-only "not configurable" vs configurable reducers)
- **Type:** consistency / correctness
- **Section:** routing-execution §1.2 (lines 85, 105, 114) vs §1.3 (lines 130-150)
- **Problem:** §1.2 states *"The framework uses a single strategy: append — all parallel writes are accumulated, never overwritten"* and §1.3 states *"All `agentState` fields use append-only semantics. This is not configurable — it is a framework-level enforcement."* Yet §1.3 immediately shows a `state_reducers:` YAML with `collectedFields: conflict_detect`, `response: last_write_wins`, `goal_check_result: last_write_wins`, and the `Reducer` interface lists `"last_write_wins" | "conflict_detect" | "append" | "merge" | "custom"`. §1.2's scalar table says scalars wrap as `[old, new]`; §1.3 says `response: last_write_wins`. The "not configurable / append-only" claim is directly contradicted by the configurable reducer interface in the same spec.
- **Proposed Fix:** Keep configurable reducers (the useful design). Rewrite §1.2/§1.3 to say append is the **default** and `last_write_wins`/`conflict_detect` are opt-in per field via `state_reducers`. Remove "not configurable"/"single strategy: append". Reconcile the scalar rule (wrap vs last_write_wins) to one.
- **Severity:** CRITICAL

### ISSUE-4: correctness — `check_rates` intent is routed to mutually exclusive handlers across four specs
- **Type:** consistency / correctness
- **Section:** intent-classification §5.2 (line 439, `check_rates → ReadOnlyAgent`), agent-types §2.1 (lines 62-64, check_rates listed under "NOT assigned to ReadOnlyAgent … deterministic lookups"), extraction §7.2 (line 758, `check_rates → collect_financial_profile_extract`), domain-model §5.1 (line 471, `check_rates.entry_state: submit_lead`), mortgage-lead/intent-definitions.md (line 70, `check_rates → ReadOnlyAgent`)
- **Problem:** `check_rates` is mapped four ways: (a) ReadOnlyAgent (intent-classification + example), (b) deterministic state-machine lookup, explicitly NOT ReadOnlyAgent (agent-types §2.1 docstring), (c) `collect_financial_profile_extract` node (extraction §7.2), (d) `submit_lead` entry state (domain-model §5.1). (a) and (b) directly contradict; (c) and (d) contradict each other and both conflict with (a)/(b). A reader cannot determine the correct routing for a primary domain intent.
- **Proposed Fix:** Pick one canonical routing and reconcile all four specs. If `check_rates` is a read-only RAG query → ReadOnlyAgent (aligns with intent-classification + example); then agent-types §2.1 must remove `check_rates` from the "NOT assigned" list, and extraction/domain-model must drop or relabel the `collect_financial_profile_extract` / `submit_lead` mappings. Add a single "intent → agent → entry_state" table all specs reference.
- **Severity:** CRITICAL


---

## HIGH

### ISSUE-5: consistency — Canonical `AgentState` schema omits `phase_stack` that two specs depend on
- **Type:** consistency / missing_edge_case
- **Section:** domain-model §10.1 (lines 726-791), routing-execution §4.2 (line 398 `phase_stack`), conversation-lifecycle §4.2 (line 259 `phase_stack`)
- **Problem:** domain-model §10.1 declares itself the canonical AgentState schema (`required: [conversation_id, user_id, phase, fieldTo, fieldExtractedList, collectedFields]`) and lists every property. But routing §4.2's phase-return-stack relies on `agentState.phase_stack`, and conversation-lifecycle §4.2 persists `phase_stack` in checkpoints. `phase_stack` is not in the canonical AgentState. The "single source of truth" is missing a field the framework's phase-routing and resume features require. (Likewise `goal`, `goal_check_result`, `response` are used by response-gen/routing but absent from §10.1.)
- **Proposed Fix:** Add `phase_stack` (array of strings, default `[]`), plus `goal`, `goal_check_result`, `response` to AgentState in domain-model §10.1, cross-referencing the owners. Audit all child specs for fields used but absent from §10.1.
- **Severity:** HIGH

### ISSUE-6: consistency — Widget Templates spec mixes insurance and mortgage domains (deductible/premium/policy in a mortgage product)
- **Type:** consistency / clarity
- **Section:** widget-templates §1 (lines 20-21), §3.1 (lines 269-274), §3.2 (lines 303-322), §3.3 (lines 354-361), §4.3 (line 516 "HOME INSURANCE CHAT"), §2.5 (line 176 app_name "MortgageLead")
- **Problem:** The spec says it is *"specifically designed for `mortgage_lead`"* (line 269) and `app_name` is "MortgageLead" (line 176), but the widget catalog is insurance-themed: inputs include `deductible` (lines 303-307, 356-359), outputs include `policy_end_date` (line 322), the comparison columns are "provider/rate/deductible/limits" (line 357), and §4.3 ASCII is titled "HOME INSURANCE CHAT" (line 516) while showing "Premium/Deductible/Cov." columns. Mortgages have no deductible/policy-end; insurance has no loan_amount. The domain is internally incoherent and will mislead anyone copying these templates.
- **Proposed Fix:** Choose one domain. If mortgage: remove `deductible`, `policy_end_date`→`loan_term_end_date`, "provider/rate/deductible/limits"→"lender/rate/term/monthly_payment", rename §4.3 to "MORTGAGE LEAD CHAT". If insurance: change `app_name` and replace `loan_amount`→`coverage_amount` consistently. Align response-gen §7.1 (`rate_breakdown_card` = "Insurance rate details") with the chosen domain.
- **Severity:** HIGH

### ISSUE-7: consistency — `transitions` library is introduced as the runtime FSM in tool-ecosystem, contradicting the state-machine spec's LangGraph-only runtime
- **Type:** consistency
- **Section:** tool-ecosystem §8 (lines 1055-1095), §1.1 (line 52), VISION §8 (no `transitions` listed)
- **Problem:** state-machine §1 states *"transitions defines WHAT. LangGraph executes HOW … the LangGraph graph is auto-generated"* — LangGraph is the sole runtime. tool-ecosystem §8 introduces a second runtime (`transitions.Machine`) the state-machine spec never mentions, claiming the FSM is generated into `transitions.Machine` then wrapped into LangGraph. VISION §8 cross-cutting list omits `transitions`. Unresolvable ambiguity about whether `transitions` is part of the runtime.
- **Proposed Fix:** Remove §8 (or demote `transitions` to an optional offline Graphviz-export utility) and align with state-machine §1: YAML → LangGraph directly. Update §1.1 and §12 decision matrix.
- **Severity:** HIGH

### ISSUE-8: correctness — Payload guardrail treats boolean `False` as empty, breaking `confirm`/`decline` payloads
- **Type:** correctness / missing_edge_case
- **Section:** extraction-layer §3.6 (line 408: *"for boolean payloads, `False` is also treated as empty."*)
- **Problem:** `ConfirmIntentPayload`/`DeclineIntentPayload` use `fields: dict[str, bool]` (§3.5). `False` is a legitimate value (`{"proceed": false}` = user declines a field). The guardrail rule "False is also treated as empty" rejects these as `GuardrailError`, breaking the two core conversation-control intents.
- **Proposed Fix:** Remove the "False is also treated as empty" clause for boolean payloads; treat only `None`/`""` as empty. Add a test case for `ConfirmIntentPayload({"proceed": false})` passing the guardrail.
- **Severity:** HIGH

### ISSUE-9: correctness — Duplicate `floor_area` key in an LLM Gateway `output_schema` example (invalid YAML/JSON Schema)
- **Type:** correctness
- **Section:** llm-gateway §7.1 (lines 849-854)
- **Problem:** The Layer 1 extraction `output_schema` example declares `floor_area` twice — once `required: true` (line 849) and once `required: false` (line 852). Duplicate keys are invalid in JSON Schema and produce a silent last-wins bug in YAML parsers, so the canonical "MANDATORY output_schema" illustration is wrong.
- **Proposed Fix:** Rename the second field (e.g., `floor_area_unit`) or delete it. Validate all schema examples with a YAML/JSON Schema linter in CI.
- **Severity:** HIGH

### ISSUE-10: correctness — Duplicate `llm_retry_total` metric definition with two different semantics
- **Type:** correctness
- **Section:** observability-monitoring §2.1 (line 77 and line 80)
- **Problem:** The metric taxonomy lists `llm_retry_total` twice: line 77 "Retry attempts (across all calls)" and line 80 "Retries before escalation or success (by node_id, error_type)". Prometheus metric names must be unique; two definitions with different label sets/descriptions is an invalid schema. §2.2 collectors and §2.3 hooks reference it once, so one definition is dead.
- **Proposed Fix:** Keep one `llm_retry_total` (recommend the per-node/error_type version with labels `node`, `error_type`, `attempt`) and delete the other row; rename the aggregate to `llm_retry_attempts_total` if both are needed.
- **Severity:** HIGH

### ISSUE-11: policy violation — Non-English (Chinese) text committed in spec files
- **Type:** consistency / completeness (governance)
- **Section:** three-tier-testing §3.3 (line 173), §6.2 (line 430), §11 (line 545), §19 (lines 810-811) — "举一反三" (5 occurrences); HLD Appendix A.5 (line 337) — "举一反三"
- **Problem:** CLAUDE.md / VISION principle #10: *"Every file committed to the GitHub repository must be in English. Non-English content belongs only in directories listed in `.gitignore`."* `docs/specs/` files are committed English specs, yet contain Chinese "举一反三" (idiom = "infer one thing from many / edge-case inference"). Direct, repeated violation of a hard project rule.
- **Proposed Fix:** Replace every "举一反三" with "edge-case inference" or "by-analogy variants". Add a CI lint (grep for CJK Unicode ranges in `docs/specs/`) to prevent recurrence.
- **Severity:** HIGH

### ISSUE-12: correctness — Mortgage-lead intent catalog marks `submit_lead` as `Complex: No`, contradicting the spec's own example and multi-intent rules
- **Type:** consistency / correctness
- **Section:** mortgage-lead/intent-definitions.md (lines 9-26, all write intents `Complex: No`), vs intent-classification §2.3 (lines 233-246, `submit_lead` example `complex: true`), §4.3 (combination rules)
- **Problem:** The catalog sets `Complex: No` for `submit_lead`, `provide_lead_detail`, `create_quote`, etc. But intent-classification §2.3's own `submit_lead` example sets `complex: true`, and §4.3's rules exist to prevent multiple `complex: true` intents combining in one turn. `submit_lead` is a multi-turn task (identify_borrower → purpose → amount → … → submit) — the textbook complex intent. Marking it `No` lets the combination validator allow two `submit_lead`-class tasks together, the exact failure §4.3 prevents. The catalog also lists only 7 of 17 system intents and omits `complex` from its IntentDef schema sketch.
- **Proposed Fix:** Set `complex: true` for `submit_lead`, `provide_lead_detail`, `create_quote`, `add_product_quote`, and other multi-turn write intents. Add the `complex` field to the catalog's IntentDef sketch and include all 17 system intents (or explicitly state which are inherited).
- **Severity:** HIGH

### ISSUE-13: correctness — LLM Gateway has duplicate "Environment-Specific Defaults" sections and an orphaned table fragment under "Sticky Model"
- **Type:** correctness / clarity
- **Section:** llm-gateway §4.6 (lines 573-579), §4.7 "Sticky Model (Escalation Memory)" (lines 581-588), §4.8 "Environment-Specific Defaults" (lines 589-595)
- **Problem:** Two sections are both titled "Environment-Specific Defaults" (§4.6 and §4.8) with different content. §4.7 is titled "Sticky Model" but its body (lines 582-588) is a comparison-table fragment (Provider redundancy / Cost predictability / Latency overhead …) with no header row — not about sticky model; the real sticky-tier content is §4.9. The 0.3.1 changelog claims duplicate headings were renamed, but these remain. §4.8 introduces `gpt-4.1`, absent from §4.1's provider config.
- **Proposed Fix:** Delete §4.8 (duplicate); keep one Environment-Specific Defaults table. Move/delete the orphaned fragment in §4.7 and merge its content into §4.9. Remove `gpt-4.1` or add it to §4.1 consistently.
- **Severity:** HIGH

### ISSUE-14: consistency — Two example `workflow.yaml` files use incompatible transition-schema styles; one contradicts the state-machine spec
- **Type:** consistency
- **Section:** home-insurance/workflow.yaml (top-level `transitions:`, lines 251-356) vs mortgage-lead/workflow.yaml (inline `transitions:` per state, lines 34-36, 49-50, 73-77, 169-173) vs state-machine §1.1 Option A/C and domain-model §6.4 (top-level `transitions:`)
- **Problem:** home-insurance uses top-level `transitions:` (matching specs); mortgage-lead nests `transitions:` inside each state (matching neither spec). The two reference examples for the same framework cannot both be valid against the same loader. A developer copying mortgage-lead's inline style produces a workflow the spec's generator does not describe.
- **Proposed Fix:** Convert mortgage-lead/workflow.yaml to top-level `transitions:` (from/to/guard). State in the state-machine spec which layout is canonical and have the loader reject the other.
- **Severity:** HIGH

### ISSUE-15: completeness — Extraction/Validate/Transform "Option B/C" appear in comparison matrices but are never described
- **Type:** completeness
- **Section:** extraction-layer §3.4 (matrix lists Option B Deterministic, Option C Hybrid), §4.4 (Option B Predicate, Option C Pydantic), §5 (only §5.3 Option A described), §6.4/§6.5 (`deterministic | llm_assisted | hybrid`)
- **Problem:** §3.2 describes only Option A. §3.4's matrix compares A/B/C. §3.3 says "Options B and C use state context to scope the fallback rules" but B and C are never defined. Same in §4 (only Option A rule engine; matrix compares A/B/C) and §5 (only Option A pipeline; `transform_strategy: llm_assisted | hybrid` referenced but undefined). A developer cannot implement B or C. This also weakens the VISION "≥2 options per interface" rule — the second option is named but unspecified.
- **Proposed Fix:** Add short §3.2 Option B (Deterministic regex/keyword) + Option C (Hybrid) subsections; same for §4.3 Option B (Predicate)/Option C (Pydantic) and §5.3 Option B (llm_assisted)/Option C (hybrid). One paragraph each (contract + strengths/weaknesses) suffices.
- **Severity:** HIGH

### ISSUE-16: consistency — `errorNode` strategies referenced under non-canonical short names in multiple specs
- **Type:** consistency
- **Section:** routing-execution §6.5 (canonical `ask_clarify | escalate_to_human | terminate | fallback_value | retry_with_context`), tool-ecosystem §2.2 (line 99 `clarify / escalate / terminate`), §7.4 (line 546 `strategies: [clarify, escalate, terminate]`, `on_clarify`/`on_escalate`/`on_terminate`), a2a §6.3 (line 433)
- **Problem:** routing §6.5 declares itself canonical and says other specs MUST cross-reference it. But tool-ecosystem uses short names (`clarify`, `escalate`, `terminate`) and config keys (`on_clarify`, `on_escalate`) that don't match the canonical enum (`ask_clarify`, `escalate_to_human`, `terminate`). A node configured with `on_clarify` won't bind to canonical `ask_clarify`. This is exactly the "discrepancy = spec bug" case §6.5 warns about.
- **Proposed Fix:** Replace all short names with canonical enum values; rename `on_clarify`→`on_ask_clarify`, `on_escalate`→`on_escalate_to_human`. Add cross-references to routing §6.5.
- **Severity:** HIGH

### ISSUE-17: correctness — Home-insurance e2e scenario has internal numeric/math inconsistencies
- **Type:** correctness
- **Section:** home-insurance/e2e-scenarios.md Scenario 1 (lines 50, 126-129, 213, 215) and Scenario 4 (lines 185, 398, 404, 411)
- **Problem:** Multiple contradictions within the same scenario:
  - Building age: line 50 `building_age: "9" … current year 2024 → age=9`; line 126 calls `compute_risk_score(age=11, …)`; audit log line 213 uses `"age":9`. 2015→2026=11, 2015→2024=9 — "current year" and age disagree.
  - Risk numbers: dialogue (lines 127-138) `risk_score=18`, `rate_multiplier=0.872`, `annual_premium=6,104`; audit log (lines 213-215) `risk_score=14`, `rate_multiplier=0.856`, `annual_premium=5,992`. Two result sets for one scenario.
  - Scenario 4 merge (line 398) and Key Design Points (line 185): `phone: LLM1(0.76) < 0.7` — 0.76 is **not** < 0.7; the comparison is false, so the "fallback to LLM2" logic is mathematically wrong.
  - Scenario 4 validate (line 404): `"555-1234"` is 7 digits, but Validate claims `pattern ^\+?1?\d{10}$ → PASS (10 digits)`; then Transform (line 411) fails on "missing area code". A 7-digit string cannot pass `\d{10}`, so Validate should also have failed.
- **Proposed Fix:** Reconcile to one age (use 2026 → age 11, or state "current year 2024" consistently) and one set of risk/premium numbers across dialogue + audit. Fix the threshold comparison (change 0.76 to <0.7, or change the branch to "LLM1 ≥ 0.7 → use LLM1"). Fix the phone digit count (10-digit number or 7-digit pattern).
- **Severity:** HIGH

### ISSUE-18: consistency — `general_inquiry` intent used in eval/examples but is not a system intent and is defined inconsistently
- **Type:** consistency
- **Section:** cicd-jenkins §4.1 (line 555 `intent: general_inquiry`), domain-model §5.1 (lines 477-482 `general_inquiry`), intent-classification §2.1 (17 system intents — no `general_inquiry`)
- **Problem:** `general_inquiry` appears as an expected eval intent and as a `fallback_intent` target, but is not one of the 17 system intents and is only defined inside domain-model §5.1's example. The `fallback_intent` concept itself only exists in domain-model's IntentDef, not intent-classification's (see ISSUE-2).
- **Proposed Fix:** Either add `general_inquiry` as an 18th system intent in intent-classification, or make references explicitly domain-specific and ensure `fallback_intent` is part of the unified IntentDef (ISSUE-2).
- **Severity:** HIGH

### ISSUE-19: consistency — `small_talk` / `greeting` / `greet` intent names used in examples/specs vs `chitchat` / `start_conversation` in the intent spec
- **Type:** consistency
- **Section:** conversation-lifecycle §9.4 (line 666 "greeting, small_talk, out_of_scope"), mortgage-lead/e2e-scenarios.md Scenario 7 (line 115 `small_talk`), three-tier-testing §3.2 (line 149 `greet`), vs intent-classification §2.1 (`chitchat`, `start_conversation`)
- **Problem:** Canonical system intents are `chitchat` and `start_conversation`. Multiple downstream artifacts use non-existent names: `small_talk`, `greeting`, `greet`. conversation-lifecycle's chitchat-turn counter keys off `greeting`/`small_talk`, which will never match real `chitchat`. The three-tier MockGateway returns `greet`, not a valid label anywhere.
- **Proposed Fix:** Replace `small_talk`/`greeting`/`greet` with `chitchat`/`start_conversation`. Update conversation-lifecycle §9.4's non-business list to `chitchat`, `out_of_scope`, `help`.
- **Severity:** HIGH

### ISSUE-20: consistency — Home-insurance workflow uses custom error-recovery states instead of the canonical `errorNode`
- **Type:** consistency
- **Section:** home-insurance/workflow.yaml (lines 104, 169, 216, 230-241 `error_recovery`/`claim_error_recovery` states; transitions lines 299, 306, 345), vs routing §6.5 and domain-model §6.5 ("Do not declare errorNode as a state … always reachable … framework-injected")
- **Problem:** The canonical model says errorNode is a framework primitive, never declared as a state, always reachable without a transition rule. The example instead declares `error_recovery` and `claim_error_recovery` as first-class states and writes explicit `to: error_recovery` transitions — directly contradicting the "single source of truth" it claims to follow.
- **Proposed Fix:** Replace `error_recovery`/`claim_error_recovery` with framework `errorNode` (remove state declarations + explicit transitions; use per-node `on_error: errorNode` + errorNode strategy config). Model different recovery messages as errorNode strategies/branches, not separate states.
- **Severity:** HIGH


---

## MEDIUM

### ISSUE-21: correctness — State-machine SCXML mapping cites the wrong open-question number for `<history>`
- **Type:** correctness
- **Section:** state-machine §1.0 table (line 52: `<history> … deferred (Appendix C.1 Q5)`), Appendix C.1 (Q3 = history state line 678; Q5 = dynamic vs static line 680)
- **Problem:** The SCXML↔YAML table defers history to "Appendix C.1 Q5", but Q5 is "Dynamic vs static workflow". The history-state question is Q3.
- **Proposed Fix:** Change "Appendix C.1 Q5" → "Appendix C.1 Q3".
- **Severity:** MEDIUM

### ISSUE-22: correctness — Duplicate `return` in `officer_eligible` sample; second references undefined `licensed_states`
- **Type:** correctness
- **Section:** state-machine §1.2 (lines 169-170)
- **Problem:** The guard sample has two consecutive `return` statements; the second uses `licensed_states` (undefined) instead of `ctx.licensed_states`. The first return makes the second dead code, and the undefined name would NameError if reached.
- **Proposed Fix:** Delete the duplicate line 170.
- **Severity:** MEDIUM

### ISSUE-23: correctness — Domain-model §11.2 dynamic-entity example uses non-OpenAPI `values:`/`fields:` after adopting OpenAPI 3.1
- **Type:** correctness / consistency
- **Section:** domain-model §11.2 (lines 944-962), §1.1 (AD 29 — OpenAPI 3.1 Schema Objects adopted)
- **Problem:** §11.2's dynamic-entity example reverts to `lead_type: fields: lead_type: type: enum values: [...]` — custom FieldDef syntax (`fields:`, `values:`) — despite the spec adopting OpenAPI 3.1 where the keywords are `properties:` and `enum:` (on the same level as `type:`). This contradicts the adopted standard.
- **Proposed Fix:** Rewrite the example using `properties:` + `type: string` + `enum: [...]`.
- **Severity:** MEDIUM

### ISSUE-24: completeness — Domain-model §4.3 references undefined `QuoteDetails` schema
- **Type:** completeness
- **Section:** domain-model §4.3 (line 412 `submit_lead` `entity: $ref: "#/components/schemas/QuoteDetails"`), §2.2 (defines Address, Borrower, MortgageLead, LeadSubmission — no QuoteDetails)
- **Problem:** The `submit_lead` state binds to `QuoteDetails`, which is never defined in the §2.2 example. The `$ref` is dangling.
- **Proposed Fix:** Define `QuoteDetails` in §2.2 or change the binding to an existing schema (e.g., `LeadSubmission`).
- **Severity:** MEDIUM

### ISSUE-25: correctness — Extraction §2.5 is labeled §2.5 but cross-referenced as §2.6
- **Type:** correctness / clarity
- **Section:** extraction-layer §2.5 (line 113 "Per-State Extraction Scope"), §3.1 (line 257 "see §2.6"), changelog 0.6.0 ("§2.6 Per-State Extraction Scope")
- **Problem:** The section is numbered §2.5 but §3.1 and the changelog reference "§2.6". There is no §2.6. Readers following the cross-reference hit a dead end.
- **Proposed Fix:** Renumber the section to §2.6 (and shift §2.5 to the original flow section) or fix the cross-references in §3.1 and the changelog to §2.5.
- **Severity:** MEDIUM

### ISSUE-26: correctness / consistency — Extraction type naming inconsistent across §4.2, §6.2, §6.4; `enum` is both a type and a constraint
- **Type:** correctness / consistency
- **Section:** extraction-layer §4.2 (line 496 `type: "int" | "float" | "string" | "date" | "boolean" | "enum"`), §6.2 (line 604 `type: "integer" | "number" | "string" | "boolean"`), §6.4 (line 660 `type: int`; line 649 `type: enum`), §6.2 note (line 613 "enum is a constraint on a string field, not a type")
- **Problem:** Three different type vocabularies: §4.2 uses `int/float/enum`, §6.2 uses JSON Schema `integer/number`, §6.4 examples use `int`/`enum`. §4.2 lists `enum` as a type while §6.2 explicitly says enum is "not a type". Direct contradiction + invalid schema coherence.
- **Proposed Fix:** Standardize on JSON Schema types (`integer`, `number`, `string`, `boolean`, `array`, `object`) everywhere. Remove `enum` and `int`/`float` as types; `enum` is always a constraint alongside `type: string`.
- **Severity:** MEDIUM

### ISSUE-27: consistency — Response-gen gap threshold has two incompatible config keys for the same concept
- **Type:** consistency
- **Section:** response-generation §4.3 (`gap_threshold: 0.3`, "completion < (1-threshold) → 422"), §4.5 (`transactional_threshold: 0.7`, "70% completion required")
- **Problem:** §4.3 uses an inverse `gap_threshold: 0.3` (completion < 0.7 → 422); §4.5 uses a direct `transactional_threshold: 0.7`. Two config keys, two semantics, same threshold. env-config §2.1 sets `GAP_THRESHOLD=0.3`, so §4.5's `transactional_threshold` is an undefined second key.
- **Proposed Fix:** Pick one key. Recommend `gap_threshold` (inverse, matches env-config) everywhere, or `completion_threshold` (direct) everywhere. Remove the other and align env-config.
- **Severity:** MEDIUM

### ISSUE-28: consistency — Response-gen §8.2 says "PII Rules (Defined in Domain Model)" but domain model has no PII rules section
- **Type:** consistency
- **Section:** response-generation §8.2 (lines 580-590 heading + body), domain-model (no `pii_rules` section in §2.2 example or elsewhere), domain-model §10.3 (line 879 says authoritative PII rules are in response-gen §8)
- **Problem:** response-gen §8.2 heading says PII rules are "Defined in Domain Model", but domain-model defines no PII rules and §10.3 points back to response-gen §8 as authoritative. Circular/misleading: where do PII rules actually live?
- **Proposed Fix:** Make response-gen §8.2 the authoritative home (it already contains the `pii_rules` YAML) and fix the heading to "PII Rules (defined here; referenced by domain model ConversationMessage.masked)". Remove the "Defined in Domain Model" wording.
- **Severity:** MEDIUM

### ISSUE-29: consistency — Conversation-lifecycle §2.1 says `paused → timeout`, but §2.2/§2.3 route `paused → archived`
- **Type:** consistency
- **Section:** conversation-lifecycle §2.1 table (line 61: paused "Transitions To: active, abandoned, timeout"), §2.2 (line 86: `paused: on: idle_24h: archived`), §2.3 (line 153: `paused → archived`)
- **Problem:** §2.1 lists `timeout` as a paused transition target, but §2.2/§2.3 go `paused → archived` directly (no paused→timeout). `timeout` should only be reachable from `active` (idle), not from `paused`. §2.1's table is wrong.
- **Proposed Fix:** Remove `timeout` from §2.1's paused "Transitions To" (keep `active, abandoned, archived`).
- **Severity:** MEDIUM

### ISSUE-30: consistency — Conversation-lifecycle §9.3 metric names don't match observability §2.1 taxonomy
- **Type:** consistency
- **Section:** conversation-lifecycle §9.3 (lines 634-641: `conversations_active_gauge`, `conversations_paused_gauge`, `conversations_timed_out_total`, `avg_conversation_duration_seconds`, `avg_turns_per_conversation`), observability §2.1 (defines `conversations_active` not `_gauge`; does not define the others)
- **Problem:** Lifecycle emits metrics not in the observability taxonomy, and uses a `_gauge` suffix convention observability doesn't use. `conversations_active` vs `conversations_active_gauge` would be two different Prometheus series for the same concept.
- **Proposed Fix:** Align names: use `conversations_active` (not `_gauge`) and add the missing metrics (`conversations_paused`, `conversations_timed_out_total`, `avg_conversation_duration_seconds`, `avg_turns_per_conversation`) to observability §2.1 taxonomy.
- **Severity:** MEDIUM

### ISSUE-31: consistency — Rate-limiting spec leaves "Claims operations" terminology in a mortgage framework
- **Type:** consistency
- **Section:** rate-limiting §2.4 (line 125 "Claims operations get tight limits"), §3.1 (line 179 `lead_distribution_engine`), §3.3 (line 239 "Claims operations/min | 5 | 30 | 100")
- **Problem:** The HLD unified examples on mortgage-lead, but rate-limiting still says "Claims operations" (insurance concept) while the actual tool is `lead_distribution_engine` (lead distribution). The §3.3 tier-comparison row label "Claims operations/min" doesn't match the configured tool.
- **Proposed Fix:** Replace "Claims operations" with "Lead distribution/min" (or the generic "Dangerous write ops/min") and align the row with `lead_distribution_engine`.
- **Severity:** MEDIUM

### ISSUE-32: consistency — Rate-limiting tier names differ between §3 and §8.3 (`free`/`pro` vs `default`/`premium`)
- **Type:** consistency
- **Section:** rate-limiting §3.1 (lines 168-210: `default`, `premium`, `enterprise`), §8.3 (lines 477-485: `free`, `pro`, `enterprise`)
- **Problem:** §3 defines `default`/`premium`/`enterprise`; §8.3's interview-output example generates `free`/`pro`/`enterprise`. Same framework, two incompatible tier vocabularies.
- **Proposed Fix:** Standardize on one tier vocabulary across §3, §8.3, and tool-ecosystem pycasbin policies.
- **Severity:** MEDIUM

### ISSUE-33: correctness — MCP Claude Desktop config mixes stdio (`command`/`args`) and SSE (`url`) in one block
- **Type:** correctness
- **Section:** mcp-api-protocol §5.1 (lines 407-420)
- **Problem:** The config has both `command`/`args` (stdio-style) and `transport: sse` + `url` (SSE-style) in the same `mcpServers` entry. Claude Desktop MCP config is either stdio (command+args) or SSE (url), not both. This is an invalid hybrid.
- **Proposed Fix:** Split into two examples: one stdio (command/args, no url) and one SSE (transport: sse, url, no command).
- **Severity:** MEDIUM

### ISSUE-34: consistency — MCP `get_status` lifecycle_state enum missing `archived`
- **Type:** consistency
- **Section:** mcp-api-protocol §3.4 (line 308 `enum: [created, active, paused, completed, abandoned, timeout]`), domain-model §10.1 (line 784 `enum: [created, active, paused, completed, abandoned, timeout, archived]`)
- **Problem:** MCP `get_status` returns 6 lifecycle states; the canonical AgentState enum has 7 (adds `archived`). An archived conversation's status can't be represented.
- **Proposed Fix:** Add `archived` to the §3.4 enum.
- **Severity:** MEDIUM

### ISSUE-35: consistency — MCP §1.1 claims streaming but §3.2 `send_message` returns a single non-streaming JSON
- **Type:** consistency
- **Section:** mcp-api-protocol §1.1 (line 44 "Streaming support — LLM responses stream token-by-token"), §3.2 (lines 174-230, `send_message` returns one structured JSON `agent_message`)
- **Problem:** §1.1 advertises token-by-token streaming, but the defined `send_message` tool returns a complete structured response (no streaming contract). The headline capability isn't reflected in the tool definition.
- **Proposed Fix:** Either add a streaming variant (`send_message_stream` returning an SSE/JSON-RPC stream) or tone down §1.1 to "streaming available via transport, not via the core tools."
- **Severity:** MEDIUM

### ISSUE-36: correctness — CI/CD References section is split; entries appear after §10
- **Type:** correctness / clarity
- **Section:** cicd-jenkins §References (lines 932-941), §10 (lines 945-947), orphaned references (lines 948-949 `[Conversation Lifecycle]`, Jenkins links)
- **Problem:** The `[Conversation Lifecycle]` and Jenkins/Pipeline references appear *after* §10 "Example Infrastructure" instead of inside the References section. The reference list is structurally broken.
- **Proposed Fix:** Move lines 948-949 up into the References section (before §10), or move §10 above References and consolidate.
- **Severity:** MEDIUM

### ISSUE-37: consistency — CI/CD error-rate thresholds are inconsistent across alert/canary/rollback
- **Type:** consistency
- **Section:** cicd-jenkins §6.2 (line 740 canary `error_rate_threshold: 5`), §7.2 (line 833 rollback auto-trigger `error_rate > 10%`), observability §4.1 (line 338 alert `error_rate > 5%`)
- **Problem:** Three different thresholds for "error rate": 5% (alert + canary) vs 10% (auto-rollback). Canary fails at 5% but rollback only auto-triggers at 10%, so a canary can fail without triggering rollback, and the alert and rollback thresholds are decoupled with no rationale.
- **Proposed Fix:** Pick one threshold (or document the deliberate tiering: alert at 5%, rollback at 10%) and state the rationale inline.
- **Severity:** MEDIUM

### ISSUE-38: consistency — A2A response is named `AgentResult` in §3 table but `a2a_response` in §2.2; registry field names differ between §4.1 and §4.3
- **Type:** consistency
- **Section:** a2a-protocol §3 (line 172 "AgentResult { status, results, audit }"), §2.2 (line 108 `a2a_response:`), §4.1 (lines 248-249 `health_endpoint`/`invoke_endpoint`), §4.3 (lines 283-290 `endpoint`/`health_check_path`)
- **Problem:** The A2A response envelope is called `AgentResult` in the comparison table but `a2a_response` in the message format. The agent-registry entry (§4.1) uses `health_endpoint`/`invoke_endpoint` while static discovery (§4.3) uses `endpoint`/`health_check_path` — two field-name vocabularies for the same concepts.
- **Proposed Fix:** Use one name (`a2a_response` or `AgentResult`) consistently. Unify registry/static-discovery endpoint field names.
- **Severity:** MEDIUM

### ISSUE-39: consistency — Environment-config duplicates a workflow entry and labels home-insurance "legacy"
- **Type:** correctness / consistency
- **Section:** environment-config §5 (lines 290-291: `workflows:` lists `mortgage_lead_submission.yaml` twice), §5 (line 287 `# - "domain-models/home-insurance.yaml" # legacy domain model`)
- **Problem:** The workflows list has a duplicate entry. Home-insurance is commented out as "legacy", but state-machine §2/§4/§6 and the home-insurance example actively use home-insurance as a primary reference domain — calling it "legacy" contradicts its current use.
- **Proposed Fix:** Remove the duplicate workflow line. Either uncomment home-insurance (it's an active example) or drop the "legacy" label and explain it's an alternate example domain.
- **Severity:** MEDIUM

### ISSUE-40: consistency — Environment-config model catalog drifts (`gpt-4.1`, `claude-opus`) from LLM-gateway §4.1
- **Type:** consistency
- **Section:** environment-config §2.1 (line 46 `LLM_MODEL_TIERS=…gpt-4.1…claude-opus`), §4 (line 218 `gpt-4.1`), llm-gateway §4.1 (lines 327-345: gpt-4o-mini, gpt-4o, claude-haiku-3-5, claude-sonnet-4-20250514)
- **Problem:** environment-config references `gpt-4.1` and `claude-opus`, which are not in the llm-gateway provider catalog. The `LLM_MODEL_TIERS` env var also uses an undocumented `→`/`;` mini-syntax not parsed anywhere (§4 uses a structured `tiers:` list).
- **Proposed Fix:** Align the model catalog across both specs. Either document the `LLM_MODEL_TIERS` env-var syntax and parse it, or drop it in favor of the structured YAML `tiers:`.
- **Severity:** MEDIUM

### ISSUE-41: consistency — Environment-config §1 says e2e uses "Mock + real" tools, but §2.3 sets `MOCK_EXTERNAL_APIS=true`
- **Type:** consistency
- **Section:** environment-config §1 table (line 24 e2e Tools "Mock + real (non-destructive)"), §2.3 (line 96 `MOCK_EXTERNAL_APIS=true`)
- **Problem:** §1 claims e2e mixes mock and real APIs; §2.3 sets all external APIs to mock. Contradiction about whether e2e exercises any real APIs.
- **Proposed Fix:** Pick one (recommend e2e = mock APIs + real LLM, matching §2.3) and fix the §1 table cell to "Mock APIs + real LLM".
- **Severity:** MEDIUM

### ISSUE-42: consistency — Environment-config §6.2 option name ("External Config Server (Consul/Vault)") ≠ §5 comment ("Cloud Secret Manager")
- **Type:** consistency
- **Section:** environment-config §6.2 (line 320 "Option B: External Config Server (Consul / Vault)"), §5 (line 273 comment "Option B: Cloud Secret Manager")
- **Problem:** The same Option B is named two different ways in two places.
- **Proposed Fix:** Use one name consistently (recommend "External Config / Secret Server").
- **Severity:** MEDIUM

### ISSUE-43: correctness — Auth `verification_order` is a list value but the comment lists enum string options
- **Type:** correctness
- **Section:** auth-token-verification §2.4 (line 109 `verification_order: [jwt, oauth] # jwt_first | oauth_only | jwt_only`)
- **Problem:** The field value is a list `[jwt, oauth]` but the comment shows enum options `jwt_first | oauth_only | jwt_only`. Inconsistent: is it a list or an enum string? A loader can't tell which contract applies.
- **Proposed Fix:** Pick one form. Recommend an enum string (`verification_order: jwt_first`) and document the allowed values, or keep the list and drop the enum comment.
- **Severity:** MEDIUM

### ISSUE-44: consistency — Auth §2.5 includes Spring/Java concepts (`permitAll`, `grant_type`) in a Python framework that says it does not do OAuth grant flows
- **Type:** consistency
- **Section:** auth-token-verification §2.5 (lines 130 `grant_type: client_credentials`, 147-151 `endpoint_permissions` with `permitAll`), §1.1 ("NOT an OAuth server — does not implement OAuth grant flows")
- **Problem:** §2.5 is "extracted from mfangdai (mRateQuote) production" — a Java/Spring config. It includes `grant_type: client_credentials` and Spring-Security-style `permitAll` endpoint permissions, which (a) the framework explicitly says it doesn't do (grant flows) and (b) are Java concepts in a Python framework spec. Misleading as a framework config sample.
- **Proposed Fix:** Replace the Spring-style `endpoint_permissions`/`permitAll` with the framework's own YAML allowlist model (routing §7.2 NodePermission), and remove `grant_type`/token-issuance fields (the framework only verifies, not issues). Keep the Keycloak JWKS/role-mapping parts which are relevant.
- **Severity:** MEDIUM

### ISSUE-45: consistency — Auth §5 defers RBAC while routing §7 and tool-ecosystem §6 already implement role-based enforcement
- **Type:** consistency / clarity
- **Section:** auth-token-verification §5 (lines 261-265 "Role-Based Access … deferred to a future interface"), routing-execution §7.6 (OAuth scope enforcement), tool-ecosystem §6 (pycasbin RBAC)
- **Problem:** Auth §5 says RBAC is deferred ("only the contract … implementation will follow"), but routing §7.6 and tool-ecosystem §6 already define runtime role/scope enforcement. The high-level "RBAC deferred" statement contradicts the specs that already specify it. (§5.3 partially acknowledges pycasbin exists, but the §5 lead-in still reads as "not designed.")
- **Proposed Fix:** Reword §5 to "RBAC enforcement is defined in routing §7 and tool-ecosystem §6; this spec defines only the RoleResolver → permission bridge, which is deferred." Remove the implication that RBAC as a whole is unbuilt.
- **Severity:** MEDIUM

### ISSUE-46: consistency — Tool-ecosystem casbin policy uses action `transition` not in the model's `act` (read/write); tool name `lead_distribution_engine` vs `lead_distribution_api`
- **Type:** consistency
- **Section:** tool-ecosystem §6.4 (line 321 `r = sub, obj, act # action (read/write)`), §6.5 (line 358 `p, *, collect_lead_purpose, transition`; line 349 `lead_distribution_engine`), routing §7.3 (line 838 `lead_distribution_api`)
- **Problem:** The casbin model defines `act` as read/write, but the policy uses `transition` as an action — not in the model's action space. Also the dangerous-write tool is `lead_distribution_engine` here but `lead_distribution_api` in routing §7.3; `calculate_rate_api` is consistent but the lead tool name drifts.
- **Proposed Fix:** Add `transition` to the model's action vocabulary (or map transitions to `write`), and unify the lead-distribution tool name across all specs.
- **Severity:** MEDIUM

### ISSUE-47: consistency — Observability HighErrorRate alert has two different formulas
- **Type:** consistency
- **Section:** observability-monitoring §4.1 (line 338 `error_rate > 5%`), §4.2 (line 383 `errorNode_invocations / messages_processed > 5%`)
- **Problem:** §4.1 expresses the alert as the `error_rate` gauge > 5%; §4.2 expresses it as a ratio `errorNode_invocations / messages_processed > 5%`. Two formulas for the same alert; unclear which is canonical, and they can disagree when `messages_processed` denominators differ.
- **Proposed Fix:** Define `error_rate` once as `errorNode_invocations_total / messages_processed_total` and reference that single metric in both places.
- **Severity:** MEDIUM

### ISSUE-48: correctness — LLM-gateway audit examples ignore the +1 LLM extra-retry rule
- **Type:** correctness
- **Section:** llm-gateway §4.5 (lines 560-565: `total_attempts: 4`, `tier_0_attempts: 2`, `tier_1_attempts: 2`), §8 (line 932 `total_attempts: 5 // Σ(2+2+1) … for non-LLM`), §3.4 (line 211 `max_attempts = node.retry_budget.max_attempts + 1`)
- **Problem:** §3.4/§4.4 say LLM nodes get +1 retry per tier. But §4.5's audit shows tier_0_attempts=2 and tier_1_attempts=2 (no +1), and §8 comments "for non-LLM" inside the LLM gateway (which is LLM-only). The audit examples use non-LLM math in the LLM gateway, contradicting the +1 rule.
- **Proposed Fix:** Update §4.5 to tier_0_attempts=3, tier_1_attempts=3 (2+1 each), total=6; update §8 to apply the +1 and remove the "for non-LLM" comment (the gateway only handles LLM calls).
- **Severity:** MEDIUM

### ISSUE-49: correctness — LLM-gateway §4.1 "min 2 providers × 2 models" requirement is violated by dev/e2e defaults
- **Type:** correctness
- **Section:** llm-gateway §4.1 (line 367 "less than 2 providers or less than 2 models per provider → config error, framework refuses to start"), §4.6 (line 577 dev "gpt-4o-mini only"), environment-config §4 (e2e: 1 provider, 2 models)
- **Problem:** The startup validation requires ≥2 providers × ≥2 models, but dev configures a single model and e2e configures a single provider. If the requirement is unconditional, dev/e2e can't start; if escalation-disabled environments are exempt, the requirement text doesn't say so.
- **Proposed Fix:** Scope the requirement to "when `model_escalation.enabled: true`"; dev/e2e with escalation disabled are exempt. State this explicitly in §4.1.
- **Severity:** MEDIUM

### ISSUE-50: correctness — Intent-classification §3.3 prompt emits a single-intent schema, but §4.2 contract requires a multi-intent list
- **Type:** correctness / consistency
- **Section:** intent-classification §3.3 (line 321 output instruction `{ intent: string, confidence: number, reasoning: string }`), §4.2 (lines 356-360 `ClassificationResult { intents: ClassifiedIntent[] }`)
- **Problem:** §3.3 tells the LLM to output a single intent object, but §4.2's contract and §4.3's combination rules require a list of intents (multi-intent per message). The prompt construction contradicts the output contract; a single-intent prompt can't produce the multi-intent result §4.2 specifies.
- **Proposed Fix:** Change §3.3's output instruction to `{ intents: [{ intent, confidence, reasoning }] }` (a list), matching §4.2.
- **Severity:** MEDIUM


---

## LOW

### ISSUE-51: completeness — HLD §8 Document Tree is stale (missing 3 specs + home-insurance example)
- **Type:** completeness
- **Section:** HLD §8 (lines 244-270), VISION §9 (complete tree)
- **Problem:** §8's document tree omits `10-agent-types.md`, `20-rag-interface.md`, `21-three-tier-agent-testing-methodology.md`, and lists only `examples/mortgage-lead/` (not `home-insurance/` or `cicd/`). §5 "Related Design Documents" is complete, so §8 is just stale.
- **Proposed Fix:** Sync §8 with VISION §9 (add the 3 missing specs + home-insurance + cicd examples).
- **Severity:** LOW

### ISSUE-52: correctness — HLD Appendix has duplicate "A.5" numbering
- **Type:** correctness
- **Section:** HLD Appendix A.5 (line 310 "Deployment & Operations"), A.5 (line 318 "Reference Implementation")
- **Problem:** Two appendix subsections share the number A.5.
- **Proposed Fix:** Renumber the second to A.6.
- **Severity:** LOW

### ISSUE-53: completeness — HLD §5 Related Docs lists mortgage-lead examples but not home-insurance
- **Type:** completeness
- **Section:** HLD §5 (line 212)
- **Problem:** §5 lists "Mortgage Lead Examples" but omits the home-insurance example set that state-machine §2/§4/§6 reference.
- **Proposed Fix:** Add a "Home Insurance Examples" bullet.
- **Severity:** LOW

### ISSUE-54: correctness — Domain-model changelog 0.5.0 row has trailing empty table cells
- **Type:** correctness
- **Section:** domain-model Changelog (line 16: `… x- extensions | |`)
- **Problem:** The 0.5.0 row ends with `| |` (an extra empty column), breaking the table grid.
- **Proposed Fix:** Remove the trailing `| |`.
- **Severity:** LOW

### ISSUE-55: clarity — State-machine §1.1 labels Option A "Current Approach" but the default recommendation is Option C
- **Type:** clarity
- **Section:** state-machine §1.1 (line 68 "Option A: YAML-Only Declarative (Current Approach)"), §1.1 end (line 226 "Default recommendation: Option C")
- **Problem:** Option A is tagged "(Current Approach)" implying it's the live one, but the default is Option C. Confusing for a new reader.
- **Proposed Fix:** Drop "(Current Approach)" from Option A or replace with "(Simple workflows)".
- **Severity:** LOW

### ISSUE-56: clarity — State-machine mixes home-insurance and mortgage-lead example references within one spec
- **Type:** clarity
- **Section:** state-machine §2 (line 234 home-insurance workflow.yaml), §3.2 (line 301 mortgage-lead workflow.yaml), §4 (line 465 home-insurance), §6 (line 547 home-insurance)
- **Problem:** The spec bounces between two example domains. intent-classification §3.1 acknowledges the dual-domain phase names, but state-machine does not, so a reader assumes a single domain.
- **Proposed Fix:** Add a one-line note at the first example pointing to intent-classification §3.1's domain-vocabulary clarification, or pick one domain per spec.
- **Severity:** LOW

### ISSUE-57: correctness — Response-gen goal example duplicates `rate_calculation` and has space-in-field-name typos
- **Type:** correctness
- **Section:** response-generation §2.2 (lines 81-82 `expected_outputs: ["rate_calculation", "rate_calculation", "quote"]`, `expected_entities: […, "loan amount_needs"]`), §2.4 (line 123 same duplicate), §3.3 (lines 260, 287 `loan amount_type`)
- **Problem:** `rate_calculation` listed twice in `expected_outputs`; field names contain spaces ("loan amount_needs", "loan amount_type") which are invalid as identifiers.
- **Proposed Fix:** Deduplicate `rate_calculation`; replace spaces with underscores (`loan_amount_needs`, `loan_amount_type`).
- **Severity:** LOW

### ISSUE-58: correctness — Response-gen eval case assigns an address to `loan_amount`
- **Type:** correctness
- **Section:** response-generation §3.3 (line 212 `entities: loan_amount: "123 Main St"`)
- **Problem:** The eval fixture sets `loan_amount` (a number) to an address string "123 Main St". Semantically wrong test data that would confuse anyone adapting the eval.
- **Proposed Fix:** Set `loan_amount: 500000` and `address: "123 Main St"`.
- **Severity:** LOW

### ISSUE-59: consistency — Response-gen §8.2 includes a Chinese-ID PII pattern in an English-only framework
- **Type:** consistency
- **Section:** response-generation §8.2 (line 586 `pattern: "\\b[0-9]{18}\\b" # Chinese ID number`), intent-classification §5.6 (English-only, cross-lingual deferred), §9.6 open question
- **Problem:** The framework is English-only (§5.6), yet a Chinese national-ID regex is baked into the PII rules. §9.6 even lists "Chinese ID vs US SSN" as an open question, so including the pattern pre-decides it.
- **Proposed Fix:** Replace with a US SSN pattern as the default example and move the Chinese-ID pattern to the open-questions section as a future i18n case.
- **Severity:** LOW

### ISSUE-60: correctness — Agent-types changelog lists 0.2.0 before 0.1.0
- **Type:** correctness
- **Section:** agent-types Changelog (lines 12-13)
- **Problem:** Versions are out of chronological order (0.2.0 above 0.1.0).
- **Proposed Fix:** Reorder so 0.1.0 is first.
- **Severity:** LOW

### ISSUE-61: correctness / consistency — RAG-interface uses `RAGResult` before definition; RAG consumer is ambiguous (ResponseGenerator vs ReadOnlyAgent)
- **Type:** correctness / consistency
- **Section:** rag-interface §2.5 (line 229 `-> RAGResult` before definition at line 240), §3.1 (line 257 ResponseGenerator calls RAGPipeline), agent-types §2.1 (ReadOnlyAgent "backend: A RAG pipeline")
- **Problem:** `RAGPipeline.query` references `RAGResult` before it's defined (would NameError without `from __future__ import annotations`). Separately, §3.1 says the ResponseGenerator (Layer 3) calls RAGPipeline, but agent-types says ReadOnlyAgent is the RAG backend. Two different consumers claimed for the same pipeline.
- **Proposed Fix:** Add `from __future__ import annotations` (or move `RAGResult` above `RAGPipeline`). Clarify that ReadOnlyAgent wraps RAGPipeline and ResponseGenerator consumes the ReadOnlyAgent result (not RAG directly).
- **Severity:** LOW

### ISSUE-62: correctness — Widget-templates uses `loan_amount_amount` (doubled word) as a field name
- **Type:** correctness
- **Section:** widget-templates §3.2 (lines 289, 334, 356)
- **Problem:** Input field name `loan_amount_amount` repeats "amount"; propagated through validation and catalog.
- **Proposed Fix:** Rename to `loan_amount`.
- **Severity:** LOW

### ISSUE-63: correctness — LLM-gateway §5 has a "5.4 Comparison Matrix" with no §5.1-5.3; §6.1 example confidence `minimum:0` disables the gate
- **Type:** correctness / clarity
- **Section:** llm-gateway §5 (Options A-D directly under §5, then "### 5.4 Comparison Matrix" line 731), §6.1 (line 758 `"minimum": 0`), §3.5 (line 263 "minimum of 0 … effectively disables the gate")
- **Problem:** §5 jumps straight to options then "5.4" with no 5.1-5.3. §6.1's example schema sets confidence `minimum: 0`, which per §3.5 disables the confidence gate — contradicting §3.5's own `minimum: 0.7` examples.
- **Proposed Fix:** Renumber the matrix (e.g., §5.5) or add §5.1-5.3. Set §6.1's confidence `minimum` to 0.7 to match §3.5, or note it's a disabled-gate example.
- **Severity:** LOW

### ISSUE-64: consistency — A2A error.category enum omits `unrecoverable_error` (routing defines 7 categories, A2A lists 6)
- **Type:** consistency
- **Section:** a2a-protocol §2.2 (line 128 `category: llm_error | api_error | tool_error | validation_error | permission_error | business_rule_error`), routing §6.4 (7 categories, adds `unrecoverable_error`)
- **Problem:** A2A's error category enum is missing `unrecoverable_error`, so an agent can't propagate that category cross-agent.
- **Proposed Fix:** Add `unrecoverable_error` to the A2A enum and cross-reference routing §6.4.
- **Severity:** LOW

### ISSUE-65: correctness — Extraction §3.6 guardrail conflates AgentState top-level fields with `collectedFields` keys
- **Type:** correctness
- **Section:** extraction-layer §3.6 (lines 389-397: "whitelist derived from `AgentState.__dataclass_fields__`", example set contains `loan_purpose`, `address`, …)
- **Problem:** The guardrail says it validates field names against `AgentState.__dataclass_fields__`, but `loan_purpose`/`address` are keys inside `collectedFields` (a dict), not top-level AgentState fields. The example set and the described derivation source don't match.
- **Proposed Fix:** Describe the whitelist as "the union of all field names across the bound entities' OpenAPI schemas (the keys allowed in `collectedFields`)", not `AgentState.__dataclass_fields__`.
- **Severity:** LOW

### ISSUE-66: consistency — Three-tier-testing claims "industry-agnostic" but uses mfangdai-specific DB names and an undefined "payment gate"
- **Type:** consistency / completeness
- **Section:** three-tier-testing line 6 ("Industry-agnostic"), §11 (lines 571, 580-582 `mfangdai_t1.db`), §5.6 (line 399 "payment gate prompt"), HLD Appendix A.5 (line 336 "$35 payment gate")
- **Problem:** The methodology claims industry-agnosticism but hardcodes `mfangdai_t*.db` filenames and references a "payment gate" / "$35" concept defined nowhere in the spec suite (only in the mfangdai production notes). Adopters of a different domain have no spec basis for the payment gate.
- **Proposed Fix:** Replace `mfangdai_t*.db` with `{project}_t*.db` placeholders. Either define the payment-gate/privacy-relay pattern as a generic spec concept or remove it from the methodology and reference it as a domain-specific example.
- **Severity:** LOW


---

## Examples vs Specs Consistency

**home-insurance/** — Follows the spec patterns well overall: the e2e scenarios correctly demonstrate the extraction spec's parallel two-LLM (narrow + broad) merge-by-confidence, the `fieldExtractedList` / `collected_fields` DomainModel invariant, guard-based routing, and human-in-the-loop interrupt. `workflow.yaml` follows state-machine §3.3 field reference (precondition/entry_guard/data_invariant/exit_guard/postcondition/context_schema) and uses the spec's top-level `transitions:` layout. **Gaps:**
- Uses custom `error_recovery`/`claim_error_recovery` states instead of canonical `errorNode` (ISSUE-20).
- `intent-definitions.md` IntentDef schema omits the `complex` field and describes `keywords` as "deterministic fallback patterns" — contradicting intent-classification §2.3 ("metadata only, not used in runtime") (related to ISSUE-2/ISSUE-12).
- e2e Scenario 1/4 have numeric and math inconsistencies (ISSUE-17).
- `workflow.yaml` guard `intent == 'get_quote'` uses `intent` as a variable, but `intent` is not in state-machine §3.3's meta-variable list (`exit_guard_pass`, `context_complete`, …). Either add `intent` to the meta-variables or route via `intent_policy`.
- Edge cases the specs promise but the examples don't cover: concurrent-access/parallel-node merge (routing §1.2), `errorNode` strategy selection, multi-intent-per-message (intent §4.2), and sub-workflow invocation — none appear in the home-insurance e2e.

**mortgage-lead/** — Aligns with intent-classification §5.2 agent dispatch (`check_rates → ReadOnlyAgent`) and demonstrates OAuth (Keycloak), rate-limiting (chitchat exhaustion), and daily-budget (HTTP 500) scenarios that tie to llm-gateway §4.1a and rate-limiting. **Gaps:**
- `intent-definitions.md` marks all write intents `Complex: No` (should be `true`) and lists only 7 of 17 system intents (ISSUE-12); payload field casing is camelCase while domain-model §2.2 uses snake_case — inconsistent entity-field convention.
- `workflow.yaml` uses inline per-state `transitions:` instead of the spec's top-level `transitions:` (ISSUE-14); states declare no `intent_policy` (state-machine §8.2) and no `on_error: errorNode` wiring.
- e2e Scenario 7 uses `small_talk` instead of the canonical `chitchat` (ISSUE-19).
- `README.md` references `../../domain-models/mortgage-lead.yaml` (verified to exist) — link is valid; good.

**cicd/hetzner-jenkins.md** — Clean, self-contained, explicitly labeled "example — not part of the generic framework spec." Aligns with cicd spec §10 and the Tier 1/2/3 testing methodology. Minor: `server_type = "cx32"` may not be a current Hetzner flavor; Jenkinsfile uses `mfangdai_t2.db` (project-specific, acceptable in an example). No spec contradictions.

**Cross-cutting example gaps:** No example demonstrates (a) the A2A/sub-workflow invocation with return-stack, (b) the LLM-gateway model-escalation chain, (c) multi-intent-per-message extraction producing multiple `ExtractedIntentPayload`s, or (d) the `errorNode` strategies in action. The specs describe all four; the examples demonstrate none. Adding at least one e2e scenario per feature would close the spec↔example loop.

---

## Top Recommendations (priority order)

1. **Reconcile the four cross-spec contradictions on shared schemas**: unify `IntentDef` (ISSUE-2), `AgentState` + `phase_stack` (ISSUE-5), `check_rates` routing (ISSUE-4), and the errorNode strategy enum (ISSUE-16). These are the highest-leverage fixes — each resolves a family of downstream inconsistencies.
2. **Fix the three internal contradictions**: intent-classification Option B vs removed keyword fallback (ISSUE-1), routing append-only vs configurable reducers (ISSUE-3), and llm-gateway duplicate/env-defaults sections (ISSUE-13).
3. **Complete the extraction spec's Option B/C descriptions** (ISSUE-15) — currently the "≥2 options per interface" VISION requirement is met only on paper.
4. **Unify the two example `workflow.yaml` schema styles** (ISSUE-14) and fix the mortgage-lead `complex` flags (ISSUE-12) so the examples are valid against the spec loader and the multi-intent rules.
5. **Resolve the widget domain confusion** (ISSUE-6) and remove insurance leftovers ("Claims operations", `deductible`/`policy_end_date`) so the mortgage-lead unification is actually complete.
6. **Enforce English-only in CI** (ISSUE-11) and add a YAML/JSON-Schema linter for schema examples (catches ISSUE-9, ISSUE-22, ISSUE-26, ISSUE-54, ISSUE-57).
7. **Align metric names and thresholds** across observability/conversation-lifecycle/cicd (ISSUE-10, ISSUE-30, ISSUE-47, ISSUE-37) so dashboards/alerts/rollback share one vocabulary.
8. **Reconcile intent labels** (`small_talk`/`greeting`/`greet` → `chitchat`/`start_conversation`; `general_inquiry` status) across conversation-lifecycle, examples, and three-tier-testing (ISSUE-18, ISSUE-19).

