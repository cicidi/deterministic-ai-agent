# Three-Tier Test Strategy — mfangdai-agent

**Date:** 2026-06-19
**Status:** Design approved, pending implementation

## 1. Architecture

```
Tier 1 (done, 65 pass): Logic Tests
  Client: hardcoded strings        Server: MockGateway (keyword)
  Purpose: verify code logic, state machine, DB persistence

Tier 2 (new): LLM Accuracy Tests
  Client: pre-written scripts      Server: real LLM (DeepSeek/GPT)
  Purpose: verify LLM correctly classifies + extracts from realistic messages

Tier 3 (new): End-to-End Completion Tests
  Client: LLM (SimClient persona)  Server: real LLM
  Purpose: measure completion rate, turn count, loop detection
  Also: borrower↔officer indirect communication via agent
```

## 2. Tier 2 Design

### Architecture
```
ScriptedClient ──hardcoded msg──► Server Agent (real LLM)
                 ◄──response────
```

### Test Structure
```python
# tests/test_tier2.py

TIER2_SCRIPTS = {
    "B1_purchase_ca": [
        ("Hi, I want to check mortgage rates", "expect_phase=collecting_info"),
        ("I'm buying a new home", "expect_loan_purpose=purchase"),
        ("My property is worth about $500,000", "expect_home_value=500000"),
        ("I need to borrow $300,000", "expect_loan_amount=300000"),
        ("The property is in California", "expect_state=CA"),
        ("My credit score is around 720", "expect_phase=completed"),
    ],
}
```

### Metrics per script
- `intent_accuracy`: % turns where LLM intent matches expected
- `entity_extraction_rate`: % required entities extracted
- `turn_count`: expected vs actual
- `false_positive_intents`: misclassifications

### Assertions per script
- `phase == "completed"` at end
- `quote is not None` for borrower flows
- `lead_id is not None`
- Agent never returned error phase

## 3. Tier 3 Design

### Architecture
```
SimClient (LLM persona) ──natural msg──► Server Agent (real LLM)
                         ◄──response────
```

### Run configuration
- Each persona runs 3-5 times to measure consistency
- Max turns per run: 15
- Loop detection: same intent/response repeating >3 turns → failure

### Metrics per persona
- `completion_rate`: % runs that reach phase=completed
- `avg_turn_count`: mean turns to completion
- `loop_count`: number of runs that entered a loop
- `error_rate`: % runs that hit error phase

### Indirect communication (deferred to expansion)
```
Borrower (LLM) → Agent → Loan Officer (LLM)
Borrower (LLM) ← Agent ← Loan Officer (LLM)
```
Agent masks contacts, enforces payment gate.

## 4. Scenario Catalog — MVP (20 scenarios)

### Borrower (12)
| # | Name | Type | Key Test |
|---|------|------|----------|
| B1 | Purchase CA 780 credit | new | happy path |
| B2 | Purchase TX 680 credit | new | different state/credit |
| B3 | Refinance NY 720 credit | new | refinance path |
| B4 | First-time buyer FL 620 credit | new | low credit tier |
| B5 | Jumbo CA 800 credit $1.2M | new | high value |
| B6 | Returning — check quote status | existing | existing lead |
| B7 | Vague — "don't know credit" | new | agent guidance |
| B8 | Correction mid-flow | new | value overwrite |
| B9 | Knowledge Q mid-flow + return | new | diversion |
| B10 | All info at once | new | multi-field extraction |
| B11 | SMS quote inquiry (mock) | existing | SMS channel |
| B12 | "What's my rate?" | existing | quote lookup |

### Loan Officer (8)
| # | Name | Type | Key Test |
|---|------|------|----------|
| L1 | Register new officer | new | onboarding |
| L2 | Available leads in CA | existing | lead discovery |
| L3 | Submit quote for lead #1 | existing | quote creation |
| L4 | Request borrower contact ($35) | existing | privacy relay |
| L5 | Ask borrower question (relay) | existing | masked relay |
| L6 | Switch between leads | existing | lead switching |
| L7 | Check balance / recharge | existing | balance mock API |
| L8 | Low balance — can't quote | existing | payment gate |

## 5. API Mocking

Mock these external APIs for testing:
- **SMS API**: mock Twilio — returns `{"status": "sent"}` for all calls
- **Balance API**: mock — returns current balance, deducts on quote
- **WIX API**: mock — accepts lead creation webhook payloads
- **Email API**: mock — logs send attempts, no actual delivery

For each mocked API, create a GitHub issue on the mfangdai repo tracking the real integration.

## 6. Implementation Plan

### Phase 0: Tier 2 Runner
1. Create `tests/test_tier2.py` with `Tier2Runner` class
2. Implement 12 borrower scripts + 8 officer scripts
3. Run against real LLM, collect metrics
4. Report: intent_accuracy, entity_extraction_rate per script

### Phase 1: Tier 3 Runner
1. Extend `tests/test_simulated.py` with `Tier3Runner`
2. Add 6 personas (4 borrower + 2 officer)
3. Run each persona 3x, collect completion metrics
4. Add loop detection

### Phase 2: API Mocks + GitHub Issues
1. Create `src/api_mocks.py` with SMS, Balance, WIX, Email mocks
2. Create GitHub issues for each real API integration

### Phase 3: Expand to 50+ scenarios
After MVP validates the approach, expand the scenario catalog.

## 7. Success Criteria

- Tier 2: ≥85% intent accuracy across all 20 scripts
- Tier 3: ≥70% completion rate across all personas
- Tier 3: 0 infinite loops detected
- Tier 3: avg turn count ≤12 for borrower flows
- All 65 Tier 1 tests still pass
