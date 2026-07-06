# Agent 0 — Vision Alignment + Cross-Document Review

**Date:** 2026-06-24
**Reviewer:** Agent 0 (Vision enforcer)
**Scope:** VISION.md + 21 spec documents + 7 example files (+ referenced `workflow.yaml` / `audit-log-sample.json` / `domain-models/*.yaml` verified to exist)
**Method:** Fresh read of every file against VISION.md §3.2, §4, §5 (33 ADs), §6, §7 (9-item checklist). Cross-document conflict detection across the full set.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 16 |
| MEDIUM | 21 |
| LOW | 10 |
| **TOTAL** | **50** |

Headline findings: (1) PII-rules authority is defined **circularly** between response-generation and domain-model; (2) Chinese text `举一反三` is committed in two English-only spec files (violates VISION.md §10); (3) the intent-classification spec internally contradicts itself on keyword fallback. Beyond these, the most damaging class of issue is **schema/naming drift between the canonical specs and the example files** (IntentDef missing `complex`, `small_talk`/`greeting` vs `chitchat`/`start_conversation`, mortgage `submit_lead` marked non-complex) — the examples teach developers patterns that contradict the specs they are meant to illustrate.

## §7 Checklist Compliance Matrix

Legend: ✅ present & adequate | ⚠️ partial / weak | ❌ missing | N/A (root HLD)

| Spec File | Interfaces | 2+ Options | Comparison Matrix | YAML Examples | Cross-refs | Open Questions | Changelog | References | Rationale |
|-----------|-----------|------------|-------------------|---------------|------------|----------------|-----------|------------|-----------|
| HLD (framework-design) | ⚠️ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| state-machine | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| domain-model | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| intent-classification | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| extraction-layer | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing-execution | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| response-generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| llm-gateway | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tool-ecosystem | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| environment-config | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| observability-monitoring | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| rate-limiting | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| a2a-protocol | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| mcp-api-protocol | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| auth-token-verification | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| cicd-jenkins-pipeline | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| conversation-lifecycle | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| widget-templates | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| agent-types | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ❌ | ✅ | ✅ | ✅ |
| rag-interface | ✅ | ⚠️ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| three-tier-testing-methodology | ⚠️ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ❌ | ⚠️ | ✅ |

**Checklist gaps (❌):**
- `agent-types`: no Open Questions section
- `rag-interface`: no Open Questions section; no comparison matrix (§4 is an adapter mapping table, not a trade-off comparison)
- `three-tier-testing-methodology`: no changelog table (only a `Version:` line), no Open Questions, no 2+ options, no comparison matrix, References labeled "Sources"
- `HLD`: no 2+ options / comparison matrix (acceptable for a root HLD, but technically fails the literal §7 rule)

## CRITICAL

### ISSUE-1: semantic_conflict — PII rules authority is circular between two specs
- **Type:** semantic_conflict
- **Documents:** `08-response-generation-layer-design.md:566,580`, `02-domain-model-design.md:879`
- **Problem:** Response-generation §8.1 states "PII rules (defined in the domain model, see Section 8.2)" and §8.2 is titled "PII Rules (Defined in Domain Model)". But the domain-model spec does NOT define any `pii_rules` anywhere — instead `02-domain-model-design.md:879` (ConversationMessage.masked) says "The authoritative PII rules definition is in [Response Generation §8]". Each spec declares the OTHER spec authoritative. A developer reading either doc is sent to the other, which sends them back. Neither spec is the canonical owner. This also blocks AD #11 compliance (framework guardrails must have a single defined home).
- **Proposed Fix:** Pick one canonical owner. Recommended: **response-generation §8** owns PII *processing* (scrubbing pipeline, masking strategies), and **domain-model** owns PII *declaration* (`pii_rules:` block inside `components/schemas/` entity extensions, e.g. `x-pii: { fields: [phone, email], strategy: partial_mask }`). Update domain-model §2/§3 to document the `x-pii` extension, and change response-generation §8.1/§8.2 to say "PII rule declarations live in the domain model as `x-pii` extensions; the scrubbing pipeline that consumes them is defined here." Remove the "authoritative definition is in Response Generation §8" note from domain-model §10.3 and replace with "PII rule declarations: see Domain Model §3 (`x-pii` extension). PII scrubbing pipeline: see Response Generation §8."
- **Severity:** CRITICAL

### ISSUE-2: vision_violation — Chinese text committed in English-only spec files
- **Type:** vision_violation
- **Documents:** `01-deterministic-workflow-framework-design.md:337`, `21-three-tier-agent-testing-methodology.md:173,430,545,810`
- **Problem:** VISION.md §10 / project CLAUDE.md states "English-Only Commits. Every file committed to the GitHub repository must be in English. Non-English content belongs only in directories listed in `.gitignore`." The `docs/specs/` directory is committed. Yet the Chinese phrase `举一反三` ("infer related cases") appears 5 times across two committed spec files: HLD line 337 ("举一反三 edge cases") and the testing methodology at lines 173, 430, 545, 810. This is a direct, unambiguous violation of a stated project principle.
- **Proposed Fix:** Replace every `举一反三` occurrence with an English equivalent such as "inference-by-analogy" or "edge-case inference" (the testing methodology already uses "expand by inference" alongside it at line 430 — just delete the Chinese). Run `rg '[一-龥]' docs/specs/` in CI to prevent regression. (Note: the `docs/specs/zh/` directory is the legitimate home for Chinese content.)
- **Severity:** CRITICAL

### ISSUE-3: semantic_conflict — intent-classification contradicts itself on keyword fallback
- **Type:** semantic_conflict
- **Documents:** `04-intent-classification-design.md:17,252-285`
- **Problem:** The changelog (v0.6.0, line 17) states: "Remove keyword fallback entirely: delete §3.4 (Keyword Matching) + §3.6 (Merge Strategy); simplify to LLM-only flow ... remove `"keyword"` from `ClassifiedIntent.source` enum; keywords kept in IntentDef as metadata only". §3.4 (line 335) reinforces: "There is no keyword fallback." Yet §2.4 "Classification Strategy" still presents **Option B: Cascade (Keyword-First, LLM-Second)** (lines 263-285) as a supported strategy with a full comparison matrix, where "the classifier runs a deterministic keyword/regex match first" and returns results "immediately (zero LLM cost)". These two statements are mutually exclusive — either keyword fallback was removed (LLM-only) or Option B is a valid keyword-first strategy. A developer cannot determine the canonical classification design.
- **Proposed Fix:** Reconcile intent. If the v0.6.0 decision stands (LLM-only, no keyword runtime use), then §2.4 Option B must be removed or relabeled as a *future/cost-optimization* option explicitly marked "not currently supported; deferred". If Option B is intentionally retained as a deployment option, then the v0.6.0 changelog entry and §3.4's "There is no keyword fallback" must be softened to "keyword matching is not used in the default LLM-first flow but is available as Option B for cost-constrained deployments." Recommend the latter (keep Option B, fix the absolute language), since VISION.md AD #3 ("LLM-assisted NLU + deterministic core") implies deterministic fallback is desirable.
- **Severity:** CRITICAL

## HIGH

### ISSUE-4: semantic_conflict — domain-model IntentDef schema is missing the `complex` field
- **Type:** semantic_conflict / missing_cross_ref
- **Documents:** `02-domain-model-design.md:454-482`, `04-intent-classification-design.md:209-246`
- **Problem:** Domain-model §5.1 defines `IntentDef` with fields `name, description, confidence_threshold, entry_state, examples, fallback_intent` — but omits the `complex` field. Intent-classification §2.3 (the canonical IntentDef schema) includes `complex: boolean` (AD #23 — the `complex` flag prevents incompatible multi-turn intents from being processed together). The domain-model IntentDef is therefore an outdated/incomplete version of the canonical schema. Any developer copying the domain-model §5.1 example will produce intents that fail the §4.3 intent-combination validation rules.
- **Proposed Fix:** Add `complex: boolean` (with description: "true = multi-turn task; cannot combine with other complex intents") to the domain-model §5.1 IntentDef schema and the §5.1 YAML example. Add a cross-reference: "Canonical IntentDef schema: see Intent Classification §2.3. This section reproduces the subset relevant to domain-model state binding." Update the changelog.
- **Severity:** HIGH

### ISSUE-5: semantic_conflict — llm-gateway §4.7/§4.8 broken structure, duplicate env-defaults, contradictory tier chains
- **Type:** semantic_conflict / version_skew
- **Documents:** `14-llm-gateway.md:573-596`
- **Problem:** Three coupled defects in §4:
  1. **§4.7 "Sticky Model (Escalation Memory)"** (line 581) is immediately followed by a stray comparison-matrix fragment (`| Provider redundancy | None | Full | ...`), not the sticky-tier content. The actual sticky-tier content lives under §4.9 "Sticky Tier" (line 597). So §4.7's heading does not match its body.
  2. **§4.8 "Environment-Specific Defaults"** (line 589) duplicates §4.6 "Environment-Specific Defaults" (line 573) — same heading, two different tables.
  3. The two tables **contradict**: §4.6 lists providers as `openai [gpt-4o-mini, gpt-4o] + anthropic [claude-haiku-3-5]` (multi-provider), while §4.8 lists a single-provider tier chain `gpt-4o-mini → gpt-4o → gpt-4.1`. §4.1's provider list does not include `gpt-4.1` at all. A developer cannot tell which env defaults are canonical.
- **Proposed Fix:** Delete the duplicate §4.8. Move the stray comparison-matrix fragment in §4.7 to wherever it belongs (likely a deleted escalation-strategy comparison) and replace §4.7's body with a one-line pointer to §4.9 ("Sticky tier behavior is defined in §4.9") or remove §4.7 entirely. Reconcile the model list: either add `gpt-4.1` to §4.1 providers or remove it from §4.8. Ensure §4.6 and §4.8 (after dedup) present one consistent set of env defaults.
- **Severity:** HIGH

### ISSUE-6: semantic_conflict — widget-templates mixes insurance and mortgage domain terminology
- **Type:** semantic_conflict / naming_drift
- **Documents:** `09-widget-templates.md:264-359,516`
- **Problem:** The spec is filed under the mortgage-lead domain (widgets named `rate_calculator`, `loan_comparison_table`) but is saturated with **insurance** terminology that does not belong in mortgage: `deductible` (§3.1, §3.2, §3.3, §3.6), `coverage amount` (§3.2 validation message), `policy_end_date` (§3.2 output), `Quote expiry`, and the §4.3 ASCII-art header literally reads `HOME INSURANCE CHAT` (line 516) while the surrounding text discusses loans. The widget catalog (§3.3) lists `deductible_estimator` and describes inputs as "loan_amount, property value, deductible". This is an incomplete domain migration from a prior home-insurance version of the spec; the result is a spec that belongs to neither domain cleanly and will mislead any developer adapting it (AD #2 — generic framework; the spec must not leak a wrong industry's vocabulary).
- **Proposed Fix:** Decide the canonical domain for this spec. Given VISION.md §9 and the mortgage-lead example are primary, convert all insurance terms to mortgage equivalents: `deductible` → remove (mortgages have no deductible; use `down_payment` or `loan_term`), `coverage amount` → `loan amount`, `policy_end_date` → `loan_term_end` or remove, `Quote expiry` → `Rate lock expiry`. Change the §4.3 header from `HOME INSURANCE CHAT` to `MORTGAGE LEAD CHAT`. Alternatively, if the spec is intended to be domain-agnostic, generalize all field names and remove both insurance- and mortgage-specific terms. Re-read every widget in §3.3 against the chosen domain.
- **Severity:** HIGH

### ISSUE-7: version_skew — tool-ecosystem §7.6 heading is missing (broken markdown)
- **Type:** version_skew
- **Documents:** `13-tool-ecosystem.md:812`
- **Problem:** Line 812 reads `--- — OpenCode / Claude SDK as a Tool` — the `## 7.6 SDK Tools` markdown heading is missing, leaving a bare `---` horizontal rule followed by ` — OpenCode / Claude SDK as a Tool` as stranded text. The §7.6 subsections (§7.6.1–§7.6.7) follow correctly, but the parent heading that anchors them is gone. This breaks document navigation and any TOC generator. The changelog (v0.5.0, line 16) claims `sdk` tool type was added to §7.6, so the heading was presumably lost in a later edit.
- **Proposed Fix:** Replace line 812 with `## 7.6 SDK Tools — OpenCode / Claude SDK as a Tool` (matching the style of `## 7.5 A2A Tool Type — Agent-to-Agent as a Tool` at line 554).
- **Severity:** HIGH

### ISSUE-8: semantic_conflict — mortgage-lead example marks `submit_lead` as non-complex and omits required examples
- **Type:** semantic_conflict
- **Documents:** `examples/mortgage-lead/intent-definitions.md:9`, `04-intent-classification-design.md:235,494`
- **Problem:** The mortgage-lead example's intent table marks `submit_lead` as `Complex: No` (line 9). But intent-classification §2.3 shows `submit_lead` with `complex: true`, and `submit_lead` drives a multi-turn lead-collection workflow (identify_borrower → collect_lead_purpose → ... → submit_lead) — exactly the "multi-turn task" the `complex` flag denotes. Marking it non-complex means it could be wrongly combined with other complex intents in a single message, violating AD #23. Separately, the example provides NO `examples:` (few-shot) and NO `keywords:` for any custom intent, yet intent-classification §5.7 mandates "Every custom intent must provide at least 3 `examples`" and rejects definitions with fewer at validation time. The example is non-conforming with two spec rules.
- **Proposed Fix:** (a) Change `submit_lead` (and any other multi-turn write intent like `provide_lead_detail`, `create_quote`) to `Complex: Yes` in the example table. (b) Add a YAML block with `examples:` (≥3) for each custom intent, matching the §2.3 IntentDef shape. The example should be a valid drop-in that passes the framework's configuration validation.
- **Severity:** HIGH

### ISSUE-9: semantic_conflict — home-insurance example uses an outdated IntentDef schema
- **Type:** semantic_conflict / version_skew
- **Documents:** `examples/home-insurance/intent-definitions.md:9-16`, `04-intent-classification-design.md:17,60,209-246`
- **Problem:** The home-insurance `IntentDef` schema (lines 9-16) shows only `name, description, keywords, examples` and describes `keywords` as "deterministic fallback patterns" — implying keywords are used in runtime classification. But intent-classification v0.6.0 (line 17) explicitly removed keyword fallback: "keywords kept in IntentDef as metadata only" and "Keywords are not used in runtime classification" (§2.1 line 60). The example also omits the `complex` field (same issue as ISSUE-4) and the `confidence_threshold`/`entry_state`/`fallback_intent` fields that domain-model §5.1 requires. The example thus teaches a schema that the framework would reject at load time.
- **Proposed Fix:** Update the home-insurance `IntentDef` schema block to match intent-classification §2.3 exactly: add `complex: boolean`, rename the `keywords` comment to "metadata only (not used in runtime classification)", and add `confidence_threshold`, `entry_state`, `fallback_intent`. Add `complex: false` to each of the 7 custom intents in the catalog (or `true` for multi-turn ones like `get_quote`/`file_claim`). Add `examples:` are already present (good) — keep ≥3.
- **Severity:** HIGH

### ISSUE-10: naming_drift — `small_talk` / `greeting` used instead of canonical `chitchat` / `start_conversation`
- **Type:** naming_drift
- **Documents:** `07-conversation-lifecycle.md:666`, `examples/mortgage-lead/e2e-scenarios.md:115`
- **Problem:** Conversation-lifecycle §9.4 (line 666) lists "Non-business intents (`greeting`, `small_talk`, `out_of_scope`)" and "Business intents (`submit_lead`, `check_rates`, `provide_information`)". But the canonical intent-classification §2.1 defines the 17 system intents as `start_conversation` (not `greet`/`greeting`), `chitchat` (not `small_talk`), and `provide_information` (✅). Neither `greeting` nor `small_talk` exist as system intents. The mortgage-lead e2e Scenario 7 (line 115) uses `small_talk` as the classified intent for "How's the weather?". These non-canonical names will not match any registered IntentDef and would fall to `unrecognized_intent` at runtime.
- **Proposed Fix:** Replace `greeting` → `start_conversation` and `small_talk` → `chitchat` in conversation-lifecycle §9.4 and mortgage-lead e2e Scenario 7. Add a note in conversation-lifecycle §9.4 that the canonical intent names are defined in intent-classification §2.1 and must be used verbatim.
- **Severity:** HIGH

### ISSUE-11: naming_drift — testing-methodology uses non-canonical intent names throughout
- **Type:** naming_drift
- **Documents:** `21-three-tier-agent-testing-methodology.md:149,157,236,243,269,442,444,527,684,687,698`
- **Problem:** The testing methodology uses intent labels `greet`, `help`, `ask_about_rates`, `provide_loan_info` — none of which are in the canonical 17 system intents (intent-classification §2.1) or the mortgage-lead custom intents (which use `submit_lead`, `check_rates`, `provide_lead_detail`). `greet` should be `start_conversation`; `ask_about_rates` and `provide_loan_info` are mfangdai-implementation names, not framework names. Because this spec is explicitly "industry-agnostic" (line 6) and meant as a reference pattern, the non-canonical names propagate the wrong vocabulary to adopters.
- **Proposed Fix:** Replace `greet` → `start_conversation`; replace `ask_about_rates` → `check_rates` (or a generic `ask_question`); replace `provide_loan_info` → `provide_information` (system) or `provide_lead_detail` (mortgage). Add a note that the concrete intent names come from the workflow's `IntentDef` catalog and that the examples use placeholder names for illustration.
- **Severity:** HIGH

### ISSUE-12: semantic_conflict — MCP `get_status` lifecycle enum is missing `archived`
- **Type:** semantic_conflict
- **Documents:** `11-mcp-api-protocol.md:308`, `02-domain-model-design.md:784`, `07-conversation-lifecycle.md:57-65`
- **Problem:** MCP §3.4 `get_status` output declares `lifecycle_state` enum as `[created, active, paused, completed, abandoned, timeout]` (6 values). The canonical lifecycle (domain-model §10.1 AgentState.lifecycleState and conversation-lifecycle §2.1) defines **7** values including `archived`. An archived conversation queried via MCP `get_status` would fail schema validation or be forced into an incorrect state. This is a cross-document enum drift.
- **Proposed Fix:** Add `archived` to the MCP §3.4 `lifecycle_state` enum so it matches domain-model §10.1 exactly: `[created, active, paused, completed, abandoned, timeout, archived]`. Add a cross-reference note: "Canonical lifecycle states: see Conversation Lifecycle §2.1."
- **Severity:** HIGH

### ISSUE-13: semantic_conflict — routing §1.2/§1.3 contradict on whether append-only is configurable
- **Type:** semantic_conflict
- **Documents:** `06-routing-execution-layer-design.md:85,113,131-140`
- **Problem:** §1.2 (line 85) states "The framework uses a single strategy: **append** — all parallel writes are accumulated, never overwritten." §1.3 (line 113) states "All `agentState` fields use append-only semantics. This is not configurable — it is a framework-level enforcement." Yet §1.3 then shows a `state_reducers:` YAML block (lines 131-140) with strategies `conflict_detect` (on_conflict: raise), `last_write_wins`, `append`, and the `Reducer` interface (line 145) offers `"last_write_wins" | "conflict_detect" | "append" | "merge" | "custom"`. A single field cannot be both "not configurable, always append" and "configurable across 5 strategies". Conversation-lifecycle §4.4 cites this section as the authority for "all state fields use append-only semantics", inheriting the contradiction.
- **Proposed Fix:** Decide one model. Recommended: append-only is the **default and framework-enforced for the listed audit fields** (`messages`, `audit_log`), but `collectedFields` and other business fields are **configurable** via `state_reducers` (because the §1.2 deep-merge and conflict-wrap behavior is already not pure append). Rewrite §1.3 to say: "Audit fields (`messages`, `audit_log`, `llm_calls`) are append-only and not configurable. Business fields (`collectedFields`, `response`, `goal_check_result`) are configurable via `state_reducers` when `parallel_nodes` is non-empty." Remove the absolute "All agentState fields use append-only ... not configurable" sentence. Update conversation-lifecycle §4.4 to match.
- **Severity:** HIGH

### ISSUE-14: vision_violation — three-tier-testing-methodology fails multiple §7 checklist items
- **Type:** vision_violation (§7 checklist)
- **Documents:** `21-three-tier-agent-testing-methodology.md` (whole file)
- **Problem:** VISION.md §7 requires every spec to contain: 2+ options per interface, comparison matrix, open questions, changelog, references. This spec has: ❌ no 2+ options (it presents a single three-tier methodology with no alternatives); ❌ no comparison matrix (no table comparing this methodology against alternatives like single-tier, two-tier, or eval-only); ❌ no Open Questions section; ❌ no changelog table (only a bare `Version: 0.4.0` line at the top); ⚠️ References labeled "Sources" (§19) rather than "References". It also contains extensive Python implementation code (MockGateway, SimClient, LayerTrace classes) which pushes against VISION.md §4.1 "no implementation code yet" — though it is framed as templates.
- **Proposed Fix:** (a) Add a `## Changelog` table (Date/Version/Changes) at the top. (b) Add a `## Open Questions` section (e.g., "What N gives stable Tier 3 confidence?", "How to handle flaky LLM providers in Tier 2 CI?"). (c) Add a `## Alternatives Considered` section with a comparison matrix: three-tier vs. single-tier-mock-only vs. two-tier (mock + e2e) vs. eval-only — with accuracy/cost/coverage trade-offs (this satisfies both "2+ options" and "comparison matrix"). (d) Rename §19 "Sources" → "References" and split into References (external) + Validation Sources (mfangdai). (e) Consider marking the Python blocks as "illustrative templates" explicitly to stay within §4.1.
- **Severity:** HIGH

### ISSUE-15: version_skew — extraction-layer §3.1 references non-existent §2.6
- **Type:** version_skew
- **Documents:** `05-extraction-layer-design.md:17,257`
- **Problem:** The changelog (v0.6.0, line 17) says "Add §2.6 Per-State Extraction Scope" and §3.1 (line 257) says "resolved per-field by confidence matrix (see §2.6)". But the actual section numbered in the document is **§2.5** "Per-State Extraction Scope" (line 113); there is no §2.6. The confidence matrix itself lives inside §2.5 (lines 189-197). So the changelog entry and the §3.1 cross-reference both point to a §2.6 that does not exist — a developer following the link finds nothing.
- **Proposed Fix:** Either renumber §2.5 → §2.6 (and update the §2.5 heading and any other internal references) or change the changelog and the §3.1 reference from "§2.6" to "§2.5". Recommended: change references to §2.5 (less churn).
- **Severity:** HIGH

### ISSUE-16: version_skew — HLD §8 Document Tree is stale (missing 4 specs + home-insurance example)
- **Type:** version_skew / missing_cross_ref
- **Documents:** `01-deterministic-workflow-framework-design.md:244-270`, `docs/VISION.md:244-256`
- **Problem:** The HLD §8 Document Tree (lines 244-270) lists only 18 spec files and shows `examples/mortgage-lead/` as the only example directory. It is missing: `09-widget-templates.md`, `20-rag-interface.md`, `10-agent-types.md`, `21-three-tier-agent-testing-methodology.md`, and the entire `examples/home-insurance/` directory (which VISION.md §9 lists as a primary example with workflow.yaml, audit-log-sample.json, etc.). The HLD §5 "Related Design Documents" (lines 191-212) does list widget-templates, rag-interface, and agent-types — so §5 and §8 are internally inconsistent. The stale tree misrepresents the project's scope.
- **Proposed Fix:** Replace the §8 Document Tree with the authoritative tree from VISION.md §9 (which is complete and current). Add `examples/home-insurance/` and `examples/cicd/`. Alternatively, delete the HLD §8 tree entirely and replace with a one-line pointer: "The authoritative document tree is maintained in [VISION.md §9](../VISION.md)." (Recommended — single source of truth.)
- **Severity:** HIGH

### ISSUE-17: semantic_conflict — HLD §A.5 commits a personal filesystem path and inconsistent project name
- **Type:** semantic_conflict / naming_drift
- **Documents:** `01-deterministic-workflow-framework-design.md:20,320`
- **Problem:** HLD §A.5 (line 320) states "The mfangdai-agent project at `~/project/mfangdai-ai-agent/` implements all three layers...". Two problems: (1) The project name is inconsistent — the changelog (line 20) and the testing methodology call it `mfangdai-agent`, but §A.5 calls it `mfangdai-ai-agent`. (2) `~/project/mfangdai-ai-agent/` is a personal absolute filesystem path committed to a public spec; this is not portable and leaks a developer's local layout. VISION.md §4.2 warns against over-specifying implementation; a hardcoded local path is the extreme case.
- **Proposed Fix:** Pick one name (`mfangdai-agent`) and use it everywhere. Replace `~/project/mfangdai-ai-agent/` with a relative or abstract reference such as "the `mfangdai-agent` reference implementation" or "see `mfangdai-agent/` (reference implementation repo)". If the mapping table is valuable, move it to an examples directory rather than the HLD body.
- **Severity:** HIGH

## MEDIUM

### ISSUE-18: semantic_conflict — extraction-layer Options B and C lack descriptions (only in matrix)
- **Type:** vision_violation (§7: "at least 2 options per interface")
- **Documents:** `05-extraction-layer-design.md:270-308,503-533,565-577`
- **Problem:** §3.2 "Implementation Options" for the **Extract** interface describes only Option A (LLM with Structured Output) in detail; Options B (Deterministic) and C (Hybrid) appear only as columns in the §3.4 comparison matrix with no prose description, no strengths/weaknesses table, no YAML. Same for **Validate** §4.3 (only Option A rule-engine described; B Predicate and C Pydantic exist only in the §4.4 matrix) and **Transform** §5.3 (only Option A Declarative Rule Pipeline described; no B/C prose). The §7 checklist requires "at least 2 options per interface" — the options are nominally present in the matrices but not documented to a usable level.
- **Proposed Fix:** Add a short `#### Option B` and `#### Option C` subsection under §3.2, §4.3, and §5.3, each with a one-paragraph description and a strengths/weaknesses table matching the style of Option A. The comparison matrices can stay as the summary.
- **Severity:** MEDIUM

### ISSUE-19: version_skew — state-machine §1.2 has a duplicate line in guards.py example
- **Type:** version_skew
- **Documents:** `03-state-machine-design.md:169-170`
- **Problem:** The `guards.py` pseudo-code block contains two consecutive identical lines: `return ctx.loan_amount <= 920000 and ctx.state in ctx.licensed_states` (line 169) and `return ctx.loan_amount <= 920000 and ctx.state in licensed_states` (line 170) — the second missing the `ctx.` prefix on `licensed_states`. This is a copy-paste artifact; the second line is dead code that would also be a NameError.
- **Proposed Fix:** Delete line 170.
- **Severity:** MEDIUM

### ISSUE-20: version_skew — state-machine §3.4 self-references §3.4 for meta-variables (they are in §3.3)
- **Type:** version_skew
- **Documents:** `03-state-machine-design.md:368`
- **Problem:** §3.4 "Guard Expression Syntax" line 368 says "Meta-variables: framework-generated flags listed in §3.4". But the meta-variables (`exit_guard_pass`, `context_complete`, etc.) are actually listed in §3.3 "Complete State Field Reference" (lines 348-358), not in §3.4. The reference is a wrong self-pointer.
- **Proposed Fix:** Change "listed in §3.4" → "listed in §3.3".
- **Severity:** MEDIUM

### ISSUE-21: version_skew — domain-model changelog row has malformed table cells
- **Type:** version_skew
- **Documents:** `02-domain-model-design.md:16`
- **Problem:** The v0.5.0 changelog row ends with `...downstream API schema patterns | |` — a trailing empty cell (`| |`) producing a malformed markdown table row (extra column). This renders as a broken row in most markdown viewers.
- **Proposed Fix:** Remove the trailing `| |` so the row has exactly 3 cells: `| 2026-06-18 | 0.5.0 | Adopt OpenAPI 3.1 ... downstream API schema patterns |`.
- **Severity:** MEDIUM

### ISSUE-22: semantic_conflict — response-generation §2.2 goal example has data errors
- **Type:** semantic_conflict
- **Documents:** `08-response-generation-layer-design.md:81-82`
- **Problem:** The `WorkflowGoal` example contains `expected_entities: ["lead_purpose", "loan amount_needs"]` (a field name with a space, "loan amount_needs", which is not a valid entity field) and `expected_outputs: ["rate_calculation", "rate_calculation", "quote"]` (duplicate `rate_calculation`). These are clearly typos that would confuse a developer copying the example.
- **Proposed Fix:** Change `"loan amount_needs"` → `"loan_amount"` (or remove); deduplicate `expected_outputs` to `["rate_calculation", "quote"]`.
- **Severity:** MEDIUM

### ISSUE-23: semantic_conflict — response-generation §3.3 eval case has wrong field values
- **Type:** semantic_conflict
- **Documents:** `08-response-generation-layer-design.md:212-214,230-232`
- **Problem:** The `prod_default` eval case sets `entities.loan_amount: "123 Main St"` (an address value assigned to a loan_amount field) and `loan_purpose: "apartment"` (`apartment` is a property_type, not a loan_purpose — loan_purpose enum is `[purchase, refinance, cash_out]` per domain-model). The `incomplete_flow` case repeats `loan_amount: "456 Oak Ave"`. These make the eval example semantically nonsensical and inconsistent with the domain-model enums.
- **Proposed Fix:** Use consistent values: `loan_amount: 500000`, `loan_purpose: "purchase"`, `property_type: "apartment"`, `address: "123 Main St"`. Align field names with the mortgage-lead domain model.
- **Severity:** MEDIUM

### ISSUE-24: version_skew — llm-gateway §7.1 Layer 1 example has a duplicate `floor_area` field
- **Type:** version_skew
- **Documents:** `14-llm-gateway.md:849-854`
- **Problem:** The `collect_lead_purpose_extract` output_schema lists `floor_area` twice (lines 849-854): once with `required: true` and once with `required: false`. YAML/JSON Schema treats this as one overriding the other (or a parse error in strict mode). A developer copying this gets an ambiguous schema.
- **Proposed Fix:** Delete the duplicate `floor_area` block (keep one with the intended `required` value).
- **Severity:** MEDIUM

### ISSUE-25: version_skew — environment-config §5 lists the same workflow twice
- **Type:** version_skew
- **Documents:** `18-environment-config.md:290-291`
- **Problem:** The `workflows:` list contains two identical entries: `- "workflows/mortgage_lead_submission.yaml"` on both line 290 and line 291. Copy-paste artifact.
- **Proposed Fix:** Delete the duplicate line.
- **Severity:** MEDIUM

### ISSUE-26: semantic_conflict — environment-config §5 calls home-insurance "legacy", contradicting VISION
- **Type:** semantic_conflict / vision_violation
- **Documents:** `18-environment-config.md:287`, `docs/VISION.md:244-249`
- **Problem:** environment-config §5 line 287 has a commented-out `- "domain-models/home-insurance.yaml"  # legacy domain model`. But VISION.md §9 lists `examples/home-insurance/` as a current primary example (with workflow.yaml, audit-log-sample.json), and `docs/domain-models/home-insurance.yaml` exists and is actively maintained (9881 bytes, dated 2026-06-18). Labeling home-insurance "legacy" contradicts VISION.md's treatment of it as a first-class example domain.
- **Proposed Fix:** Either uncomment the home-insurance domain-model entry (it exists and is current) or, if only one domain model is loaded by default, change the comment from "legacy domain model" to "alternate example domain — enable for home-insurance workflows". Remove the word "legacy".
- **Severity:** MEDIUM

### ISSUE-27: semantic_conflict — observability §2.1 defines `llm_retry_total` twice with different semantics
- **Type:** semantic_conflict
- **Documents:** `15-observability-monitoring.md:77,80`
- **Problem:** The metric taxonomy lists `llm_retry_total` twice: line 77 ("Retry attempts (across all calls)", Counter) and line 80 ("Retries before escalation or success (by node_id, error_type)", Counter). Same metric name, two different definitions and label sets — Prometheus would collapse these into one series with conflicting labels, causing query confusion.
- **Proposed Fix:** Split into two distinct metrics: `llm_retry_total` (total retry attempts, labels: model) and `llm_retries_before_escalation_total` (retries before escalation, labels: node_id, error_type). Keep only the first in the §2.2 `llm` collector list and add the second.
- **Severity:** MEDIUM

### ISSUE-28: version_skew — cicd §10 splits the References section
- **Type:** version_skew
- **Documents:** `19-cicd-jenkins-pipeline.md:932-950`
- **Problem:** §9 "References" ends at line 941, then §10 "Example Infrastructure" begins at line 945, but lines 948-950 contain THREE more reference entries (`- [Conversation Lifecycle]...`, `- [Jenkins Declarative Pipeline]...`, `- [Jenkins Kubernetes Plugin]...`) appended AFTER §10. The References list is split across §9 and a stray tail after §10 — a reader scanning §9 misses the Conversation Lifecycle and Jenkins references, and a reader of §10 finds unexpected reference lines at the end.
- **Proposed Fix:** Move lines 948-950 (`Conversation Lifecycle`, `Jenkins Declarative Pipeline`, `Jenkins Kubernetes Plugin`) up into the §9 References list. Leave §10 as a single paragraph pointing to the hetzner-jenkins example.
- **Severity:** MEDIUM

### ISSUE-29: naming_drift — rate-limiting uses "Claims operations" terminology (insurance leftover)
- **Type:** naming_drift
- **Documents:** `17-rate-limiting.md:125,239`
- **Problem:** §2.4 line 125 says "Claims operations get tight limits for security and cost reasons" but the example tool is `lead_distribution_engine` (a mortgage-lead tool, not an insurance claim). §3.3 tier comparison (line 239) lists a "Claims operations/min" capability row with values 5/30/100, but the per-tool examples throughout are `lead_distribution_engine`, `vector_search_mcp`, `calculate_rate_api` — none of which is a claims operation. "Claims" is leftover insurance vocabulary; the framework is generic (AD #2) and the running example is mortgage-lead.
- **Proposed Fix:** Replace "Claims operations" → "Sensitive write operations" (generic) or "Lead distribution" (mortgage-lead example) consistently in §2.4 and §3.3. Update the §3.3 capability row label.
- **Severity:** MEDIUM

### ISSUE-30: semantic_conflict — home-insurance e2e-scenarios has internal data inconsistencies
- **Type:** semantic_conflict
- **Documents:** `examples/home-insurance/e2e-scenarios.md:50,126,129,136,185,213,215`
- **Problem:** Scenario 1's narrative and its audit log disagree on the same scenario: (a) building age: line 50 says "age=9" (built 2015, "current year 2024"), but line 126 says `compute_risk_score(age=11, ...)` and line 213 audit says `"age":9`. (b) risk_score: narrative line 129 uses `risk_score = 18`, audit line 213 uses `"risk_score":14`. (c) premium: narrative line 136 says `annual_premium = 6,104`, audit line 215 says `"annual_premium":5992`. (d) line 185 (Key Design Points) says "phone: LLM1(0.76 < 0.7)" — but 0.76 is NOT < 0.7, and the actual Scenario 1 phone flow (line 46) had LLM1=null. The 0.76 value belongs to Scenario 4 (line 390), not Scenario 1. The same scenario is described with two incompatible sets of numbers.
- **Proposed Fix:** Reconcile the narrative and audit log to one set of numbers. Recommended: use risk_score=18, rate_multiplier=0.872, annual_premium=6104 (the narrative values) and update the audit-log JSON (lines 213-215) to match, plus set age=9 consistently. Fix line 126 `age=11` → `age=9`. Fix line 185 to reference the correct Scenario 1 numbers (LLM1=null for phone) or move that row to a Scenario 4 design-points table.
- **Severity:** MEDIUM

### ISSUE-31: version_skew — agent-types §2.1 has a malformed Python docstring
- **Type:** version_skew
- **Documents:** `10-agent-types.md:56-70`
- **Problem:** The `ReadOnlyAgent` Protocol pseudo-code opens a docstring at line 56 (`"""Agent for casual conversation...`), closes it at line 64 (`"""`), then has bare text `Backend examples:` (lines 66-69) floating outside any docstring, then another `"""` at line 70. The "Backend examples" block is stranded between two docstring delimiters — syntactically invalid even as pseudo-code and confusing to read (it looks like a second docstring that never opened).
- **Proposed Fix:** Merge into a single docstring: open `"""` at line 56, keep all content (including "Backend examples") inside, close `"""` once at line 70. Remove the premature `"""` at line 64.
- **Severity:** MEDIUM

### ISSUE-32: version_skew — agent-types changelog rows are out of order
- **Type:** version_skew
- **Documents:** `10-agent-types.md:12-13`
- **Problem:** The changelog lists v0.2.0 (line 12) BEFORE v0.1.0 (line 13), breaking the chronological convention used by every other spec in the suite (which lists versions either strictly ascending or strictly descending). Both are dated 2026-06-18, so the ordering is ambiguous, but v0.2.0 should come after v0.1.0.
- **Proposed Fix:** Swap the two rows so v0.1.0 precedes v0.2.0 (descending: newest first → v0.2.0 then v0.1.0 is actually correct for descending; the issue is they appear ascending-by-version-number but dated identically). Clarify by giving v0.1.0 and v0.2.0 distinct descriptive entries and ensuring descending order (v0.2.0 first) matches the rest of the suite. Most specs use descending — so the current order (v0.2.0 then v0.1.0) is actually fine for descending; verify all specs use the same direction and standardize.
- **Severity:** MEDIUM

### ISSUE-33: vision_violation — rag-interface missing Open Questions and comparison matrix
- **Type:** vision_violation (§7 checklist)
- **Documents:** `20-rag-interface.md` (whole file)
- **Problem:** The RAG interface spec has no `## Open Questions` section and no comparison matrix. §4 "Backend Adapter Mapping" is a mapping table (Interface → Haystack/LlamaIndex/LangChain implementations), not a comparison matrix with trade-offs (accuracy/cost/latency/community). VISION.md §7 requires both. The spec also presents 3 backend options (Haystack/LlamaIndex/LangChain) but never compares them on dimensions like ease-of-adoption, vector-DB support, or RAG-pattern coverage.
- **Proposed Fix:** (a) Add a `## Open Questions` section (e.g., "Should the framework expose a hybrid retrieval (BM25+dense) option in the interface, or leave that to backend config?", "How are RAG results cited in the audit trail?", "Should RAG evaluation metrics be standardized?"). (b) Add a `### Backend Comparison` matrix comparing Haystack/LlamaIndex/LangChain on: interface cleanliness, vector-DB support, reranker support, RAG patterns (multi-query, parent-doc), community size, license.
- **Severity:** MEDIUM

### ISSUE-34: vision_violation — agent-types missing Open Questions section
- **Type:** vision_violation (§7 checklist)
- **Documents:** `10-agent-types.md` (whole file)
- **Problem:** The agent-types spec has no `## Open Questions` section. Every other spec has one. Notable deferred questions exist (e.g., "Should a WriteAgent ever be reintroduced for non-deterministic writes?", "How do agents interact with the A2A protocol — can an agent be an A2A target?", "Should ReadOnlyAgent support streaming responses?") but are not captured.
- **Proposed Fix:** Add a `## Open Questions` section with 4-6 deferred questions, including the examples above and "Should agents share a common base protocol for capabilities()/health()?".
- **Severity:** MEDIUM

### ISSUE-35: missing_cross_ref — response-generation §1.1 "Section 6" is an ambiguous cross-reference
- **Type:** missing_cross_ref
- **Documents:** `08-response-generation-layer-design.md:50`
- **Problem:** §1.1 "What Layer 3 Does NOT Cover" says "Retry / error handling → Layer 2 (Section 6)". "Section 6" is ambiguous — it could mean §6 of THIS spec (Parallel Execution Pattern) or §6 of the routing spec (Retry & Error Handling). The intended target is routing-execution §6, but the bare "Section 6" reads as a self-reference.
- **Proposed Fix:** Change "Layer 2 (Section 6)" → "Layer 2 — see [Routing & Execution §6](./06-routing-execution-layer-design.md)".
- **Severity:** MEDIUM

### ISSUE-36: semantic_conflict — model names inconsistent across llm-gateway and environment-config
- **Type:** semantic_conflict / naming_drift
- **Documents:** `14-llm-gateway.md:321-345,595,934`, `18-environment-config.md:46,121`
- **Problem:** The set of model names differs across docs: llm-gateway §4.1 providers list only `gpt-4o-mini, gpt-4o, claude-haiku-3-5, claude-sonnet-4-20250514`; §4.8/§8 references `gpt-4.1`; environment-config §2.1 `LLM_MODEL_TIERS` includes `gpt-4.1` and `claude-opus`; §2.3/§2.4/§3 reference `gpt-4o` as the e2e/prod model. A developer cannot determine the canonical model catalog. `gpt-4.1` and `claude-opus` appear in env-config and gateway audit logs but never in the gateway's provider definition.
- **Proposed Fix:** Define the canonical model catalog once (recommend llm-gateway §4.1) and have environment-config's `LLM_MODEL_TIERS` reference it. Either add `gpt-4.1` and `claude-opus` to §4.1's providers or remove them from env-config and the §8 audit example. Ensure the §4.6/§4.8 env-defaults tables (after ISSUE-5 dedup) use only models from §4.1.
- **Severity:** MEDIUM

### ISSUE-37: version_skew — domain-model §5.3 "Multi-Intent Sessions" is stale vs intent-classification
- **Type:** version_skew
- **Documents:** `02-domain-model-design.md:513-522`, `04-intent-classification-design.md:354-411`
- **Problem:** Domain-model §5.3 "Multi-Intent Sessions" describes multi-intent as a future/loose concept: "A single conversation may match multiple intents over its lifetime" (across turns) and "The default behavior is to re-route unless the current state's transition rules explicitly prevent it." But intent-classification §4.2/§4.3 has already IMPLEMENTED multi-intent PER MESSAGE (single user message → multiple `ClassifiedIntent` objects) with the `complex`-flag combination rules (AD #23). Domain-model §5.3 describes an older, weaker model and doesn't reference the implemented per-message multi-intent behavior.
- **Proposed Fix:** Update domain-model §5.3 to cross-reference intent-classification §4.2/§4.3: "Multi-intent per single message is supported — see Intent Classification §4.2 (ClassificationResult with multiple ClassifiedIntent) and §4.3 (combination rules via the `complex` flag)." Add a note that the domain-model's `IntentDef.complex` field (per ISSUE-4) drives the combination validation.
- **Severity:** MEDIUM

### ISSUE-38: naming_drift — `submit_mortgage_lead` vs `submit_lead` vs `submit_mortgage_lead` across docs
- **Type:** naming_drift
- **Documents:** `19-cicd-jenkins-pipeline.md:535,668`, `02-domain-model-design.md:456`, `examples/mortgage-lead/intent-definitions.md:9`
- **Problem:** The primary mortgage intent is named inconsistently: domain-model §5.1 uses `submit_mortgage_lead`; mortgage-lead example uses `submit_lead`; CICD §5.1/§5.3 eval uses `submit_mortgage_lead`; routing/HLD examples use `submit_lead`. Two different names for the same concept. A developer wiring the CICD eval dataset to the mortgage-lead intent catalog would get intent-accuracy=0 because the labels don't match.
- **Proposed Fix:** Pick one canonical name. Recommended: `submit_lead` (shorter, matches the example intent-definitions which is the most concrete artifact). Update domain-model §5.1 and CICD §5.1/§5.3 to use `submit_lead`. Add a note in domain-model §5.1 that intent names are domain-defined and `submit_lead` is the mortgage-lead instance.
- **Severity:** MEDIUM

### ISSUE-39: semantic_conflict — mortgage-lead e2e Scenario 7 routes chitchat-exhaustion to errorNode, contradicting lifecycle spec
- **Type:** semantic_conflict
- **Documents:** `examples/mortgage-lead/e2e-scenarios.md:115-116`, `07-conversation-lifecycle.md:663`
- **Problem:** Mortgage-lead e2e Scenario 7 (line 115) shows the 11th chitchat message routing to `errorNode`. But conversation-lifecycle §9.4 (line 663) specifies that when `max_chitchat_turns` is exhausted, the behavior is "Decline further chitchat, redirect to business intents" — NOT an errorNode transition. errorNode is reserved for errors (AD #15); chitchat-exhaustion is a soft limit, not an error.
- **Proposed Fix:** Change Scenario 7's 11th-turn behavior from `errorNode` to a deterministic "redirect to business" response (matching lifecycle §9.4), e.g., intent=`chitchat`, state=`decline_chitchat` → system responds redirecting to business, returns to previous state. Reserve `errorNode` for actual errors.
- **Severity:** MEDIUM

## LOW

### ISSUE-40: version_skew — routing §6.7 ASCII flow diagram has misaligned box-drawing
- **Type:** version_skew
- **Documents:** `06-routing-execution-layer-design.md:760`
- **Problem:** In the §6.7 errorNode flow diagram, the `retry_with_context` branch line `└── retry_with_context` is indented one column less than its siblings (`├── ask_clarify`, `├── escalate_to_human`, etc.), breaking the visual alignment of the tree.
- **Proposed Fix:** Add one leading space to line 760 so `└── retry_with_context` aligns with the sibling branches.
- **Severity:** LOW

### ISSUE-41: version_skew — home-insurance e2e references "current year 2024" (stale)
- **Type:** version_skew
- **Documents:** `examples/home-insurance/e2e-scenarios.md:50`
- **Problem:** Line 50 says "building built 2015, current year 2024 → age=9". The doc is dated 2026-06-16 and today's date is 2026. Using 2024 as "current year" is stale and makes the age calculation wrong (2026-2015=11, not 9).
- **Proposed Fix:** Change "current year 2024" → "current year 2026" and recompute age=11 (or keep age=9 by changing the build year to 2017). Ensure the age value matches ISSUE-30's reconciliation.
- **Severity:** LOW

### ISSUE-42: version_skew — widget-templates §2.5 welcome message has awkward phrasing
- **Type:** version_skew
- **Documents:** `09-widget-templates.md:177`
- **Problem:** The theme `welcome_message` reads "Hi! I can help you find the best mortgage lead marketplace loan amount." — "loan amount" is the wrong noun (a user wants a loan/rate, not a "loan amount"). Likely a find-and-replace artifact from "insurance quote" → "loan amount".
- **Proposed Fix:** Change to "Hi! I can help you find the best mortgage loan for your needs." or similar.
- **Severity:** LOW

### ISSUE-43: naming_drift — mortgage-lead intent-definitions uses a non-canonical "Type: Write/Read/Control" column
- **Type:** naming_drift
- **Documents:** `examples/mortgage-lead/intent-definitions.md:7-27`, `10-agent-types.md:191-197`
- **Problem:** The mortgage-lead example categorizes intents with a `Type` column (`Write | Read | Control`) — a schema not present in intent-classification §2.3 (which uses `complex: boolean`) or agent-types §4 (which uses the Agent Type × operation matrix). The "Write/Read/Control" taxonomy is invented by the example. While it maps loosely to the agent-types permission model, it is not a documented field and could mislead developers into thinking IntentDef has a `type` field.
- **Proposed Fix:** Either (a) replace the `Type` column with the canonical `complex` boolean column (matching ISSUE-8), or (b) relabel it "Category (informative)" and add a note that it is not part of IntentDef but is derived from the agent-dispatch table in agent-types §4.
- **Severity:** LOW

### ISSUE-44: vision_violation — auth §2.5 commits a real production hostname
- **Type:** vision_violation (§4.2 over-specification)
- **Documents:** `16-auth-token-verification.md:121,131`
- **Problem:** auth §2.5 "Keycloak Configuration (Sample)" says "Extracted from mfangdai (mRateQuote) production deployment" and includes the real-looking host `mratequote.live:17832` and realm `mRateQuote`. Committing a real production hostname/port in a public spec is a security/operational leak and violates VISION.md §4.2 "Don't over-specify implementation". It also ties the spec to one adopter's deployment.
- **Proposed Fix:** Replace `mratequote.live:17832` with a placeholder like `auth.example.com` or `keycloak.${DOMAIN}`. Keep the structural shape (realm, client_id, jwks path) but anonymize the host. Change "Extracted from mfangdai production deployment" → "Adapted from a production Keycloak deployment (anonymized)".
- **Severity:** LOW

### ISSUE-45: semantic_conflict — conversation-lifecycle §1.2 minor contradiction on message history
- **Type:** semantic_conflict
- **Documents:** `07-conversation-lifecycle.md:48,267-268`
- **Problem:** §1.2 says "Message history storage — LangGraph checkpoints handle this" (implying the lifecycle spec does not define it), but §4.2 Checkpoint Content includes a `messages: history: array` field with `window_size: 6`. Minor tension over whether message history is "handled by LangGraph" (opaque) or part of the lifecycle-defined checkpoint schema.
- **Proposed Fix:** Reword §1.2 to "Message history storage — stored within LangGraph checkpoints; the lifecycle schema enriches checkpoints with a bounded `messages.history` window (see §4.2)".
- **Severity:** LOW

### ISSUE-46: naming_drift — example state names vary (`distribute_lead` vs `submit_lead` vs `assign_lead`)
- **Type:** naming_drift
- **Documents:** `01-deterministic-workflow-framework-design.md:81`, `03-state-machine-design.md:301`, `06-routing-execution-layer-design.md:431-432`, `examples/mortgage-lead/e2e-scenarios.md:30`
- **Problem:** The "lead distribution/assignment" state is named `distribute_lead` (HLD §2.1, state-machine §3.2), `assign_lead` (state-machine §1.1, routing §4.3), and `submit_lead`/`lead_submitted` (mortgage-lead e2e). These are three different names for overlapping concepts. While some variation is expected across example scenarios, the canonical specs themselves use both `distribute_lead` and `assign_lead` without explaining the relationship.
- **Proposed Fix:** In the canonical specs, standardize on one name (`assign_lead` for the matching step, `distribute_lead` for the distribution sub-step) and document the distinction once in state-machine §2. Examples can then use either with a cross-reference.
- **Severity:** LOW

### ISSUE-47: version_skew — cicd hetzner-jenkins example Jenkinsfile DB-cleanup is inconsistent
- **Type:** version_skew
- **Documents:** `examples/cicd/hetzner-jenkins.md:60-62`
- **Problem:** The example Jenkinsfile T1 stage runs `rm -f *.db` (glob, deletes all DBs) but T2/T3 run `rm -f mfangdai_t2.db` / `rm -f mfangdai_t3.db` (specific files). The T1 glob would also delete the T2/T3 DBs if run in the same workspace, and the specific-name approach in T2/T3 won't catch other stale DBs. Minor inconsistency in cleanup strategy; also ties the example to the `mfangdai` project name.
- **Proposed Fix:** Standardize on a project-prefixed glob: `rm -f ${PROJECT}_*.db` in all three stages, or use `rm -f *.db` consistently. Replace `mfangdai_t2.db` with `${PROJECT}_t2.db` and parameterize `PROJECT`.
- **Severity:** LOW

### ISSUE-48: version_skew — mortgage-lead README says "18 intents" but the schema omits 10 of the 17 system intents
- **Type:** version_skew
- **Documents:** `examples/mortgage-lead/README.md:14`, `examples/mortgage-lead/intent-definitions.md:20-27`, `04-intent-classification-design.md:36-54`
- **Problem:** The mortgage-lead README claims "18 intents with payload schemas" and the intent-definitions lists 18 (11 custom + 7 control). But the 7 control intents listed omit 10 of the 17 canonical system intents (`pause`, `restart`, `provide_information`, `repeat`, `ambiguous_request`, `out_of_scope`, `help`, `chitchat`, `complaint`, `escalate`). This is acceptable for a domain subset, but the count "18" implies completeness and the missing system intents (especially `escalate`/`complaint` which the agent-types spec assigns to EscalationAgent) leave a gap in the example's coverage of the agent-dispatch model.
- **Proposed Fix:** Either (a) add the missing system intents (at least `escalate`, `complaint`, `help`, `chitchat`, `out_of_scope`) to the example's control-intent table with their agent-dispatch targets, or (b) add a note: "This example lists only the domain-custom intents plus the control intents used in these scenarios; the full 17 system intents are defined in Intent Classification §2.1 and are available automatically." Adjust the "18 intents" claim accordingly.
- **Severity:** LOW

### ISSUE-49: missing_cross_ref — a2a-protocol references "Google A2A Protocol" without context
- **Type:** missing_cross_ref
- **Documents:** `12-a2a-protocol.md:547`
- **Problem:** The References section links `[Google A2A Protocol](https://github.com/google/A2A)` as "Google's Agent-to-Agent protocol (conceptual reference)". The spec body never mentions Google A2A or explains the relationship/inspiration. A reader sees an unfamiliar external reference with no context. (Note: this URL should be verified — if inaccurate it would be a fabricated reference.)
- **Proposed Fix:** Add one sentence in §1 or §7.3 noting that the framework's A2A design is conceptually informed by Google's A2A protocol (if true) and what specifically was borrowed (e.g., task lifecycle, agent cards). If the reference is aspirational rather than substantive, remove it.
- **Severity:** LOW

### ISSUE-50: version_skew — domain-model §2.1 references `mortgage-lead.yaml` but §4.3 example uses `QuoteDetails` (undefined)
- **Type:** version_skew
- **Documents:** `02-domain-model-design.md:97,412`
- **Problem:** §2.1 points to `docs/domain-models/mortgage-lead.yaml` (which exists). §4.3 `submit_lead` state binds `entity: $ref: "#/components/schemas/QuoteDetails"` — but `QuoteDetails` is not defined in the §2.2 schema example (which defines Address, Borrower, MortgageLead, LeadSubmission) nor visible as a defined schema. A reader following the example hits an undefined `$ref`. (The actual `mortgage-lead.yaml` file may define it, but the spec's inline example does not.)
- **Proposed Fix:** Either add a `QuoteDetails` schema snippet to §2.2 or change the §4.3 `submit_lead` entity binding to reference a schema that IS shown in §2.2 (e.g., `LeadSubmission`). Add a note that the full schema is in `mortgage-lead.yaml`.
- **Severity:** LOW

## Consolidated Findings by Category

### Vision Violations (VISION.md §3.2 / §4 / §7 / §10)
- **CRITICAL:** Chinese text in committed specs (ISSUE-2); PII rules circular ownership (ISSUE-1); intent-classification self-contradiction on keyword fallback (ISSUE-3).
- **HIGH:** testing-methodology fails §7 checklist (ISSUE-14); HLD document tree stale (ISSUE-16).
- **MEDIUM:** environment-config mislabels home-insurance "legacy" (ISSUE-26); rag-interface/agent-types missing Open Questions (ISSUE-33, ISSUE-34); extraction Options B/C undocumented (ISSUE-18).
- **LOW:** auth §2.5 commits real production host (ISSUE-44).

### Semantic Conflicts (cross-document contradictions)
- PII rules circular (ISSUE-1) · intent-classification keyword fallback (ISSUE-3) · llm-gateway §4.7/4.8 (ISSUE-5) · widget-templates domain mix (ISSUE-6) · mortgage `submit_lead` non-complex (ISSUE-8) · home-insurance outdated IntentDef (ISSUE-9) · MCP lifecycle enum (ISSUE-12) · routing append-only (ISSUE-13) · domain-model §5.3 stale (ISSUE-37) · model-name catalog drift (ISSUE-36) · chitchat-exhaustion routing (ISSUE-39) · home-insurance e2e numbers (ISSUE-30) · response-gen goal/eval data (ISSUE-22, ISSUE-23) · observability duplicate metric (ISSUE-27).

### Naming Drift
- `small_talk`/`greeting` vs `chitchat`/`start_conversation` (ISSUE-10) · testing-methodology `greet`/`ask_about_rates`/`provide_loan_info` (ISSUE-11) · `submit_mortgage_lead` vs `submit_lead` (ISSUE-38) · rate-limiting "Claims operations" (ISSUE-29) · mortgage IntentDef "Type: Write/Read/Control" (ISSUE-43) · `distribute_lead`/`assign_lead`/`submit_lead` (ISSUE-46) · `mfangdai-agent` vs `mfangdai-ai-agent` (ISSUE-17).

### Version Skew (broken/stale cross-references)
- extraction §2.6 → §2.5 (ISSUE-15) · HLD doc tree (ISSUE-16) · state-machine duplicate line (ISSUE-19) · state-machine §3.4 self-ref (ISSUE-20) · domain-model changelog cell (ISSUE-21) · llm-gateway duplicate floor_area (ISSUE-24) · environment-config duplicate workflow (ISSUE-25) · cicd split References (ISSUE-28) · agent-types malformed docstring (ISSUE-31) · agent-types changelog order (ISSUE-32) · home-insurance stale year (ISSUE-41) · domain-model undefined QuoteDetails (ISSUE-50).

### Missing Coverage (VISION.md requirements not addressed by any spec)
- No spec defines the canonical `pii_rules` declaration home (ISSUE-1 — both specs disown it).
- No spec defines the **Spec Generator Skill** interview templates / decision-point markers (VISION.md §3.3 — "Add interview templates / decision point markers to specs"). The HLD §6 mentions the skill vision but no spec contains actual interview-template sections. This is flagged for the next phase, but no spec records it as an open question.
- No spec addresses **multi-tenant workflow isolation** (HLD Appendix A.5 Q13 lists it as an open question, but no spec owns the design; rate-limiting and auth touch tenancy only at the request/identity layer, not workflow-instance isolation).
- No spec defines **blue-green / version migration of in-flight conversations** (HLD A.5 Q12 and state-machine Appendix C.5 list it as open, but no spec owns a design or references a canonical approach).

## Recommended Priority Order for Fixes

1. **ISSUE-2** (Chinese text) — trivial, CI-enforceable, do first.
2. **ISSUE-1** (PII circular) — blocks AD #11; pick an owner and update both specs.
3. **ISSUE-3** (intent-classification keyword fallback) — reconcile the canonical classification design.
4. **ISSUE-4, ISSUE-8, ISSUE-9** (IntentDef `complex` field across domain-model + both examples) — fix together; the examples are teaching wrong schemas.
5. **ISSUE-5** (llm-gateway §4 structure) — structural decay affecting the most-referenced spec.
6. **ISSUE-6** (widget-templates domain mix) — a whole spec belongs to the wrong domain.
7. **ISSUE-10, ISSUE-11** (intent naming drift in lifecycle/testing/mortgage example) — fix together.
8. **ISSUE-13** (routing append-only contradiction) — affects conversation-lifecycle too.
9. **ISSUE-14** (testing-methodology §7 compliance) — add changelog/open-questions/alternatives.
10. **ISSUE-16** (HLD doc tree) — point to VISION.md §9 as single source of truth.

All remaining MEDIUM/LOW issues are independently fixable in any order.
