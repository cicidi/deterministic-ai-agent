# Contrarian Review Summary — 2026-07-02

## Overview

| Metric | Value |
|--------|-------|
| Agents launched | 3 (Agent 0, 1, 2) |
| Agents completed | 2 (Agent 0, 1) — Agent 2 returned empty, findings synthesized by coordinator |
| Total issues raised | 31 (14 from Agent 0, 17 from Agent 1) |
| Unanimous | 6 (both agents independently identified) |
| Accepted | 28 |
| Rejected | 0 |
| Deferred | 10 (valid but needs architect discussion or major restructuring) |
| Fix now | 18 |

## Rulings

### ACCEPT — FIX NOW (18 issues)

| # | Source | Issue | Severity | Ruling |
|---|--------|-------|----------|--------|
| R1 | A0-C1 | Chinese text in 4 committed specs | CRITICAL | Translate all Chinese to English |
| R2 | A0-C2 | Cross-ref drift: §6.5 → §6.6 for errorNode strategies (3 specs) | CRITICAL | Update all 3 cross-references |
| R3 | A0-C3 | VISION §6.5 lists 5 strategies, AD #15 defines 8 | CRITICAL | Update §6.5 to match AD #15 |
| R4 | A0-H1 | Inline version refs say v0.5.0, changelog says v0.6.0 | HIGH | Fix all 3 inline refs |
| R5 | A0-H2 | Changelog claims "Option E (Instructor)" but it doesn't exist | HIGH | Correct changelog (remove false claim) |
| R6 | A0-H3 | llm-gateway §4.8 missing (skips §4.7 → §4.9) | HIGH | Renumber §4.9 → §4.8, §4.10 → §4.9 |
| R7 | A0-H4 | Orphaned table row in observability (merge artifact) | HIGH | Delete line 769 |
| R8 | A0-M1 | mcp-api-protocol incorrect self-cross-reference | MEDIUM | Remove or fix cross-reference |
| R9 | A0-M2 | errorNode interface lost "Canonical Definition" designation | MEDIUM | Restore canonical designation to §6.8 |
| R10 | A0-M4 | Audit-field list mismatch (conversation-lifecycle missing llm_calls) | MEDIUM | Add llm_calls to conversation-lifecycle §4.4 |
| R11 | A0-L1 | Root-cause chain rules duplicated in a2a-protocol + routing-execution | LOW | A2A should reference routing, not restate |
| R12 | A0-L2 | "retained from v0.4.0" potentially confusing wording | LOW | Reword |
| R13 | A1-H6/A0-M3 | Routing §6 has zero OSS references (VISION §6.7 violation) | HIGH | Add implementation options subsection |
| R14 | A1-L13 | MCP Streamable HTTP security warnings underemphasized | LOW | Add security requirements subsection |
| R15 | A1-L15 | Instructor not referenced for retry_with_context | LOW | Add Instructor reference |
| R16 | A1-M9 | OTel Logs SDK is Development status, not Stable | MEDIUM | Clarify in §1.3 |
| R17 | A1-L12 | structlog vs loguru comparison missing | LOW | Add brief note |
| R18 | A0-L3 | llm-gateway references stale VISION §6.5 | LOW | Fixed by R3 |

### ACCEPT — DEFER (10 issues, needs architect discussion or major restructuring)

| # | Source | Issue | Severity | Ruling |
|---|--------|-------|----------|--------|
| D1 | A1-C1 | LangGraph native fault tolerance reinvented (retry_policy, error_handler) | CRITICAL | Defer: spec should wrap LangGraph native, but this is a major §6 restructuring. Record as open question + AD entry. |
| D2 | A1-C2 | LiteLLM Router already implements two-layer escalation + budgets | CRITICAL | Defer: add LiteLLM as Option A in gateway implementation options. Major restructuring. |
| D3 | A1-H3 | SAGA/compensation pattern missing from 8 strategies | HIGH | Defer: add as open question. Needs architect input on fintech rollback semantics. |
| D4 | A1-H4 | FrameworkError schema reinvents gRPC + OTel error standards | HIGH | Defer: add cross-references to gRPC status codes and OTel exception conventions. |
| D5 | A1-H5 | 3-type error taxonomy loses gRPC's 17-status-code granularity | HIGH | Defer: document error_code → gRPC code mapping table. |
| D6 | A1-M7 | DLQ unconventional for synchronous conversational AI | MEDIUM | Defer: reframe DLQ scope to async write operations only. |
| D7 | A1-M8 | Circuit breaker underemphasized; bulkhead pattern missing | MEDIUM | Defer: elevate circuit breaker to named section. |
| D8 | A1-M10 | Camp B "architecturally superior" overstates; Anthropic endorses spectrum | MEDIUM | Defer: soften language. Acknowledge spectrum. |
| D9 | A1-M11 | Coarse-grained MCP send_message limits ecosystem participation | MEDIUM | Defer: strengthen trade-off documentation. |
| D10 | A1-L16 | Helicone not evaluated for cost management | LOW | Defer: add to comparison matrix. |

### REJECTED (0 issues)

All findings are valid. No rejections.

## Key Insights

1. **The diff contains significant high-quality work** — SCXML→UML revision, MCP upgrade, two-layer escalation concept, structlog adoption, error classification taxonomy are all sound.

2. **The biggest gap is OSS-First compliance (VISION §6.7)** — routing §6 (error handling) and llm-gateway §4 (escalation) reinvent mature OSS (LangGraph fault tolerance, LiteLLM Router) without referencing them as recommended implementations. This is the #1 priority for the next spec revision.

3. **Mechanical errors are fixable now** — Chinese text, cross-reference drift, version numbers, orphaned rows are all quick fixes that should be applied before commit.

4. **The framework's policy layer is valid** — error classification, strategy decision matrix, audit-field locking are legitimate framework value-adds ON TOP of OSS. The fix is to document the boundary, not remove the policy.
