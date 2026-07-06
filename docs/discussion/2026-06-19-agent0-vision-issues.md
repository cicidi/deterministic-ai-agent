# Agent 0 — Vision Alignment + Cross-Document Review

**Date:** 2026-06-19
**Reviewer:** Agent 0 (Vision enforcer)
**Scope:** VISION.md + HLD + implement-interview SKILL.md + auto-tdd stub/full SKILL.md + contrarian-review SKILL.md + mfangdai PRD.md + GAPS.md

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 7 |
| HIGH | 11 |
| MEDIUM | 10 |
| LOW | 7 |
| **TOTAL** | **35** |

---

## CRITICAL (7)

### ISSUE-1: vision_violation — implement-interview generates code, violating VISION §4.1 "No implementation code yet"

- **Type:** vision_violation
- **Documents:** VISION.md:72, implement-interview/SKILL.md:16, implement-interview/SKILL.md:232-256
- **Problem:** VISION.md §4.1 states "No implementation code yet. Spec-first." This is the first and most emphatic "Never" rule. The implement-interview skill declares itself "upgraded to produce code instead of documents" (line 16) and Phase 6 (lines 232-256) generates a runnable Python project with `src/`, `tests/`, `main.py`. This directly contradicts the Vision's current phase: specs are the deliverable; Python reference implementation is marked "not yet started" (line 28).
- **Proposed Fix:** Either (a) update VISION.md to reflect that the phase has advanced to code generation, updating §4.1, §3.3, and the deliverables table; OR (b) strip code generation from implement-interview and restore it to spec-generation only (as the original spec-generator).
- **Severity:** CRITICAL

### ISSUE-2: semantic_conflict — implement-interview redefines the "spec-generator" deliverable

- **Type:** semantic_conflict
- **Documents:** VISION.md:26-28, VISION.md:62-64, implement-interview/SKILL.md:16
- **Problem:** VISION.md deliverables table defines "Spec Generator Skill" as a "downstream tool" that "interviews a developer and outputs a product-specific spec" (line 27). implement-interview claims "This skill IS the `spec-generator` from VISION.md, upgraded to produce code instead of documents" (line 16). The deliverable changed from "output a spec" to "output code" — a fundamental scope change that conflicts with the Vision's current phase statement.
- **Proposed Fix:** Align VISION.md deliverables table and implement-interview description. If the Vision has evolved to include code generation, update VISION.md §3.2 and §4.1. If not, rename implement-interview's claim to reflect its true role (code generator, NOT spec-generator).
- **Severity:** CRITICAL

### ISSUE-3: version_skew — VISION.md says Python ref impl "not yet started" but HLD maps it

- **Type:** version_skew
- **Documents:** VISION.md:28, HLD:14 (v0.10.0), HLD:273 (Appendix A.5)
- **Problem:** VISION.md line 28 marks "Python Reference Implementation" as "Code (future) | Proves feasibility; not yet started." But HLD v0.10.0 (line 14, dated 2026-06-19) added "reference implementation mapping (mfangdai-agent) — see Appendix B" and Appendix A.5 (lines 319-339) maps every spec concept to concrete mfangdai-agent source files. The HLD treats the reference implementation as existing and mapped; the Vision says it hasn't started. Only one can be true.
- **Proposed Fix:** Update VISION.md §3.3 deliverables table: change Python Reference Implementation status from "not yet started" to "mfangdai-agent (MVP built, 64 tests)" and add a cross-reference to HLD Appendix A.5. Or revert HLD v0.10.0 if mfangdai-agent is not yet accepted as the reference implementation.
- **Severity:** CRITICAL

### ISSUE-4: missing_cross_ref — VISION.md document tree missing `14-llm-gateway.md`

- **Type:** missing_cross_ref
- **Documents:** VISION.md:218-240 (document tree), HLD:199, implement-interview/SKILL.md:38
- **Problem:** Both HLD §5 (line 199) and implement-interview prerequisites (line 38) reference `docs/specs/14-llm-gateway.md` as a spec document. The file exists on disk. But VISION.md's document tree (lines 218-240) does NOT list `14-llm-gateway.md`. This means the Vision's own document tree — the "authoritative reference" — is incomplete. implement-interview's Strategy Defaults table (line 148) references `llm-gateway §3`, so the omission cascades.
- **Proposed Fix:** Add `14-llm-gateway.md` to VISION.md's document tree at line 238 (alphabetically, between `intent-classification` and `mcp-api-protocol`). Also add `12-a2a-protocol.md` and `11-mcp-api-protocol.md`, `16-auth-token-verification.md`, and `07-conversation-lifecycle.md` — all are listed in HLD's tree (lines 249-265) but missing from VISION.md's tree.
- **Severity:** CRITICAL

### ISSUE-5: vision_violation — mfangdai-agent does not use LangGraph, violating AD1

- **Type:** vision_violation
- **Documents:** VISION.md:89 (AD1), PRD.md:341
- **Problem:** VISION AD1: "Python + LangGraph. LangGraph provides state graph, checkpoint, streaming; Python has strongest ecosystem." PRD line 341 states: "Custom LangGraph-style agent loop (no LangGraph dependency)." GAPS.md line 349 already flags this as a "Deviation." This is a direct violation of the framework's foundational technology decision. A "custom LangGraph-style loop" loses checkpoint, streaming, state graph visualization, and the LangGraph ecosystem (LangSmith, LangGraph CLI).
- **Proposed Fix:** Replace the custom state machine loop with actual LangGraph `StateGraph`. If the decision is to NOT use LangGraph, update AD1 in VISION.md with a revised decision and rationale. Until then, this is a spec non-conformance.
- **Severity:** CRITICAL

### ISSUE-6: missing_coverage — GAPS.md Spec Compliance Checklist doesn't check VISION Architecture Decisions

- **Type:** missing_coverage
- **Documents:** VISION.md:87-122 (33 ADs), GAPS.md:330-349 (Spec Compliance Checklist)
- **Problem:** GAPS.md's "Spec Compliance Checklist" (15 rows) checks the mfangdai-agent against patterns from the HLD/framework spec only. It does NOT check against any of the 33 Architecture Decisions in VISION.md. The following VISION ADs have NO corresponding check in GAPS.md and NO evidence of implementation or non-implementation status: AD5 (per-node control), AD14 (goal-driven workflow), AD17 (serial/parallel/mixed sub-workflow nodes), AD18 (two response modes), AD19 (node loop-back), AD22 (two-stage classify+extract), AD23 (multi-intent + complex flag), AD28 (SCXML), AD29 (OpenAPI 3.1 Schema), AD30 (multi-pass extraction), AD31 (progressive model escalation), AD32 (cheap model by default), AD33 (daily token budget).
- **Proposed Fix:** Add a "VISION.md Architecture Decision Compliance" table to GAPS.md, listing all 33 ADs with implementation status (OK / Partial / GAP / N/A). Or, in a Mode 2 contrarian review, generate a separate VISION-compliance gap report.
- **Severity:** CRITICAL

### ISSUE-7: semantic_conflict — PRD claims LangChain framework, contradicting AD1 (LangGraph)

- **Type:** semantic_conflict
- **Documents:** VISION.md:89 (AD1), PRD.md:340-341
- **Problem:** PRD line 340 lists "Framework: LangChain (ChatOpenAI)" and line 341 says "Custom LangGraph-style agent loop (no LangGraph dependency)." VISION AD1 mandates LangGraph as the runtime substrate. PRD says "LangChain" — a different library (LangChain is the broader ecosystem; LangGraph is the state graph library). The PRD is using LangChain's `ChatOpenAI` wrapper, not LangGraph's `StateGraph`. This is a fundamental technology inconsistency between the vision and the implementation.
- **Proposed Fix:** Replace `LangChain (ChatOpenAI)` with the LLM Gateway pattern from the framework spec. Use LangGraph's `StateGraph` for the state machine. Update PRD line 340 accordingly.
- **Severity:** CRITICAL

---

## HIGH (11)

### ISSUE-8: naming_drift — "spec-generator" in VISION vs "implement-interview" as skill name

- **Type:** naming_drift
- **Documents:** VISION.md:27 ("Spec Generator Skill"), VISION.md:63 ("downstream Spec Generator Skill"), implement-interview/SKILL.md:1 (name: implement-interview), HLD:214-215 ("skill-assisted spec generation", "downstream skill")
- **Problem:** The Vision consistently names this deliverable "Spec Generator Skill." The HLD uses "Skill-Assisted Spec Generation" and "downstream skill." The actual skill is named "implement-interview" — a term that appears nowhere in VISION.md or the HLD. Multiple naming chains for the same concept: VISION says it outputs specs; HLD says it outputs specs; the skill says it outputs code. Different names for the same concept create confusion about what this skill does.
- **Proposed Fix:** Decide on one canonical name. If the skill generates specs: rename to "spec-generator." If it generates code: update VISION.md and HLD to reflect the new name and purpose. Document the name in VISION.md §3.3.
- **Severity:** HIGH

### ISSUE-9: duplication — Completeness Verification (implement-interview) overlaps Anti-Stall Protocol (auto-tdd)

- **Type:** duplication
- **Documents:** implement-interview/SKILL.md:152-189, ai-coworker-auto-tdd/SKILL.md:248-260
- **Problem:** implement-interview defines a 7-step "Completeness Verification" phase (lines 152-189) with checks for requirement-to-spec traceability, artifacts discovery, multi-party interaction, privacy, testing requirements, output format, and completeness self-audit. auto-tdd defines a 7-row "Anti-Stall Protocol" table (lines 251-259) covering similar concerns: not declaring done too early, not missing tests, not skipping quality review, not dropping user requirements, etc. Both serve the same purpose — preventing premature "done" declarations — but use different checklists, different terminology, and don't reference each other.
- **Proposed Fix:** Extract the common concern into a single "completeness verification" protocol in one location. Have both skills cross-reference it. The contrarian-review Mode 1 flow already partially addresses this — make it the canonical gate and remove the duplicated checklists.
- **Severity:** HIGH

### ISSUE-10: duplication — Contrarian review final gate defined in 3 places

- **Type:** duplication
- **Documents:** implement-interview/SKILL.md:191-206, ai-coworker-auto-tdd/SKILL.md:274, ai-coworker-contrarian-review/SKILL.md:67-99
- **Problem:** The "final gate = contrarian review → GAPS.md" flow is defined in three documents:
  1. implement-interview lines 191-206: describes GAPS.md flow with developer decision steps (fix now / defer / accept risk)
  2. auto-tdd line 274 (Rule 11): "Contrarian review is the final gate... writes GAPS.md... If gaps exist, they become new tasks"
  3. contrarian-review SKILL.md lines 67-99: defines Mode 1 with full GAPS.md template and severity categorization
  implement-interview duplicates the GAPS.md logic (lines 196-206) instead of simply cross-referencing the contrarian-review skill. The template in contrarian-review (lines 78-99) is more structured than implement-interview's prose version.
- **Proposed Fix:** Make ai-coworker-contrarian-review the single canonical source for the GAPS.md template and final gate flow. implement-interview and auto-tdd should cross-reference it with a single line: "Invoke ai-coworker-contrarian-review Mode 1 (see that skill for details)." Remove the inline GAPS.md flow descriptions from both skills.
- **Severity:** HIGH

### ISSUE-11: missing_cross_ref — implement-interview references `llm-gateway §3` but llm-gateway missing from Vision tree

- **Type:** missing_cross_ref
- **Documents:** implement-interview/SKILL.md:148, VISION.md:218-240
- **Problem:** implement-interview's Strategy Defaults table (line 148) references `llm-gateway §3` for the LLM Gateway strategy default. The file exists (docs/specs/14-llm-gateway.md), but it is absent from VISION.md's authoritative document tree. A new developer following the Vision tree would have no way to locate this prerequisite.
- **Proposed Fix:** Same as ISSUE-4 — add `14-llm-gateway.md` to VISION.md's document tree.
- **Severity:** HIGH

### ISSUE-12: missing_coverage — mfangdai-agent PRD missing AD14 (goal-driven workflow) and AD19 (node loop-back)

- **Type:** missing_coverage
- **Documents:** VISION.md:102 (AD14), VISION.md:107 (AD19), PRD.md
- **Problem:** VISION AD14 mandates "Goal-driven workflow: Async goal set at start; parallel goal check at end; 422 on large gap." VISION AD19 mandates "Node loop-back: Self-correction: detect incomplete → return to earlier node." Neither concept appears in the PRD's architecture section (lines 167-235), feature list (lines 239-267), or test coverage (lines 270-330). GAPS.md does not flag either gap.
- **Proposed Fix:** Add goal-driven workflow (async goal setting on workflow entry, goal checking before completion) to the PRD's architecture section. Add node loop-back as an explicit framework capability. If these are deferred, add them to PRD §8 "Out of Scope" or "Next Steps."
- **Severity:** HIGH

### ISSUE-13: vision_violation — mfangdai-agent YAML configs are documentary, not runtime (violates AD26)

- **Type:** vision_violation
- **Documents:** VISION.md:114 (AD26), GAPS.md:322-326 (L14), PRD.md:346
- **Problem:** VISION AD26: "YAML as single source of truth for workflow definition; Python functions registered by name and referenced from YAML; framework startup validates all name bindings resolve (drift detection)." GAPS.md L14 (lines 322-326) documents: "The three YAML config files are loaded by... nothing. They are documentation artifacts, not runtime configuration." `workflow.yaml` specifies models and strategies but no code reads them. `intents.yaml` lists 7 intents but `classify.py` hardcodes 14. `domain_model.yaml` defines transitions but `state_machine.py` hardcodes its own. This is a direct violation of AD26's core premise.
- **Proposed Fix:** Implement a `ConfigLoader` class that reads YAML files at startup and wires them into runtime behavior. Or add a CI validation step that asserts code constants match YAML definitions. Until one of these is done, the YAML files are misleading.
- **Severity:** HIGH

### ISSUE-14: vision_violation — mfangdai-agent missing per-node permission enforcement (violates AD12)

- **Type:** vision_violation
- **Documents:** VISION.md:100 (AD12), GAPS.md:335, PRD.md:4.4 (AgentState)
- **Problem:** VISION AD12: "Two-level permission model: Config-level (YAML allowlists) + OAuth/role-based (runtime)." GAPS.md line 335 flags this as GAP (under C1). The PRD's AgentState (lines 222-235) has `user_type` but no permission check gates. PRD features #22 (line 262) describes "Error escalation" but not permission enforcement. This is a framework-level requirement that is entirely absent from the reference implementation.
- **Proposed Fix:** Add `allowed_tools` and `allowed_transitions` per-node YAML declarations. Implement a `PermissionEnforcer` that checks these at node entry. Wire OAuth scopes from context hydration.
- **Severity:** HIGH

### ISSUE-15: missing_cross_ref — implement-interview doesn't reference auto-tdd; only auto-tdd references implement-interview

- **Type:** missing_cross_ref
- **Documents:** implement-interview/SKILL.md, ai-coworker-auto-tdd/SKILL.md:68
- **Problem:** auto-tdd explicitly mentions implement-interview: "Used as the final gate in auto-tdd and implement-interview loops" (line 68). But implement-interview has no reciprocal reference to auto-tdd. These skills are designed to work together (contrarian-review as the shared final gate), yet implement-interview's "Related skills" or "See also" section doesn't exist. A developer discovering implement-interview would never know auto-tdd exists.
- **Proposed Fix:** Add a cross-reference section to implement-interview: "After code generation, use auto-tdd for continuous test-driven development with the 3-agent arbitration loop." Both skills should mutually reference each other and contrarian-review.
- **Severity:** HIGH

### ISSUE-16: semantic_conflict — implement-interview extract strategy default (hybrid) conflicts with AD30 (multi-pass)

- **Type:** semantic_conflict
- **Documents:** implement-interview/SKILL.md:141, VISION.md:118 (AD30)
- **Problem:** implement-interview's Strategy Defaults table (line 141) sets the extract strategy default to `hybrid` (LLM-first + deterministic fallback), referencing `extraction-layer-design §3.2`. But VISION AD30 (line 118, dated 2026-06-18) specifies: "Multi-pass per-state extraction scope. Pass 1: two parallel LLMs (narrow scope + broad scope). Pass 2: merge, cross-validate, and user confirmation (never silently merge guessed data)." The multi-pass approach with dual LLMs, cross-validation, and user confirmation is significantly more sophisticated than a simple "LLM-first + deterministic fallback" hybrid. The skill's default does not match the framework's latest architectural decision.
- **Proposed Fix:** Update implement-interview's Strategy Defaults table to reflect AD30: change extract strategy default from `hybrid` to `multi_pass` and add a note about the 2-pass parallel LLM + merge + cross-validate flow. Reference VISION.md AD30.
- **Severity:** HIGH

### ISSUE-17: missing_coverage — mfangdai-agent PRD does not implement AD26 (declarative field mutations)

- **Type:** missing_coverage
- **Documents:** VISION.md:115 (AD27), PRD.md
- **Problem:** VISION AD27: "Declarative field mutations (on_entry/on_exit/on_take.set_field). Every agentState field write is declared in YAML via lifecycle hooks — no hidden code mutations." The mfangdai-agent modifies `AgentState` fields imperatively in `state_machine.py` (e.g., `state.phase = "collecting_info"`, `state.collected_data.update(...)`) with no YAML declarations. GAPS.md doesn't flag this gap against AD27 specifically.
- **Proposed Fix:** Add declarative field mutation declarations to `config/domain_model.yaml` under each state transition. Or add this to PRD §8 "Next Steps" as a deferred framework compliance item.
- **Severity:** HIGH

### ISSUE-18: missing_cross_ref — HLD references "Appendix B" but actual section is "Appendix: Implementation Planning"

- **Type:** missing_cross_ref
- **Documents:** HLD:14 (line 14 changelog v0.10.0), HLD:273
- **Problem:** HLD changelog v0.10.0 (line 14) says "see Appendix B" but the appendix is labeled "Appendix: Implementation Planning — Open Questions" (line 273) with sub-section "A.5 Reference Implementation" (line 319). There is no "Appendix B" label anywhere in the document. This is a broken cross-reference — a developer searching for "Appendix B" would find nothing.
- **Proposed Fix:** Change changelog v0.10.0 to say "see Appendix A.5" instead of "see Appendix B."
- **Severity:** HIGH

---

## MEDIUM (10)

### ISSUE-19: naming_drift — "Error escalation" in PRD vs "errorNode" in VISION/HLD

- **Type:** naming_drift
- **Documents:** PRD.md:262, VISION.md:104 (AD15), HLD:131
- **Problem:** VISION AD15 (line 104) and HLD §4.1 (line 131) consistently use the term "errorNode" — "All errors → errorNode unified." PRD feature #21 (line 262) uses "Error escalation" and the implementation uses `_error_response`. GAPS.md uses "errorNode" in its compliance table (line 328) but the concept isn't named consistently across the ecosystem.
- **Proposed Fix:** Standardize on "errorNode" as the canonical term. Update PRD feature #21 name from "Error escalation" to "Unified errorNode." Update the handler function name to `_error_node` for consistency.
- **Severity:** MEDIUM

### ISSUE-20: naming_drift — "Phase-aware routing with return stack" present in HLD but not surfaced in PRD

- **Type:** naming_drift
- **Documents:** VISION.md:101 (AD13), HLD:131, PRD.md
- **Problem:** VISION AD13 and HLD §4.1 use the term "phase return stack" (tracking parent context when sub-workflows complete). The mfangdai-agent has `AgentState.return_stack: list[str]` (hydration.py:20) but GAPS.md L2 (line 251) notes it's "declared but never used." The PRD never mentions phase return stack or sub-workflow reuse. This framework pattern exists in the spec but has no concrete representation in the PRD.
- **Proposed Fix:** Either implement sub-workflow push/pop in the agent loop (and document in PRD §4.4), or add to PRD §8 as deferred. The `return_stack` field should not silently exist without documentation.
- **Severity:** MEDIUM

### ISSUE-21: naming_drift — "Completeness Verification" vs "Anti-Stall Protocol" vs "Quality Gates"

- **Type:** naming_drift
- **Documents:** implement-interview/SKILL.md:152 ("Completeness Verification"), ai-coworker-auto-tdd/SKILL.md:248 ("Anti-Stall Protocol"), ai-coworker-auto-tdd/SKILL.md:277 ("Quality Gates"), ai-coworker-contrarian-review/SKILL.md:70 ("Lightweight Verification Gate")
- **Problem:** Four different names for the same core concern (preventing premature "done" declarations) across three skills:
  - implement-interview: "Completeness Verification" (7 steps)
  - auto-tdd: "Anti-Stall Protocol" (failure mode table)
  - auto-tdd: "Quality Gates" (MUST/NICE checklist)
  - contrarian-review: "Lightweight Verification Gate" (Mode 1)
  These are semantically overlapping concepts with no shared terminology. A developer seeing all four would be confused about which to follow.
- **Proposed Fix:** Standardize terminology. Suggestion: "Completeness Gate" as the umbrella term, with "Anti-Stall Protocol" as the execution mechanism and "Quality Gates" as the checklist. Cross-reference the contrarian-review Mode 1 as the final verifier.
- **Severity:** MEDIUM

### ISSUE-22: duplication — GAPS.md template format differs between contrarian-review SKILL.md and actual mfangdai GAPS.md

- **Type:** duplication
- **Documents:** ai-coworker-contrarian-review/SKILL.md:78-99, mfangdai-ai-agent/GAPS.md:1-412
- **Problem:** The contrarian-review skill defines a GAPS.md template (lines 78-99) with sections: Summary, Critical, High, Medium, Low — each as a markdown table with columns `# | Gap | File | Fix`. The actual mfangdai GAPS.md uses a different format: numbered issues (C1-C8, H1-H9, M1-M14, L1-L14) with bullet-point details (Files, Gap, Impact, Fix). The actual file also adds Spec Compliance Checklist, Postman Use Cases, `.gitignore` issues, and Code Quality Notes — sections not in the template. This makes the template in the skill misleading — it doesn't match what the skill actually produces.
- **Proposed Fix:** Either (a) update the contrarian-review SKILL.md template to match the mfangdai GAPS.md format (which is more detailed and useful), or (b) constrain future GAPS.md outputs to match the template exactly. The template should reflect reality.
- **Severity:** MEDIUM

### ISSUE-23: missing_coverage — GAPS.md doesn't check against AD21 (3 environments), AD22 (two-stage classify+extract), AD23 (multi-intent)

- **Type:** missing_coverage
- **Documents:** VISION.md:108-110 (AD21, AD22, AD23), GAPS.md
- **Problem:** GAPS.md Spec Compliance Checklist (line 330) checks 15 spec patterns, but several core VISION ADs have no corresponding check:
  - AD21 (3 environments: dev/e2e/prod): PRD has `workflow.yaml` with a `dev` section and mentions `LLM_MODEL` env var, but GAPS.md has no formal check of environment separation.
  - AD22 (Two-stage classify+extract): mfangdai-agent co-extracts intent+entities in a single LLM call (PRD line 199: "Co-extracted with intent from the same LLM call"), violating AD22. GAPS.md doesn't flag this.
  - AD23 (Multi-intent per message + complex flag): PRD has no multi-intent support. GAPS.md doesn't flag this.
- **Proposed Fix:** Add these ADs to the GAPS.md Spec Compliance Checklist. For AD22 specifically, the co-extraction approach should be flagged as a deviation from the framework spec.
- **Severity:** MEDIUM

### ISSUE-24: semantic_conflict — mfangdai-agent co-extracts intent+entities in single call, violating AD22 (two-stage)

- **Type:** semantic_conflict
- **Documents:** VISION.md:109 (AD22), PRD.md:199
- **Problem:** VISION AD22: "Two-stage classify+extract (separate nodes). Accuracy > latency: scoped schema per extract call prevents cross-intent field confusion; single combined prompt with all schemas causes LLM to misroute fields between intents." PRD line 199: "Entity Extraction: Co-extracted with intent from the same LLM call." The PRD explicitly describes a single combined prompt approach that AD22 was specifically designed to prevent. The rationale in AD22 ("single combined prompt... causes LLM to misroute fields") is the exact pattern the PRD uses.
- **Proposed Fix:** Either (a) refactor mfangdai-agent to use separate classify + extract nodes per AD22, or (b) document this as a deliberate deviation in PRD with rationale, and update VISION.md to acknowledge that co-extraction may be an acceptable trade-off for certain workflows.
- **Severity:** MEDIUM

### ISSUE-25: vision_violation — mfangdai-agent uses co-extraction (single prompt) despite AD22 warning

- **Type:** vision_violation
- **Documents:** VISION.md:109 (AD22), PRD.md:199
- **Problem:** This is the same as ISSUE-24 but framed as a vision violation. AD22 explicitly says "single combined prompt with all schemas causes LLM to misroute fields between intents" — this is a strongly-worded architectural decision. The PRD ignores this warning and uses co-extraction. If the co-extraction works for the current scope, it should be acknowledged as a conscious deviation with justification.
- **Proposed Fix:** Same as ISSUE-24.
- **Severity:** MEDIUM

### ISSUE-26: missing_cross_ref — auto-tdd stub (skills/auto-tdd/SKILL.md) doesn't link to implement-interview

- **Type:** missing_cross_ref
- **Documents:** skills/auto-tdd/SKILL.md:1-24, ai-coworker-auto-tdd/SKILL.md
- **Problem:** The auto-tdd stub at `skills/auto-tdd/SKILL.md` is a reference stub pointing to the ai-coworker-auto-tdd skill. It describes the 3-agent TDD loop and mentions contrarian review as the final gate. But it never mentions implement-interview — even though auto-tdd is the natural next step after implement-interview generates code. The ai-coworker-auto-tdd full skill (line 68) correctly references implement-interview. The stub should too.
- **Proposed Fix:** Add a note to the stub: "Use after implement-interview to TDD the generated code to production quality."
- **Severity:** MEDIUM

### ISSUE-27: version_skew — implement-interview Strategy Defaults reference specific spec sections that may drift

- **Type:** version_skew
- **Documents:** implement-interview/SKILL.md:139-151, VISION.md ADs
- **Problem:** implement-interview's Strategy Defaults table (lines 139-151) pins specific section references: `extraction-layer-design §3.2`, `extraction-layer-design §4`, `routing-execution-layer-design §4`, `routing-execution-layer-design §5`, `routing-execution-layer-design §5.2`, `routing-execution-layer-design §6`, `llm-gateway §3`, `tool-ecosystem §3`. These section numbers will drift as spec documents evolve. There is no mechanism to detect broken cross-references. Already, `llm-gateway §3` (line 148) may not be aligned with the actual 14-llm-gateway.md content.
- **Proposed Fix:** Add a CI step that validates cross-references in skill files against spec documents. Use fuzzy matching if section numbers change. Or reference concepts by name instead of section number (e.g., "Response: default to pure_message, per response-generation-layer-design").
- **Severity:** MEDIUM

### ISSUE-28: missing_coverage — GAPS.md doesn't check AD22 violation (co-extraction), AD28 (SCXML), AD29 (OpenAPI 3.1)

- **Type:** missing_coverage
- **Documents:** VISION.md:109,115-116 (AD22, AD28, AD29), GAPS.md:330-349
- **Problem:** GAPS.md's Spec Compliance Checklist has no checks for:
  - AD22 (co-extraction vs two-stage) — PRD uses co-extraction, violating the AD
  - AD28 (SCXML as semantic standard) — No SCXML mapping in YAML definitions
  - AD29 (OpenAPI 3.1 Schema as data model standard) — Domain model uses custom YAML format, not OpenAPI Schema Objects
  - AD31 (Progressive model escalation) — Gateway has no provider/model escalation chain
  - AD32 (Cheap model by default) — Implementation defaults to `deepseek-v4-flash` (is this the "cheapest"?)
  - AD33 (Daily token budget) — No budget/cost calculator exists
- **Proposed Fix:** Expand the GAPS.md Spec Compliance Checklist to cover all 33 ADs. For each, mark status: OK / Partial / GAP / N/A (for ADs that don't apply to the MVP scope).
- **Severity:** MEDIUM

---

## LOW (7)

### ISSUE-29: semantic_conflict — implement-interview code generation structure doesn't match mfangdai-agent structure

- **Type:** semantic_conflict
- **Documents:** implement-interview/SKILL.md:238-256 (project structure), PRD.md (actual structure)
- **Problem:** implement-interview defines a generated project structure with `src/state_machine.py`, `src/executors/extract.py`, `src/executors/classify.py`, `src/executors/decide.py`, `src/executors/respond.py`, `src/gateway.py`, `src/hydration.py`. But the actual mfangdai-agent project — which was presumably built by an earlier version of this skill or manually — has a different layout: `src/state_machine.py` contains both routing and execution logic (849 lines), not the clean separation the skill describes. The skill claims all files will be ≤350 lines, but the actual agent's `state_machine.py` is 849 lines.
- **Proposed Fix:** Either (a) align the mfangdai-agent structure to match the generated template (split `state_machine.py` into routing + per-workflow handlers), or (b) update implement-interview's project structure to reflect the actual patterns used in practice.
- **Severity:** LOW

### ISSUE-30: naming_drift — "Rule engine" default in implement-interview doesn't match any actual usage

- **Type:** naming_drift
- **Documents:** implement-interview/SKILL.md:146, VISION.md:98 (AD10), GAPS.md
- **Problem:** implement-interview's Strategy Defaults table (line 146) sets "Rule engine" default to `durable_rules`, referencing `tool-ecosystem §3`. VISION AD10 also specifies "durable_rules as default rule engine." However, the mfangdai-agent PRD and codebase use no rule engine at all — validation is done imperatively in Python functions. The concept of "rule engine" is present in framework specs but absent in the reference implementation. GAPS.md doesn't flag this.
- **Proposed Fix:** Either add `durable_rules` (or business-rules) to the mfangdai-agent for entity validation, or remove the rule engine default from implement-interview's defaults and defer it with a note.
- **Severity:** LOW

### ISSUE-31: naming_drift — `intents.yaml` in implement-interview vs `config/intents.yaml` in mfangdai-agent; naming mismatch of "system intents"

- **Type:** naming_drift
- **Documents:** implement-interview/SKILL.md:243 (`config/intents.yaml`), mfangdai-ai-agent/GAPS.md:193-198 (M8: intents.yaml incomplete)
- **Problem:** GAPS.md M8 documents that `intents.yaml` defines only 7 intents while `classify.py` hardcodes 14 system intents. implement-interview's code generation rule #1 (line 262) says "Include 17 system intents + custom intents from interview." The count is inconsistent across documents: Vision says "17 system intents" (HLD line 194), implement-interview says "17 system intents," GAPS.md says "14 system intents + ask_mortgage_question," and `classify.py` list has 10 intents in the prompt template. No single document has the authoritative count.
- **Proposed Fix:** Audit and reconcile the intent count. Publish a canonical list of all system intents in the intent classification spec. Update implement-interview, GAPS.md, and the mfangdai-agent to reference the canonical list.
- **Severity:** LOW

### ISSUE-32: missing_cross_ref — VISION.md document tree lists `zh/` directory but HLD doesn't

- **Type:** missing_cross_ref
- **Documents:** VISION.md:240 (line shows `zh/`), HLD:244-265 (document tree)
- **Problem:** VISION.md's document tree (line 240) includes `zh/` as a subdirectory under `specs/`. HLD's document tree (lines 244-265) does not include `zh/`. This is a minor version skew: does `zh/` exist? Is it supposed to? Only one document tree includes it.
- **Proposed Fix:** Either remove `zh/` from VISION.md's tree or add it to HLD's tree. Verify if the directory exists and contains content.
- **Severity:** LOW

### ISSUE-33: duplication — implement-interview anti-patterns table partly overlaps GAPS.md findings

- **Type:** duplication
- **Documents:** implement-interview/SKILL.md:323-338, mfangdai-ai-agent/GAPS.md:1-412
- **Problem:** implement-interview's anti-patterns table (lines 323-338) lists 13 anti-patterns with symptoms, rationale, and fixes. Several of these anti-patterns — "Declaring done after code generation," "Accepting 'I want a chatbot' without multi-party flows," "Skipping privacy questions," "Not asking about output format," "Generating files over 1000 lines" — correspond directly to gaps found in the mfangdai-agent review (GAPS.md: C6 no real borrower contact, H6 no input limits, M2 no conversation archival, C1 no auth, etc.). The anti-patterns were presumably derived from these gaps, but the connection isn't documented. The anti-patterns table should cite specific GAPS.md issues as evidence.
- **Proposed Fix:** In the anti-patterns table's "Sources" column or in a footnote, cite the specific GAPS.md issues that motivated each anti-pattern. This makes the anti-patterns evidence-based rather than speculative.
- **Severity:** LOW

### ISSUE-34: naming_drift — "Temperature = 0" rule in VISION vs actual usage in mfangdai-agent

- **Type:** naming_drift
- **Documents:** VISION.md:154, PRD.md:197, PRD.md:218
- **Problem:** VISION §6.3 LLM Rules: "Temperature = 0 for extraction/classification/decision; 0.3 for response generation." PRD line 197: "Intent Classification: LLM-driven (temperature=0)." PRD line 218: "LLM (call_text, temperature=0.3) is available for free-text generation." This aligns with the Vision. However, the `classify.py` code in the mfangdai-agent may use different temperatures depending on the Gateway configuration, and GAPS.md never checks temperature compliance. The PRD alignment is fine, but the runtime compliance is unverified.
- **Proposed Fix:** Add a temperature compliance check to GAPS.md or a CI validation step.
- **Severity:** LOW

### ISSUE-35: missing_cross_ref — contrarian-review SKILL.md quality gates check for skills/ and schemas/ directories

- **Type:** missing_cross_ref
- **Documents:** ai-coworker-contrarian-review/SKILL.md:285-286
- **Problem:** Quality gate MUST item (line 285): "No references to non-existent `scripts/` or `schemas/` directories." This is a quality gate from ai-coworker-auto-tdd that was likely inherited by contrarian-review. The contrarian-review skill itself has no such references (passes), but other skills in this project (`skills/`) have no `scripts/` or `schemas/` directories. This gate is applied inconsistently — it should either be removed from the general checklist or consistently enforced across all project skills.
- **Proposed Fix:** Remove project-specific quality gates from the ai-coworker-contrarian-review skill and keep only review-specific gates (all agents launched, debates within 3 rounds, judge ruled on everything, etc.).
- **Severity:** LOW

---

## Consolidated Findings by Category

### Vision Violations (6): ISSUE-1, ISSUE-5, ISSUE-7, ISSUE-13, ISSUE-14, ISSUE-25

| Issue | What | Vision Reference |
|-------|------|------------------|
| ISSUE-1 | implement-interview generates code | §4.1 "No implementation code yet" |
| ISSUE-5 | mfangdai-agent no LangGraph | AD1: Python + LangGraph |
| ISSUE-7 | PRD uses LangChain not LangGraph | AD1: Python + LangGraph |
| ISSUE-13 | YAML configs are documentary, not runtime | AD26: YAML as single source of truth |
| ISSUE-14 | No per-node permission enforcement | AD12: Two-level permission model |
| ISSUE-25 | Co-extraction violates two-stage | AD22: Two-stage classify+extract |

### Duplications (4): ISSUE-9, ISSUE-10, ISSUE-22, ISSUE-33

| Issue | What | Where |
|-------|------|-------|
| ISSUE-9 | Completeness Verification vs Anti-Stall Protocol | implement-interview vs auto-tdd |
| ISSUE-10 | Contrarian review final gate | implement-interview, auto-tdd, contrarian-review |
| ISSUE-22 | GAPS.md template vs actual format | contrarian-review template vs mfangdai GAPS.md |
| ISSUE-33 | Anti-patterns table overlaps GAPS.md findings | implement-interview anti-patterns vs mfangdai GAPS.md |

### Naming Drifts (6): ISSUE-8, ISSUE-19, ISSUE-20, ISSUE-21, ISSUE-30, ISSUE-34

| Issue | What | Terms |
|-------|------|-------|
| ISSUE-8 | spec-generator vs implement-interview | VISION vs skill name |
| ISSUE-19 | Error escalation vs errorNode | PRD vs VISION/HLD |
| ISSUE-20 | Phase return stack terminology | HLD vs PRD |
| ISSUE-21 | Completeness Verification/Anti-Stall/Quality Gates | Multiple skills |
| ISSUE-30 | Rule engine default not used | implement-interview vs mfangdai |
| ISSUE-34 | Temperature naming consistency | VISION vs PRD vs runtime |

### Cross-Reference Issues (6): ISSUE-4, ISSUE-11, ISSUE-15, ISSUE-18, ISSUE-26, ISSUE-35

| Issue | What | Detail |
|-------|------|--------|
| ISSUE-4 | 14-llm-gateway.md missing from VISION tree | Referenced by HLD and implement-interview |
| ISSUE-11 | llm-gateway §3 cross-ref from skill | Part of ISSUE-4 cascade |
| ISSUE-15 | implement-interview doesn't reference auto-tdd | One-way reference |
| ISSUE-18 | "Appendix B" doesn't exist in HLD | Should be "Appendix A.5" |
| ISSUE-26 | auto-tdd stub doesn't mention implement-interview | Missing reciprocal link |
| ISSUE-35 | quality gates reference non-existent project dirs | Inherited from auto-tdd |

### Missing Coverage (5): ISSUE-6, ISSUE-12, ISSUE-17, ISSUE-23, ISSUE-28

| Issue | What | Missing From |
|-------|------|-------------|
| ISSUE-6 | GAPS.md doesn't check VISION ADs | GAPS.md |
| ISSUE-12 | AD14 (goal-driven) + AD19 (loop-back) missing | PRD, GAPS.md |
| ISSUE-17 | AD27 (declarative field mutations) missing | PRD, GAPS.md |
| ISSUE-23 | AD21, AD22, AD23 not checked | GAPS.md |
| ISSUE-28 | AD22, AD28, AD29, AD31, AD32, AD33 not checked | GAPS.md |

### Version Skew (3): ISSUE-3, ISSUE-27, ISSUE-32

| Issue | What | Detail |
|-------|------|--------|
| ISSUE-3 | VISION says ref impl not started; HLD maps it | Time mismatch |
| ISSUE-27 | Skill strategy defaults pin section numbers | Fragile cross-references |
| ISSUE-32 | VISION tree has `zh/`; HLD tree doesn't | Divergent document trees |

### Semantic Conflicts (4): ISSUE-2, ISSUE-7, ISSUE-16, ISSUE-24

| Issue | What | Detail |
|-------|------|--------|
| ISSUE-2 | implement-interview redefines spec-generator role | Specs vs code output |
| ISSUE-7 | LangChain vs LangGraph | Framework choice |
| ISSUE-16 | Extract default vs AD30 multi-pass | Strategy mismatch |
| ISSUE-24 | Co-extraction vs AD22 two-stage | Architectural approach |
| ISSUE-29 | Generated structure vs actual structure | Project layout mismatch |

---

## Most Urgent Actions (Top 5)

1. **Resolve ISSUE-1 and ISSUE-2** — Decide whether the current phase allows code generation. If yes, update VISION.md §4.1, §3.2, and the deliverables table. If no, strip code generation from implement-interview.

2. **Fix ISSUE-5 and ISSUE-7** — Reconcile mfangdai-agent's tech stack (LangChain, no LangGraph) with VISION AD1 (Python + LangGraph). Either migrate to LangGraph or update the AD with rationale.

3. **Fix ISSUE-4** — Add all missing documents to VISION.md's document tree. This is a 5-minute fix that prevents cascading confusion.

4. **Fix ISSUE-3** — Align VISION.md deliverables table with reality. The Python reference implementation exists (mfangdai-agent). Update the status.

5. **Fix ISSUE-9 and ISSUE-10** — Consolidate duplicated completeness/counterfactual review logic into the contrarian-review skill as the single canonical source.

---

## Appendix: VISION.md ADs Not Covered in GAPS.md

| AD | Description | Status in PRD | Status in GAPS.md |
|----|-------------|---------------|-------------------|
| AD5 | Per-node LLM/deterministic switch | Partial (implicit in routing) | Not checked |
| AD14 | Goal-driven workflow | Missing | Not checked |
| AD17 | Serial/parallel/mixed sub-workflow nodes | Not implemented | Not checked |
| AD18 | Two response modes | Partial (only deterministic formats) | Not checked |
| AD19 | Node loop-back | Missing | Not checked |
| AD22 | Two-stage classify+extract | Violated (co-extraction) | Not checked |
| AD23 | Multi-intent + complex flag | Missing | Not checked |
| AD27 | Declarative field mutations | Violated (imperative mutations) | Not checked |
| AD28 | SCXML as semantic standard | Missing | Not checked |
| AD29 | OpenAPI 3.1 Schema | Not used (custom YAML format) | Not checked |
| AD30 | Multi-pass extraction | Not implemented | Not checked |
| AD31 | Progressive model escalation | Missing | Not checked |
| AD32 | Cheap model by default | Unverified | Not checked |
| AD33 | Daily token budget | Missing | Not checked |
