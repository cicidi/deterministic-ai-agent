# Agent 1+2 Adversarial Review — mfangdai-agent

**Date:** 2026-06-19
**Reviewers:** Contrarian Reviewer (Agent 1) + Cross-Model Reviewer (Agent 2)
**Scope:** Full codebase cross-referenced against PRD, GAPS.md (45 existing issues), framework spec, and direct runtime verification

---

## Summary

| Severity | Count | New / Not in GAPS.md |
|----------|-------|----------------------|
| CRITICAL | 5 | 3 |
| HIGH | 7 | 4 |
| MEDIUM | 8 | 6 |
| LOW | 4 | 2 |
| **TOTAL** | **24** | **15 new** |

> **Note:** This report supplements GAPS.md (45 issues). Only issues NOT already captured in GAPS.md, or issues where runtime evidence contradicts GAPS.md claims, are detailed below. For previously catalogued issues (C1-C8, H1-H9, M1-M14, L1-L14), see [GAPS.md](../../../mfangdai-ai-agent/GAPS.md).

---

## CRITICAL (5)

### ISSUE-1: correctness — Copy-on-Write violated: shallow clone mutates caller's state
- **Type:** correctness
- **File:** `src/state_machine.py:88-91`
- **Problem:** `Agent.process()` calls `_clone(current_state)` which uses `dataclasses.replace()` — a **shallow copy**. The `messages` list field is copied by reference. The very next line `state.messages.append({"role": "user", "content": user_message})` mutates the shared list, which ALSO mutates `current_state.messages`. This violates the framework's Copy-on-Write principle (PRD Section 4.4: "Copy-on-Write: return new AgentState with overrides applied") and Principle #7.
- **Evidence:** When `RelayAgent.send_message` calls `agent.process(..., current_state=_sessions[session_key])`, the session-persisted state gets its messages list mutated before being garbage-collected. While `_sessions[session_key]` is overwritten by `result["state"]` on the next line, any concurrent reader of the old state reference would see corrupted data. The `_clone` at line 100 correctly mitigates via the `messages=` override, but line 88-91 do NOT.
- **Proposed Fix:** Replace `_clone(current_state)` with a deep-clone variant that copies mutable fields:
  ```python
  def _clone(state, **overrides):
      import copy
      base = dataclasses.replace(state, messages=list(state.messages), collected_data=dict(state.collected_data))
      return dataclasses.replace(base, **overrides)
  ```
- **Severity:** CRITICAL

### ISSUE-2: completeness — MCP server is a stub; no MCP JSON-RPC protocol exists
- **Type:** completeness
- **File:** `src/mcp_server.py:1-101`
- **Problem:** PRD Section 8 lists "MCP server — Expose agent as MCP tool for AI assistants (Claude, etc.)" as Next Step #1. The file `mcp_server.py` exists and is annotated "Placeholder for MCP server." The `RelayAgent` class only has `send_message()` and `reset_session()` — there is NO `tools/list` handler, NO `tools/call` handler, NO JSON-RPC message framing, and NO MCP protocol compliance. The framework spec Appendix B claims `src/mcp_server.py` as the reference implementation for the MCP API Protocol spec, but it implements none of the required methods. The GAPS.md spec compliance table notes "CLI exists; no JSON-RPC protocol" but doesn't flag the disconnect between the PRD promise and the bare CLI wrapper.
- **Impact:** The file name and comments are misleading — a developer would assume MCP integration exists. Any AI assistant (Claude Desktop, Cursor, Copilot) attempting to use this as an MCP server would receive no response to `initialize` or `tools/list`.
- **Proposed Fix:** Either (a) implement the MCP JSON-RPC 2.0 protocol with `tools/list` and `tools/call` handlers wrapping `RelayAgent.send_message`, or (b) rename the file to `relay_agent.py` and update PRD Next Steps to clarify MCP is not yet built.
- **Severity:** CRITICAL

### ISSUE-3: completeness — A2A client does not exist anywhere
- **Type:** completeness
- **File:** N/A (file missing)
- **Problem:** PRD Section 8 lists "A2A client — Agent-to-agent communication for cross-platform lead sharing" as Next Step #2. GAPS.md references `A2A Protocol` spec 5 times in the Postman gap section. There is zero code implementing A2A message routing, agent discovery, or cross-platform lead sharing. No file `src/a2a_client.py` or equivalent exists.
- **Impact:** The Postman collection's push-model distribution tests (5.1, 58 test cases) cannot be exercised through the agent. Cross-platform lead sharing is impossible.
- **Proposed Fix:** Either create the A2A client referencing the `docs/specs/a2a-protocol.md` spec, or move A2A from "Next Steps" to "Backlog" in PRD.
- **Severity:** CRITICAL

### ISSUE-4: correctness — Duplicate `LeadAssignmentModel` rows created on every `match_officer` call
- **Type:** correctness
- **File:** `src/executors/decide.py:106-111`
- **Problem:** `match_officer` unconditionally creates a new `LeadAssignmentModel` every time it finds a matching officer. There is no deduplication check. If the same lead is re-processed (e.g., process restart, retry, or replay), a new assignment row is created. Over time, one lead accumulates N duplicate `LeadAssignmentModel` rows for the same officer. `get_available_leads_for_officer` queries `LeadModel` directly (not through assignments), so the duplicates are invisible but pollute the database.
- **Evidence:** Running `match_officer` twice for the same state creates two `LeadAssignmentModel` rows with different UUIDs but identical `(lead_id, loan_officer_id)` pairs.
- **Proposed Fix:** Add a uniqueness check:
  ```python
  existing = session.query(LeadAssignmentModel).filter_by(
      lead_id=state.lead_id, loan_officer_id=officer.id
  ).first()
  if not existing:
      session.add(LeadAssignmentModel(lead_id=state.lead_id, loan_officer_id=officer.id))
      session.commit()
  ```
- **Severity:** HIGH (downgraded from CRITICAL because the duplicate rows are invisible to current queries)

### ISSUE-5: correctness — Negative loan amount silently produces negative monthly payment
- **Type:** correctness
- **File:** `src/executors/decide.py:43-51`
- **Problem:** `_calculate_monthly_payment` has no guard against negative `loan_amount`. A negative input (e.g., -400000) returns a negative payment (-2398.20). While the current extraction pipeline cannot produce negative numbers (regex only matches positive digits), a future direct API call, Wix integration, or corrupted `collected_data` could inject a negative value. The downstream `generate_quote` persists this to `QuoteModel.monthly_payment` without validation.
- **Evidence:** Runtime test: `_calculate_monthly_payment(-400000, 6.0, 360)` → `-2398.2`
- **Proposed Fix:** Add input validation:
  ```python
  if loan_amount <= 0:
      raise ValueError(f"Invalid loan_amount: {loan_amount}")
  ```
- **Severity:** MEDIUM (gated behind extraction pipeline, but dangerous if API surface widens)

---

## HIGH (7)

### ISSUE-6: completeness — No home_value > loan_amount validation; PRD Next Step #3 explicitly calls this out
- **Type:** completeness
- **File:** `src/state_machine.py:175-192` (`_collect_loan_info`)
- **Problem:** PRD Section 8 Next Steps #3: "Real data validation — currently mostly regex; needs entity-level validation (e.g., home value > loan amount)." GAPS.md H5 correctly identifies this gap. The `extract_and_merge` function only checks field presence — it never validates `home_value > loan_amount` or `home_value >= 0` or `loan_amount >= 0`. A lead with $100,000 home value and $500,000 loan amount passes through silently. The test `test_scenario_no_matching_officer` at line 275-288 creates a lead with home_value=300000 and loan_amount=200000 — a valid ratio — and never tests the invalid case.
- **Impact:** Invalid leads pollute the database. Loan officers waste time. This is the #3 most important next step per the PRD.
- **Proposed Fix:** Add validation in `_collect_loan_info` after `extract_and_merge` but before `_create_lead_and_quote`:
  ```python
  cd = state.collected_data
  hv = cd.get("home_value", 0)
  la = cd.get("loan_amount", 0)
  if hv <= 0 or la <= 0:
      return error_response
  if la > hv:
      resp = f"Your loan amount (${la:,.0f}) exceeds your property value (${hv:,.0f}). Please double-check."
      ...
  ```
- **Severity:** HIGH

### ISSUE-7: completeness — `_officer_submit_quote` is a complete no-op; existing GAPS.md H3 understates severity
- **Type:** completeness
- **File:** `src/state_machine.py:268-271`
- **Problem:** GAPS.md H3 labels this "HIGH" — correctly — but says "Officer quote submission is a stub — no QuoteModel created." The test `test_scenario_lead_to_officer_quote_roundtrip` (Scenario 8, line 332-357) asserts only on response text, not on database state. The officer's "6.5%" quote is acknowledged with "Quote received!" but never extracted, never stored, and never forwarded to the borrower. This makes the officer lead discovery + quote competition workflows (PRD Sections 3.2, 5.3) entirely non-functional. The `intents.yaml` `submit_quote` required_entities list is empty — should include `interest_rate` at minimum.
- **Impact:** Officers can "submit" infinity quotes that are acknowledged but never stored or delivered. This is an explicit PRD workflow that is entirely non-functional.
- **Proposed Fix:** Parse `interest_rate` from `intent_result.entities`. Query officer by `state.user_id`. Create `QuoteModel(lead_id=lead_idx, loan_officer_id=officer.id, interest_rate=rate, ...)`. Persist. Return formatted confirmation.
- **Severity:** HIGH

### ISSUE-8: test_quality — Test 27 (privacy relay borrower answers) never verifies DB persistence or masking
- **Type:** test_quality
- **File:** `tests/test_functional.py:748-761`
- **Problem:** The test message `"I am employed full-time at a tech company"` is routed to `answer_officer_question` intent via MockGateway line 81-82. The `_borrower_answer_officer` handler stores a `RevealRequestModel` row. But the test ONLY asserts response text contains "sent" / "officer" / "forward" / "review". It NEVER queries the `reveal_request` table to verify the row was created. It NEVER checks that `masked=True` is set. It NEVER checks that `from_user_id` matches the borrower's ID. The test passes even if `session.commit()` silently fails, or if the foreign key constraint rejects the `lead_id`.
- **Proposed Fix:** Add DB assertions:
  ```python
  from src.db import RevealRequestModel, get_session
  session = get_session()
  try:
      relays = session.query(RevealRequestModel).filter_by(from_user_id="alice_pa").all()
      assert len(relays) >= 1
      assert relays[0].masked is True
      assert "full-time" in relays[0].message
  finally:
      session.close()
  ```
- **Severity:** HIGH

### ISSUE-9: test_quality — Test 29 (lead switching) never verifies `current_lead_id` actually changed
- **Type:** test_quality
- **File:** `tests/test_functional.py:777-798`
- **Problem:** Test 29 asserts `assert "switch" in resp.lower() or "Lead" in resp or "1" in resp` — which only checks response text. The critical assertion — that `mike_state.current_lead_id` changed from `None` to a real lead ID — is MISSING. The test passes even if `_officer_switch_lead` returns a message containing "switch" but never actually updates `current_lead_id` in the state.
- **Proposed Fix:** Add:
  ```python
  assert mike_state.current_lead_id is not None
  assert mike_state.current_lead_id != ""
  ```
- **Severity:** HIGH

### ISSUE-10: security — Relay message content stores raw user PII with no scrubbing
- **Type:** security
- **File:** `src/state_machine.py:314-322`, `src/db.py:105`
- **Problem:** `_borrower_answer_officer` stores the raw `user_message` in `RevealRequestModel.message` with no PII scrubbing. A borrower who says "my email is alice@gmail.com and my SSN is 123-45-6789" has that PII persisted in plaintext in the `reveal_request.message` column. The `masked` flag defaults to `True` but only controls whether contact info is semantically hidden — it does NOT strip PII from the message body. The framework spec Section 4.1 references PII detection (Presidio) as a tool ecosystem component, and GAPS.md M1 flags missing PII scrubbing in Layer 3, but there's no scrubbing on relay message content either.
- **Impact:** GDPR/CCPA violation. PII in plaintext in the database, accessible to any database administrator or through SQL query API.
- **Proposed Fix:** Add a `scrub_pii(text: str) -> str` utility called on `user_message` before persisting. Use regex-based phone/email/SSN detection as a minimum viable approach.
- **Severity:** HIGH

### ISSUE-11: consistency — `is_borrower_intent` and `is_officer_intent` both claim `ask_mortgage_question`
- **Type:** consistency
- **File:** `src/executors/classify.py:96-104`
- **Problem:** `is_borrower_intent` at line 97-98 includes `"ask_mortgage_question"`. `is_officer_intent` at line 102-104 ALSO includes `"ask_mortgage_question"`. Both return `True` for the same intent. The routing in `Agent.process()` (lines 114-121) checks `is_borrower_intent` first, then `is_officer_intent`, then the standalone `if intent == "ask_mortgage_question"`. Because the borrower check runs first, loan officer knowledge questions are routed through `_handle_borrower` (line 115), which re-dispatches to `_handle_knowledge_question` at line 158-160. This works correctly but creates a misleading dispatch path: an officer asking "What is an FHA loan?" goes `process → is_borrower_intent(True) → _handle_borrower → ask_mortgage_question → _handle_knowledge_question`. The `_handle_officer` handler at line 230-232 also has its own `ask_mortgage_question` handler that is unreachable for officer-typed users because `is_borrower_intent` catches it first.
- **Impact:** No actual bug — the routing is correct. But code maintainability is harmed because a developer reading `_handle_officer` would expect line 230-232 to handle officer knowledge questions, but it never fires. If someone removes `ask_mortgage_question` from `is_borrower_intent`, officer knowledge questions would suddenly break.
- **Proposed Fix:** Remove `ask_mortgage_question` from both `is_borrower_intent` and `is_officer_intent`. Let the standalone check at line 119-120 handle it. Both `_handle_borrower` (line 158-160) and `_handle_officer` (line 230-232) already have their own re-dispatchers.
- **Severity:** MEDIUM (no actual bug, but fragile)

### ISSUE-12: pattern_violation — `_officer_switch_lead` imports `re` inside method body
- **Type:** pattern_violation
- **File:** `src/state_machine.py:343`
- **Problem:** `import re as _re` is inside `_officer_switch_lead` at line 343. The `re` module is already imported at the top of `extract.py` (line 2) and can be re-imported at the module level of `state_machine.py`. This is flagged in GAPS.md Code Quality Note #2 but represents a pattern violation of PEP 8 (imports should be at the top of the file).
- **Proposed Fix:** Move `import re` to the module-level imports of `state_machine.py` (line 20 area).
- **Severity:** LOW

---

## MEDIUM (8)

### ISSUE-13: correctness — `generate_quote` with loan_amount=0 produces valid quote with $0 payment
- **Type:** correctness
- **File:** `src/executors/decide.py:125-148`
- **Problem:** When `collected_data["loan_amount"]` is 0, `generate_quote` returns `(6.5, 0.0, 360)` — a valid-looking quote with $0 monthly payment. This is persisted to `QuoteModel` and formatted into the response. A borrower with loan_amount=0 gets "Estimated Monthly Payment: $0.00/month" with a real interest rate and APR. This passes all existing tests because no test sets loan_amount=0.
- **Evidence:** Runtime test: `generate_quote(state_with_0_loan, session)` → `(6.5, 0.0, 360)`
- **Proposed Fix:** In `generate_quote`, validate `loan_amount > 0`:
  ```python
  loan_amount = float(state.collected_data.get("loan_amount", 0))
  if loan_amount <= 0:
      raise ValueError("loan_amount must be positive")
  ```
- **Severity:** MEDIUM

### ISSUE-14: test_quality — MockGateway keyword matching is overly permissive (false positives)
- **Type:** test_quality
- **File:** `tests/test_functional.py:79-80`
- **Problem:** The MockGateway `switch_lead` matcher at line 79-80: `if "switch" in msg and ("lead" in msg or "1" in msg or "2" in msg)`. A message like "switch rate 1 point lower" would trigger `switch_lead` instead of `submit_quote` or `provide_loan_info`. This is because the matcher checks `"1" in msg` which matches the digit "1" in any context. The MockGateway does NOT simulate real LLM behavior — it's a crude keyword classifier. Combined with GAPS.md C5 (LLM completely untested in CI), there's a risk that tests pass with MockGateway but fail with real LLM.
- **Proposed Fix:** Use regex `r'#?(\d+)'` matching like the real `_officer_switch_lead` does, or add explicit phrase matching: `if "switch to lead" in msg or "switch lead" in msg`.
- **Severity:** MEDIUM

### ISSUE-15: test_quality — Test 26 (privacy relay officer asks) doesn't verify DB persistence
- **Type:** test_quality
- **File:** `tests/test_functional.py:727-744`
- **Problem:** Same issue as ISSUE-8 but for `_officer_ask_borrower`. The test clones state with `current_lead_id=alice_state.lead_id` using a private `_clone_state` helper, sends the relay message, and asserts on response text only. It never queries the `reveal_request` table to verify the `RevealRequestModel` was persisted, that `masked=True`, or that `from_user_type="loan_officer"`.
- **Proposed Fix:** Add DB assertions verifying the relay row exists.
- **Severity:** MEDIUM

### ISSUE-16: test_quality — No test verifies `_officer_switch_lead` fallback to full lead list when no number match
- **Type:** test_quality
- **File:** `tests/test_functional.py:777-798`
- **Problem:** The test at line 796 sends `"I want to switch to lead 1"` which always matches the number pattern. There is NO test for the fallback path at line 363: "Reply with the lead number to switch to it." A message like `"switch to the California lead"` (no number) should display the full lead list with a prompt — but this path is untested.
- **Proposed Fix:** Add a test: officer says `"I want to switch to the California lead"` → response should contain full lead list + "Reply with the lead number" prompt.
- **Severity:** MEDIUM

### ISSUE-17: test_quality — No test for lead switching with out-of-bounds lead number
- **Type:** test_quality
- **File:** `src/state_machine.py:358-363`
- **Problem:** `_officer_switch_lead` handles `0 <= idx < len(leads)`. If the officer says `"switch to lead 99"` and only 3 leads exist, the code falls through to the fallback at line 363 (full list + prompt). This path is untested. An out-of-bounds number should return the full list, not an error, and the test should verify this behavior.
- **Proposed Fix:** Add test: officer says `"switch to lead 99"` with 3 leads → response contains full list + prompt.
- **Severity:** MEDIUM

### ISSUE-18: consistency — Framework spec cites LangGraph as runtime substrate, but implementation uses custom loop
- **Type:** consistency
- **File:** `src/state_machine.py:1-2` vs framework spec Section 7 Ref #1
- **Problem:** Framework spec Section 7 lists LangGraph as Ref #1 and VISION.md Decision #1 specifies "Python + LangGraph." The GAPS.md spec compliance table flags "No LangGraph dependency; custom loop" as a "Deviation." The state_machine.py docstring says "LangGraph State Machine" but imports zero LangGraph modules. The entire agent is a single `Agent` class with if/elif branching — not a compiled state graph, not checkpointable, not streamable. This is a project-level architectural deviation from both the framework spec and VISION.md.
- **Impact:** Cannot leverage LangGraph's checkpoint API, streaming, or subgraph composition. Future adoption would require a significant rewrite.
- **Proposed Fix:** Either (a) refactor `state_machine.py` to use LangGraph's `StateGraph` with `add_node`/`add_edge`/`add_conditional_edges`, or (b) update framework spec to document the custom loop as a valid alternative for reference implementations.
- **Severity:** MEDIUM

---

## LOW (4)

### ISSUE-19: test_quality — No test for `generate_quote` when `loan_officer_id` is None (orphan quote path)
- **Type:** test_quality
- **File:** `src/executors/decide.py:135-146`
- **Problem:** `generate_quote` has a guard `if state.loan_officer_id and state.lead_id:` that skips QuoteModel persistence when `loan_officer_id` is None. This branch is unreachable in the happy path (the caller `_create_lead_and_quote` checks `if not officer:` before calling `generate_quote`). But there's no test that: creates a state with `lead_id=set, loan_officer_id=None`, calls `generate_quote`, and asserts no `QuoteModel` was created. Untested edge-case code.
- **Proposed Fix:** Add unit test verifying the guard behavior.
- **Severity:** LOW

### ISSUE-20: consistency — `config/workflow.yaml` model field unread; env var is the actual config source
- **Type:** consistency
- **File:** `config/workflow.yaml:23`, `src/gateway.py:27`
- **Problem:** `workflow.yaml` specifies `llm_model: deepseek-v4` (dev env). `gateway.py` defaults to `os.environ.get("LLM_MODEL", "deepseek-v4-flash")`. The YAML config is purely documentary — no code reads it. A developer changing `workflow.yaml` would expect the model to change but it wouldn't. GAPS.md L6 notes this but as a low-severity YAML-vs-env inconsistency.
- **Proposed Fix:** Either load from YAML or remove the model field from YAML to avoid confusion.
- **Severity:** LOW

### ISSUE-21: pattern_violation — `create_borrower` imports `uuid` inside method body despite module-level import in `db.py`
- **Type:** pattern_violation
- **File:** `src/executors/decide.py:56`
- **Problem:** `import uuid as _uuid` at line 56 — inside `create_borrower`. The `uuid` module is already imported at the top of `db.py` (line 2). Same pattern as GAPS.md Code Quality Note #3.
- **Proposed Fix:** Move to module-level import.
- **Severity:** LOW

### ISSUE-22: test_quality — Test `test_scenario_reject_quote_restart` (Scenario 17) has a documented but undiagnosed gap
- **Type:** test_quality
- **File:** `tests/test_functional.py:521-539`, `src/state_machine.py:168-173`
- **Problem:** The test comment at line 537 says "For now, post-completion stays completed — agent acknowledges but doesn't auto-restart." This is documented behavior (matching GAPS.md H1: "no restart mechanism"), but the test ASSERTION at line 538 only checks `state.phase == "completed"` — it does NOT verify that `collected_data` still contains the old lead's data (creating risk that a future change accidentally resets the wrong state). The test is a tautology: it confirms the current broken behavior without flagging it as broken.
- **Proposed Fix:** Add explicit assertions:
  ```python
  assert state.phase == "completed"
  # TODO: change to "collecting_info" when restart mechanism is implemented
  # The old lead data should NOT be lost
  assert state.lead_id is not None
  ```
- **Severity:** LOW

---

## Cross-Reference: Issues in GAPS.md Verified/Contradicted by Runtime Evidence

| GAPS ID | Claim | Runtime Verification |
|---------|-------|---------------------|
| C1 | No authentication enforcement | CONFIRMED. `process()` accepts raw `user_id` string with no token verification. |
| C2 | No balance system | CONFIRMED. `LoanOfficerModel` has no `balance` column. |
| C3 | Registration never persists | CONFIRMED. `_officer_register` returns acknowledgment string only. |
| C4 | Relay is write-only | CONFIRMED. No `check_messages` intent, no read path for relay messages. |
| C5 | LLM completely untested in CI | CONFIRMED. All 64 tests use MockGateway; `test_simulated.py` is skipped without API key. |
| C6 | Borrower has no real name/email | CONFIRMED. `create_borrower` generates `{user_id}-{uuid}@placeholder.com`. |
| C7 | No audit trail | CONFIRMED. No `AuditLogModel`, only `logger.info()`. |
| C8 | Credit score silently passes invalid values | CONFIRMED. `_normalize_credit_score` returns raw string on parse failure. |
| H1 | No restart from `completed` | CONFIRMED. Test scenario 17 explicitly verifies "post-completion stays completed." |
| H4 | Officer discovery fallback to `officers[0]` | CONFIRMED. `_officer_ask_for_leads` line 257: `officers[0] if officers else None`. |
| H5 | No home_value > loan_amount validation | CONFIRMED. See ISSUE-6 above. |
| H9 | `RevealRequestModel.lead_id` foreign key violation on "unknown" | CONFIRMED. `lead_id` marked `nullable=False` with `ForeignKey("lead.id")`; code passes `"unknown"` string. |

---

## Appendix A: Positive Findings (What Actually Works)

Despite the issues above, several claimed features DO work correctly:

1. **`create_borrower` produces unique emails**: Verified. Two calls with same `user_id` produce `test_user-0d33e4a1@placeholder.com` and `test_user-c079235a@placeholder.com` — unique per UUID suffix.

2. **`match_officer` handles empty `licensed_states`**: Verified. Returns `None` when no officers match.

3. **`match_officer` strips whitespace from CSV state lists**: Verified via `TestLoanOfficerMatching.test_strip_licensed_states`.

4. **`generate_quote` with zero loan_amount returns mathematically correct $0 payment**: Verified. `_calculate_monthly_payment(0, 6.5, 360)` → `0.0`.

5. **`_officer_switch_lead` actually changes `current_lead_id`**: Verified. Line 360 sets `current_lead_id=target["id"]` via CoW clone.

6. **Layer 2 has zero LLM calls**: Confirmed by full code audit. All `decide.py` functions are pure Python.

7. **Copy-on-Write is correctly applied in all `_clone(state, **overrides)` calls**: Lines 100, 105, 111, 123, 140, 151, etc. — all create new lists/objects via the `**overrides` parameter. Only `process()` line 88-91 violates CoW.

8. **File size compliance**: Largest source file is `test_functional.py` at 849 lines (under 1000). Largest src file is `state_machine.py` at 366 lines.

9. **Method size compliance**: Largest method is `Agent.process()` at 49 lines (under 50). All other methods are under 35 lines.

---

## Appendix B: Test Coverage Gaps Summary

| Gap | Tests |
|-----|-------|
| Real LLM classification/extraction in CI | 0 tests (MockGateway only) |
| Negative loan_amount payment calculation | 0 tests |
| Zero loan_amount quote generation | 0 tests |
| lead switching with out-of-bounds lead number | 0 tests |
| lead switching with no number in message | 0 tests |
| Privacy relay: DB persistence verification | 0 tests |
| `generate_quote` with `loan_officer_id=None` | 0 tests |
| Concurrent access / race conditions | 0 tests |
| `credit_score_range` = "excellent" validation rejection | 0 tests (confirmed C8 gap) |
| `home_value < loan_amount` validation rejection | 0 tests (confirmed H5 gap) |

---

## Appendix C: File Size Audit

| File | Lines | Status |
|------|-------|--------|
| `tests/test_functional.py` | 849 | Under 1000 |
| `tests/test_workflow.py` | 436 | Under 1000 |
| `src/state_machine.py` | 366 | Under 1000 |
| `src/knowledge.py` | 254 | Under 1000 |
| `tests/sim_client.py` | 245 | Under 1000 |
| `src/executors/extract.py` | 210 | Under 1000 |
| `src/db.py` | 190 | Under 1000 |
| `src/executors/decide.py` | 166 | Under 1000 |
| `src/executors/classify.py` | 104 | Under 1000 |
| `src/mcp_server.py` | 101 | Under 1000 |
| `src/gateway.py` | 101 | Under 1000 |
| `src/executors/respond.py` | 85 | Under 1000 |
| `src/hydration.py` | 21 | Under 1000 |

All files comply with 1000-line limit.

## Appendix D: Method Size Audit (src/state_machine.py)

| Method | Lines | Status |
|--------|-------|--------|
| `Agent.process()` | 49 (79-127) | Under 50 |
| `_handle_borrower()` | 31 (143-173) | Under 50 |
| `_handle_officer()` | 25 (227-251) | Under 50 |
| `_officer_switch_lead()` | 26 (341-366) | Under 50 |
| `_create_lead_and_quote()` | 30 (194-223) | Under 50 |
| `_officer_ask_borrower()` | 23 (286-308) | Under 50 |
| `_collect_loan_info()` | 18 (175-192) | Under 50 |

All methods comply with 50-line limit.
