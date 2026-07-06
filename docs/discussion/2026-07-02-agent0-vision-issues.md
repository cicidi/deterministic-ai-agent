# Agent 0: Vision Alignment + Cross-Document Review

## Summary
- 14 issues found: 3 critical, 4 high, 4 medium, 3 low

All findings cite verified line numbers from the current files (post-diff state) and/or the diff patch.

---

## Critical Issues

| # | Type | Section | Issue | Fix |
|---|------|---------|-------|-----|
| C1 | `vision_violation` | 06-routing-execution-layer-design.md:845; 12-a2a-protocol.md:650-658; 11-mcp-api-protocol.md:85; 15-observability-monitoring.md:44,49 | **Chinese text in committed spec docs.** New additions introduce Chinese characters in files that must be English-only per CLAUDE.md Principle #10 ("English-Only Commits") and VISION §6.1 ("All docs/comments in English"). Specific violations: (1) routing-execution `user_facing_message: "您输入的信用分 7200 超出有效范围（300-850），您是指 720 吗？"`; (2) a2a-protocol §6.3 clarification YAML — 5 lines of Chinese (`超出 FICO 范围`, `用户输入错误`, `数据源错误`, `强制使用`, `暂停，等待信用分澄清`); (3) mcp-api-protocol §1.3 diagram `send_message("我想贷款50万买房")`; (4) observability §1.3 diagram `统一面板` and `LLM 专项调试`. These are in the diff's ADDED lines, not pre-existing. | Translate all Chinese to English. If Chinese examples are needed for locale testing, move them to `docs/specs/zh/` (which is gitignored per `.gitignore`). |
| C2 | `version_skew` | 13-tool-ecosystem.md:528; 03-state-machine-design.md:323; 14-llm-gateway.md:1059 | **Cross-reference drift: §6.5 no longer contains errorNode strategies.** The routing-execution spec moved errorNode strategies from old §6.5 to new §6.6 ("Recovery Strategies (Canonical Definition — 8 Strategies)"). Old §6.5 is now "Structured Error Schema" (FrameworkError). Three specs still reference `Routing & Execution §6.5` for "canonical errorNode strategies": 13-tool-ecosystem.md:528 ("see [Routing & Execution §6.5]... for the canonical errorNode strategy definitions"), 03-state-machine-design.md:323 ("errorNode provides unified error handling, defined in [Routing & Execution §6.5]"), 14-llm-gateway.md:1059 ("For the canonical errorNode strategies, see [Routing & Execution §6.5]"). All now point to the wrong section. | Update all three cross-references from `§6.5` to `§6.6` (Recovery Strategies). The errorNode *interface* is now §6.8, and the *error schema* is §6.5 — references must disambiguate which they mean. |
| C3 | `semantic_conflict` | VISION.md:166-171 (§6.5 Error Handling) | **VISION §6.5 internally contradicts AD #15 (revised).** §6.5 still lists only 5 strategies: "ask_clarify, escalate_to_human, terminate, fallback_value, retry_with_context". AD #15 (revised 2026-06-25, same file line 104) explicitly expanded to 8 strategies (added `retry_with_backoff`, `graceful_degradation`, `dead_letter_queue`). Additionally, §6.5 says "no per-category dispatch" which is now misleading — AD #15 added a mandatory 3-type error classification (transient/permanent/partial) BEFORE strategy selection. The design-principles section was never updated to match the AD revision. | Update VISION §6.5 to: (1) list all 8 strategies, (2) add error classification step as a design principle, (3) clarify "no per-category *routing*" (classification is allowed; routing is always to errorNode). |

---

## High Issues

| # | Type | Section | Issue | Fix |
|---|------|---------|-------|-----|
| H1 | `version_skew` | 06-routing-execution-layer-design.md:698, 755, 911 | **Inline version references say "v0.5.0" but changelog says "v0.6.0".** Three inline tags reference the wrong version: §6.3 line 698 `> **New in v0.5.0.**`, §6.5 line 755 `> **New in v0.5.0.**`, §6.8 line 911 `# errorNode contract — v0.5.0`. The changelog entry for this overhaul is `0.6.0` (line 18). The v0.6.1 changelog entry (line 19) is the concurrency fix, not the error handling overhaul. | Change all three inline references from `v0.5.0` to `v0.6.0`. |
| H2 | `missing_coverage` | 14-llm-gateway.md:17 (changelog) vs §5 (lines 801-878) | **Changelog claims "Option E (Instructor)" added but it does not exist.** The v0.4.0 changelog states: "Added Instructor as recommended production implementation (Option E, per VISION §6.7 OSS-First)." However, §5 "Gateway Validation Strategies" contains only Options A (Provider-Native), B (Post-Process), C (Hybrid), D (Validator-Enhanced). There is no Option E. The changelog overstates what was delivered, and the §6.7 OSS-First requirement for the gateway is unmet. | Either (a) add Option E (Instructor) as a §5 implementation option with comparison-matrix entry, or (b) correct the changelog to remove the claim if it was deferred. |
| H3 | `version_skew` | 14-llm-gateway.md §4 section numbering | **Section §4.8 is missing — numbering skips §4.7 → §4.9.** The changelog says "Removed duplicate §4.7/§4.8" and §4.7 was repurposed for "Escalation Rate SLO". But the old §4.9 "Sticky Tier" was not renumbered to §4.8. Sequence is: §4.7 (Escalation Rate SLO), §4.9 (Sticky Tier), §4.10 (Pre-Call Checks). | Renumber §4.9 → §4.8 and §4.10 → §4.9. |
| H4 | `naming_drift` | 15-observability-monitoring.md:769 | **Orphaned table row — merge artifact.** Line 769 `| Best for | Teams with existing Kubernetes/Prometheus infrastructure; cost-sensitive deployments; open-source-first organizations |` is a leftover row from the OLD Option A table. It sits alone after a free-text paragraph (line 768 "Minimal deployment..."), disconnected from any table. The new §7.1 Option A table (lines 760-766) already has its own "Best for" row. | Delete line 769 (the orphaned row). |

---

## Medium Issues

| # | Type | Section | Issue | Fix |
|---|------|---------|-------|-----|
| M1 | `missing_cross_ref` | 11-mcp-api-protocol.md:239 | **Incorrect self-cross-reference.** The "Session Management" subsection says: "See [MCP API Protocol §1.3](#13-exposure-granularity--coarse-grained-by-design) for the separation of concerns." But §1.3 is "Exposure Granularity — Coarse-Grained by Design" (why internal tools aren't exposed). It does NOT discuss session-management vs conversation-state separation. The referenced section is about tool-exposure granularity, an unrelated topic. | Either remove the cross-reference or point to a section that actually discusses protocol-session vs conversation-state separation (may need to add this content). |
| M2 | `naming_drift` | 06-routing-execution-layer-design.md:908 | **errorNode interface lost its "Canonical Definition" designation.** The previous §6.5 was titled "errorNode Interface (Canonical Definition)" with the canonical-authority claim. After restructuring, §6.8 is titled only "errorNode Interface (Updated)" and lacks the canonical-authority statement. Meanwhile §6.6 (strategies) retained the "(Canonical Definition)" suffix. The errorNode *interface contract* should also be marked canonical since other specs reference it. | Rename §6.8 to "errorNode Interface (Canonical Definition)" and add the canonical-authority note (as §6.6 has). |
| M3 | `missing_coverage` | 06-routing-execution-layer-design.md §6.3-§6.12; 12-a2a-protocol.md §1.3, §3.2 | **New §6.7 OSS-First checklist item not satisfied for two modified specs.** VISION §7 now requires "at least one mature OSS library referenced as a recommended implementation option (per §6.7)". (1) routing-execution error handling additions (§6.3-§6.12) define DLQ backends (postgresql/redis/file) but frame them as config values, not as "wrap this OSS library" recommendations per §6.7. No OSS library is cited for structured error handling or DLQ patterns. (2) a2a-protocol §1.3/§3.2 additions reference "Google A2A Protocol" conceptually but list no mature OSS SDK as a recommended implementation option. | (1) For routing: add an OSS-first note referencing e.g. `tenacity` (retry library), `celery`/`dramatiq` (DLQ patterns), or similar. (2) For A2A: reference the official A2A Python SDK (or equivalent) as Option A in an implementation-options section. |
| M4 | `semantic_conflict` | 07-conversation-lifecycle.md:309 vs 06-routing-execution-layer-design.md:901 | **Audit-field list mismatch between two specs.** conversation-lifecycle §4.4 lists audit fields as "`messages`, `audit_log`" (2 fields). routing-execution §1.2 lists audit fields as "`messages`, `audit_log`, `llm_calls`" (3 fields). The routing spec added `llm_calls` as a third append-only audit field, but conversation-lifecycle was not updated to include it. | Add `llm_calls` to the audit-fields list in conversation-lifecycle §4.4 to match routing-execution §1.2. |

---

## Low Issues

| # | Type | Section | Issue | Fix |
|---|------|---------|-------|-----|
| L1 | `duplication` | 12-a2a-protocol.md:649-655 vs 06-routing-execution-layer-design.md:803-807 | **Root-cause chain rules duplicated across two specs.** A2A §6.3 "Root-Cause Chain Rules" (5 rules) and routing §6.5 "Design rules for root_cause chain" (4 rules) overlap significantly — same "append my_context, never modify root_cause" / "retryable inherits from deepest" / "correlation_id shared" rules. VISION §4.2 says "Don't duplicate. If a concept is defined in one spec, reference it; don't redefine." The A2A version adds A2A-specific rules (clarification flow, max_a2a_clarifications) but the base chain rules are restated. | A2A §6.3 should say "Same root-cause chain rules as Routing §6.5, plus the following A2A-specific extensions:" and only list the A2A-specific additions. |
| L2 | `version_skew` | 06-routing-execution-layer-design.md:741 | **"retained from v0.4.0" is correct but potentially confusing.** §6.4 says "The 7 error categories below are retained from v0.4.0 for audit logging." This is historically accurate (categories were introduced in v0.4.0) but a reader may wonder if the current document version is v0.4.0. Minor ambiguity given the version-skew issues in H1. | Reword to: "The 7 error categories below (introduced in v0.4.0) are retained for audit logging and are orthogonal to the three error types in §6.3." |
| L3 | `missing_cross_ref` | 14-llm-gateway.md:1121 | **LLM Gateway references VISION §6.5 which is now stale (see C3).** The References section says "[VISION.md] — §6.3 LLM Rules, §6.5 Error Handling". Since VISION §6.5 still lists 5 strategies (should be 8 per AD #15), this cross-reference points readers to stale information. | Fix is dependent on C3: once VISION §6.5 is updated, this reference is correct. No standalone action needed beyond C3. |

---

## Cross-Reference Map (Verified)

The following cross-references in the diff were checked and are **CORRECT** (no action needed):

- VISION AD #15 → "routing-execution §6.3–§6.10" ✓ (all sections exist)
- VISION AD #28 (revised) → state-machine §1.0 ✓ (matches UML statechart revision)
- VISION AD #31 (revised) → llm-gateway §4.2a/§4.2b/§4.2c ✓ (all exist)
- VISION AD #34 → §6.8 ✓ (LLM Positioning section exists)
- VISION AD #35 → mcp-api-protocol §1.3 ✓ (Exposure Granularity exists)
- a2a-protocol §2.2 → "Routing §6.5" for FrameworkError schema ✓ (§6.5 is now the schema)
- a2a-protocol §2.2 → "§6.3" for bidirectional clarification ✓ (§6.3 contains it)
- routing §6.5 → "see A2A §6.3" for trace store lookup ✓ (A2A §6.3 exists)
- intent-classification §5.2 → check_rates = ReadOnlyAgent ✓ (consistent with domain-model, extraction-layer, agent-types fixes)
- domain-model §5.1, extraction-layer §7.2, agent-types §2.1/§3 — all `check_rates` routing fixes are mutually consistent ✓

## Checklist Compliance (§7) for Modified Specs

| Spec | OSS-First (§6.7) | ≥2 Options | Comparison Matrix | Changelog | Open Questions | Cross-Ref |
|------|------------------|------------|-------------------|-----------|----------------|-----------|
| routing-execution | ❌ (see M3) | ✅ (§2.4, §3.2) | ✅ | ✅ | ✅ | ❌ (see C2) |
| a2a-protocol | ❌ (see M3) | ✅ (§3.2) | ✅ (§3.2) | ✅ | — | ✅ |
| llm-gateway | ❌ (see H2) | ✅ (§5 A-D) | ✅ (§5.4) | ❌ (see H2) | ✅ | ✅ |
| observability | ✅ (OTel) | ✅ (§7 A-C) | ✅ (§7.4) | ✅ | — | ✅ |
| mcp-api-protocol | ✅ (MCP SDK) | ✅ (§6.1) | ✅ (§6.1) | ✅ | — | ⚠️ (see M1) |
| state-machine | ✅ (LangGraph) | ✅ | ✅ | ✅ | ✅ | ❌ (see C2) |
