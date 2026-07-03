# Final Review Summary — 2026-06-24 All Specs Adversarial Review

**Date:** 2026-06-24
**Scope:** 21 English spec files in `docs/specs/` + 7 example files in `docs/examples/` + `docs/VISION.md`
**Method:** Mode 2 Full Adversarial Review (3 independent agents → debate → judge)

---

## Review Statistics

| Metric | Value |
|--------|-------|
| Documents reviewed | 29 files (15,556 lines) |
| Agents launched | 3 (Agent 0: Vision, Agent 1: Web-Search, Agent 2: Cross-Model) |
| Total issues raised | 136 |
| Unanimously agreed (no debate) | 126 |
| Debated issues | 10 |
| Judge rulings: ACCEPT | 7 |
| Judge rulings: COMPROMISE | 3 |
| Judge rulings: REJECT | 0 |

### Issues by Severity (after judge reconciliation)

| Severity | Count | Examples |
|----------|-------|----------|
| CRITICAL | 11 | Chinese text in specs, IntentDef schema conflict, keyword fallback contradiction, PII circular ownership, routing append-only contradiction, check_rates 4-way routing |
| HIGH | 35 | Widget domain mix, LLM gateway broken sections, model escalation conflation, A2A outdated, MCP obsolete transport, Temporal missing, token budget naive, Instructor missing |
| MEDIUM | 45 | Extraction Option B/C undocumented, metric naming drift, schema type inconsistencies, env-config contradictions |
| LOW | 25 | Stale year, ASCII misalignment, doubled words, changelog ordering |

---

## Top 10 Priority Fixes (Judge-Ordered)

1. **Replace Chinese `举一反三` in 2 spec files** — trivial, CI-enforceable, violates VISION §10. Add `rg '[一-龥]' docs/specs/` CI check.

2. **Unify `IntentDef` schema** — domain-model §5.1 must match intent-classification §2.3 (add `complex`, `keywords`, `entry_state`, `fallback_intent`). Update both examples. This is CRITICAL — two incompatible schemas for one concept.

3. **Restore keyword cascade as Layer 0** in intent-classification — undo v0.6.0 over-correction. Restore `"keyword"` to `source` enum. Cascade: keyword/regex (≥0.95 confidence, $0) → LLM → `unrecognized_intent`. Aligns with VISION §6.2 and 2026 industry consensus.

4. **Fix PII rules circular ownership** — domain-model owns `x-pii` declarations, response-gen §8 owns processing pipeline. Add 3-layer pipeline (regex → Presidio NER → contextual LLM). Add OpenAI Privacy Filter to tool catalog.

5. **Fix routing append-only contradiction** — audit fields = append-only locked, business fields = configurable (append default). Remove "not configurable" absolute language.

6. **Reconcile `check_rates` 4-way routing** — pick one canonical routing across intent-classification, agent-types, extraction, domain-model. Create single "intent → agent → entry_state" table.

7. **Fix widget-templates domain mix** — remove all insurance terminology (`deductible`, `policy_end_date`, "HOME INSURANCE CHAT") from the mortgage spec.

8. **Split model escalation into reliability + quality layers** — separate provider failover from cost-quality routing. Document cost formula. Add escalation_rate SLO alert. Update AD 31.

9. **Align A2A spec with v1.0** — replace custom Agent Registry with Agent Cards at `/.well-known/agent-card.json`. Adopt official `message/send` + Task lifecycle. Reference official SDKs.

10. **Add Temporal as optional durable execution layer** — revise AD 1 to "Python + LangGraph + optional Temporal." Add to routing §5.4 for side-effecting async sub-workflows.

---

## Architectural Recommendations (from Agent 1 web evidence)

| # | Recommendation | Rationale | Impact |
|---|----------------|-----------|--------|
| AR1 | Add Instructor as recommended LLM gateway implementation | 3M+ downloads, 15+ providers, de-facto Python standard | Reduces framework code, adopts industry standard |
| AR2 | Make broad-scope extraction conditional (not parallel every turn) | Industry multi-pass is for recall (same schema), not scope division | Halves LLM cost on every turn |
| AR3 | Revise SCXML rationale — drop "W3C standard" compliance claim | SCXML executable content rejected in mapping; no auditor named | Removes unfalsifiable compliance assertion |
| AR4 | Fix OpenAPI 3.1 rationale — Draft 2020-12 is canonical, not "less mature" | LLM providers support JSON Schema subset, not OpenAPI extensions | Aligns rationale with reality |
| AR5 | Replace HTTP 500 budget kill-switch with staged warn→throttle→reject | Industry uses per-user/per-team granularity, not global stop | Prevents availability footgun |
| AR6 | Add refusal handling to LLM gateway | OpenAI Structured Outputs can refuse (safety); retrying is pointless | Prevents retry-budget waste |
| AR7 | Replace unmaintained rule engines with Pydantic validators | durable_rules/business-rules/pyknow are unmaintained; Pydantic already a dependency | Removes unmaintained deps |
| AR8 | Add LangGraph Functional API as alternative | `@entrypoint`/`@task` for simpler workflows | Developer ergonomics |
| AR9 | Reference 2026 testing SOTA (AgentAssay, TDAD, layer-isolated) | Stochastic test semantics, mutation testing, per-layer slice gates | Makes methodology defensible to auditors |
| AR10 | Add MCP v2 migration plan | MCP 2026-07-28 RC: stateless core, Streamable HTTP replaces SSE | Prevents foundation-on-quicksand |

---

## §7 Checklist Compliance Gaps

| Spec | Missing Items |
|------|---------------|
| HLD | 2+ options / comparison matrix (acceptable for root HLD) |
| three-tier-testing-methodology | changelog table, open questions, 2+ options, comparison matrix, references (labeled "Sources") |
| rag-interface | open questions, comparison matrix |
| agent-types | open questions |
| domain-model | 2+ options (partial), comparison matrix (partial) |
| extraction-layer | 2+ options (B/C undocumented), rationale (partial) |
| rate-limiting | 2+ options (partial), comparison matrix (partial) |
| tool-ecosystem | 2+ options (partial), rationale (partial) |

---

## Cross-Document Conflict Map

### Schema Conflicts (must unify)
- `IntentDef`: domain-model §5.1 vs intent-classification §2.3 (different fields)
- `AgentState`: canonical §10.1 missing `phase_stack`, `goal`, `goal_check_result`, `response`
- `errorNode` strategies: canonical enum vs short names in tool-ecosystem/a2a
- `lifecycle_state` enum: MCP §3.4 (6 values) vs domain-model §10.1 (7 values, adds `archived`)

### Naming Drift (must standardize)
- `small_talk`/`greeting`/`greet` → `chitchat`/`start_conversation`
- `submit_mortgage_lead` vs `submit_lead` 
- `Claims operations` (insurance leftover) → `Sensitive write operations`
- `distribute_lead`/`assign_lead`/`submit_lead` (overlapping concepts)
- `mfangdai-agent` vs `mfangdai-ai-agent`
- `general_inquiry` (not a system intent but used in evals)

### Domain Contamination (insurance → mortgage migration incomplete)
- widget-templates: `deductible`, `policy_end_date`, "HOME INSURANCE CHAT"
- rate-limiting: "Claims operations"
- response-gen: Chinese ID pattern in English-only framework

---

## Files Modified During Review

| File | Type |
|------|------|
| `docs/discussion/2026-06-24-all-specs-review.md` | Round file (created) |
| `docs/discussion/2026-06-24-agent0-vision-issues.md` | Agent 0 findings (50 issues) |
| `docs/discussion/2026-06-24-agent1-issues.md` | Agent 1 findings (20 issues) |
| `docs/discussion/2026-06-24-agent2-issues.md` | Agent 2 findings (66 issues) |
| `docs/discussion/2026-06-24-judge-rulings.md` | Debate transcripts + judge rulings (10 debates) |
| `docs/discussion/2026-06-24-review-summary.md` | This file |

**No spec files were modified during this review.** All findings and rulings are documented in `docs/discussion/`. The user should review the judge rulings and decide which modifications to apply to the spec files.

---

## Next Steps

1. **Review the judge rulings** in `2026-06-24-judge-rulings.md` — all 10 debates resolved, 7 ACCEPT + 3 COMPROMISE
2. **Apply Priority Fixes 1-10** (listed above) to the spec files — these are the highest-leverage changes
3. **Decide on Architectural Recommendations AR1-AR10** — these require updating VISION.md ADs (1, 28, 29, 30, 31, 33) and several spec files
4. **Run the §7 checklist compliance gaps** — add missing sections to three-tier-testing, rag-interface, agent-types
5. **Fix cross-document schema conflicts** — unify IntentDef, AgentState, errorNode strategies, lifecycle enum
6. **Complete the insurance→mortgage domain migration** — widget-templates, rate-limiting, response-gen
7. **Add CI checks**: CJK character detection, YAML/JSON Schema validation, cross-reference validation

---

## Open Concerns (deferred for later)

- No spec defines the **Spec Generator Skill** interview templates (VISION §3.3) — flagged as missing coverage
- No spec addresses **multi-tenant workflow isolation** — HLD Appendix A.5 Q13 lists it as open but no spec owns the design
- No spec defines **blue-green / version migration of in-flight conversations** — HLD A.5 Q12 open, no canonical approach
- **Multilingual roadmap** missing — English-only NLU but multilingual PII regex already exists; no migration path
- **Context hydration enforcement mechanism** missing — "selective load" is aspirational, not enforceable
