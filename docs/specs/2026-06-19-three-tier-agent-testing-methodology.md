# Three-Tier Agent Testing Methodology

**Version:** 0.1.0
**Scope:** Testing strategy for agents built on the three-layer deterministic workflow framework. Industry-agnostic. Applies to any domain (fintech, healthcare, legal, government).

---

## 1. Problem Statement

Testing LLM-powered agents is fundamentally different from testing traditional software. The agent has two kinds of components: deterministic code (Layer 2 decisions, Layer 3 responses) and non-deterministic LLM calls (Layer 1 classification and extraction). A test that passes today may fail tomorrow because the LLM classified a message differently. Conversely, a test that mocks the LLM perfectly may pass while the real LLM fails on the same input.

The three-tier methodology separates these concerns: test the code without the LLM, test the LLM without variable user input, then test both together.

## 2. The Three Tiers

```
┌──────────────────────────────────────────────────────────────┐
│ Tier 1: Logic Tests                                          │
│ Client: hardcoded strings   Server: MockGateway (keyword)    │
│ Verifies: code logic, state machine, database persistence    │
│ Runs: fast, deterministic, CI-safe, no API keys needed       │
├──────────────────────────────────────────────────────────────┤
│ Tier 2: LLM Accuracy Tests                                   │
│ Client: pre-written scripts  Server: real LLM                │
│ Verifies: LLM can correctly classify and extract from        │
│           realistic but controlled user messages             │
│ Runs: with API keys, measures intent accuracy per turn       │
├──────────────────────────────────────────────────────────────┤
│ Tier 3: Completion Tests                                     │
│ Client: LLM (persona)        Server: real LLM                │
│ Verifies: end-to-end conversation success rate, turn count,  │
│           loop detection, indirect multi-party communication  │
│ Runs: with API keys, stochastic (run N times for confidence) │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 Why Three Tiers?

A single tier is insufficient:

| If you only have... | You miss... |
|--------------------|------------|
| Tier 1 only | LLM may misclassify real user messages. All 65 tests pass but the agent fails in production. |
| Tier 2 only | The scripted client can't find unexpected edge cases. Coverage is limited to what humans pre-write. |
| Tier 3 only | Stochastic LLM variance makes it impossible to localize bugs. Is the test failing because of a code bug or an LLM fluke? |

Together, the three tiers isolate failures: Tier 1 tells you "is my code wrong?", Tier 2 tells you "can the LLM understand my users?", Tier 3 tells you "does the whole system work?"

## 3. Tier 1: Logic Tests

### 3.1 Architecture

```
FixedScriptClient ──pre-written message──► Agent (MockGateway)
                    ◄──deterministic response──
```

Both sides are deterministic. The same input always produces the same output.

### 3.2 MockGateway

Replace the real LLM with a keyword-based classifier that returns pre-determined intents. The mock must:

- Return correct intents for every test message
- Return appropriate entities for entity-extraction tests
- Be deterministic — same message → same intent every run

### 3.3 What to Test

**Happy paths:**
- Complete workflow from start to finish
- Every state transition fires correctly
- Every entity is written to the database

**Edge cases (举一反三):**
For each happy path test, write 2-3 variants by changing one dimension:
- Different values (amounts, states, credit scores)
- Different order of information provision
- Multiple fields provided in one message
- Corrections (wrong value → correct value)
- Diversions (ask unrelated question mid-flow → return)

**Error paths:**
- LLM returns low confidence
- LLM returns unrecognized intent
- Required entity missing
- No matching entities in database
- Database connection failure

**Domain model exhaustion:**
For every entity field in the domain model, verify:
- Is there a test where this field is missing?
- Is there a test where this field is wrong and corrected?
- Is there a test where this field is at its boundary?
- Is there a test where this field is provided alongside other fields?

### 3.4 Assertion Patterns

```python
# State machine assertions
assert result["phase"] == "completed"
assert state.collected_data.get("required_field") is not None

# Database assertions
assert session.query(LeadModel).filter_by(id=state.lead_id).count() == 1

# Response assertions
assert expected_text in result["response"].lower()

# Trace assertions (LayerTrace)
assert result["trace"].layer1_intent == "expected_intent"
assert result["trace"].layer2_phase_after == "expected_phase"
```

## 4. Tier 2: LLM Accuracy Tests

### 4.1 Architecture

```
ScriptedClient ──pre-written message──► Agent (real LLM)
                 ◄──response──────────
```

The client sends fixed messages from a script. The server uses the real LLM for intent classification and entity extraction. All other agent logic (Layer 2 decisions, Layer 3 responses) runs normally.

### 4.2 Script Format

```python
TIER2_SCRIPTS = [
    {
        "id": "scenario_name",
        "user_type": "borrower",
        "turns": [
            {
                "message": "Hi, I want to check rates",
                "expect": {
                    "intent": "ask_about_rates",
                    "phase_after": "collecting_info",
                }
            },
            {
                "message": "I'm buying a home in California, worth $500k",
                "expect": {
                    "intent": "provide_loan_info",
                    "entities": {"loan_purpose": "purchase", "state": "CA", "home_value": 500000},
                }
            },
        ]
    },
]
```

### 4.3 Metrics Collected Per Script

| Metric | Definition | Target |
|--------|-----------|--------|
| `intent_accuracy` | % turns where LLM intent matches expected | ≥85% |
| `entity_extraction_rate` | % expected entities correctly extracted | ≥80% |
| `false_positive_intents` | Number of turns where LLM returned wrong intent | 0 |
| `turn_count` | Actual turns vs expected turns | ±1 acceptable |
| `error_rate` | % scripts that hit the errorNode | 0% |

### 4.4 Scenario Design Principles

**Cover every intent.** For each intent in the system, write at least one script where that intent is expected.

**Cover every user type.** Scripts for each user role (borrower, officer, admin).

**Cover both happy and edge paths.** Not just "everything works" but also "what if the user is vague?" and "what if the user corrects themselves?"

**Vary natural language.** Don't use the same phrasing across scripts. "I want a mortgage quote" vs "can you tell me current rates?" vs "how much would a loan cost?" — all should map to `ask_about_rates`.

**Industry-agnostic names.** Don't name scenarios "B1_purchase_ca". Name them generically: "S01_happy_path_user_type_A", "S02_edge_case_vague_input".

## 5. Tier 3: Completion Tests

### 5.1 Architecture

```
SimClient (LLM persona) ──natural msg──► Agent (real LLM)
                          ◄──response──
```

Both sides use LLMs. The simulated client is given a persona (goal, situation, characteristics) and a system prompt instructing it to role-play as that user. The server agent runs normally.

### 5.2 Persona Format

```python
PERSONA = {
    "id": "persona_name",
    "user_type": "borrower",
    "goal": "get a mortgage rate quote",
    "system_prompt": "You are a home buyer. Your situation: {situation}. "
                     "Respond naturally to the mortgage agent's questions. "
                     "Answer what is asked. Be concise.",
    "situation": {
        "loan_purpose": "purchase",
        "home_value": 500000,
        "loan_amount": 300000,
        "state": "California",
        "credit_score": "around 720",
    },
    "success_criteria": {
        "phase": "completed",
        "quote_not_null": True,
    },
}
```

### 5.3 Run Configuration

Each persona must be run multiple times (N ≥ 3) to account for LLM variance:

```
for persona in PERSONAS:
    for run in range(N):
        result = run_conversation(persona, max_turns=15)
        record(result)
```

### 5.4 Metrics Collected Per Persona

| Metric | Definition | Target |
|--------|-----------|--------|
| `completion_rate` | % runs that reach the success criteria | ≥70% |
| `avg_turn_count` | Mean turns to completion (or max if failed) | ≤12 |
| `loop_count` | Number of runs where same intent repeated >3 turns | 0 |
| `error_rate` | % runs that hit the errorNode | ≤10% |
| `turn_distribution` | Histogram of turn counts across all runs | — |

### 5.5 Loop Detection

A conversation has entered a loop when:
- The same intent is classified 3+ consecutive turns
- AND the state phase has not changed
- AND the collected data has not changed

When a loop is detected, the run is marked as failed and the conversation transcript is saved for debugging.

### 5.6 Indirect Multi-Party Communication

Tier 3 also validates scenarios where two end-users communicate through the agent:

```
Borrower (LLM) ──msg──► Agent (masks contacts) ──forward──► Loan Officer (LLM)
                       ◄──response─────────────────────────
```

The agent strips PII (email, phone) from forwarded messages. Tier 3 tests must verify:
- Neither party receives the other's contact info
- Messages are correctly relayed
- The payment gate prompt appears when contact is requested

## 6. Scenario Catalog

### 6.1 Minimum Viable Catalog (20 scenarios)

| # | User Type | Scenario Class | Key Test |
|---|-----------|---------------|----------|
| 1 | Type A | Happy path, normal values | Complete workflow |
| 2 | Type A | Happy path, different values | State/amount variant |
| 3 | Type A | Alternative workflow | Different primary action |
| 4 | Type A | Boundary low values | Minimum acceptable inputs |
| 5 | Type A | Boundary high values | Maximum values |
| 6 | Type A | Returning user | Existing data lookup |
| 7 | Type A | Vague responses | Agent guidance |
| 8 | Type A | Mid-flow correction | Value overwrite |
| 9 | Type A | Mid-flow diversion | Topic jump + return |
| 10 | Type A | All info at once | Multi-field extraction |
| 11 | Type A | Channel variant | Alternative input channel |
| 12 | Type A | Status inquiry | Data retrieval |
| 13 | Type B | Registration | Onboarding |
| 14 | Type B | Discovery | List available items |
| 15 | Type B | Action on item | Create/update on item |
| 16 | Type B | Privacy gate | Access control request |
| 17 | Type B | Indirect communication | Relay through agent |
| 18 | Type B | Context switching | Switch between items |
| 19 | Type B | Balance/payment | Financial transaction |
| 20 | Type B | Insufficient balance | Payment gate enforcement |

### 6.2 Expansion to 50+ Scenarios

From the MVP catalog, expand by inference (举一反三):

- For each happy path (1-3): add 2-3 variants (different states, amounts, credit tiers)
- For each edge case (4-8): add 2-3 variants (different fields corrected, different diversions)
- For each officer flow (13-20): add variants (different states, different lead types, different products)
- Add multi-party indirect communication: borrower↔officer complete cycle

## 7. LayerTrace for Visibility

Every agent turn must include a `LayerTrace` that separates LLM work from deterministic work:

```
[L1:LLM] intent=provide_loan_info, conf=0.95, entities={home_value: 800000}
[L2:CODE] phase: collecting_info → collecting_info, decision=borrower_provide_loan_info
[L3:CODE] type=deterministic, template=
```

This enables:
- Tier 2: verify the LLM classified correctly
- Tier 3: detect when the LLM and code disagree (LLM extracted entity X but code rejected it)
- Debugging: pinpoint which layer failed without reading the full conversation

## 8. API Mocking

When the agent depends on external APIs (SMS, payment, CRM), mock them for all three tiers:

| API | Mock Behavior |
|-----|-------------|
| SMS | Return `{"status": "sent"}` for all calls |
| Payment/Balance | In-memory ledger, deduct on quote, recharge on command |
| Email | Log all sends, return success |
| External data | Return pre-seeded test data |

For each mocked API, track a GitHub issue for the real integration. The mock interface should match the real API's contract so the switch requires zero agent code changes.

## 9. CI/CD Integration

| Tier | Runs On | Trigger | API Key Required |
|------|---------|---------|-----------------|
| Tier 1 | Every commit | pre-push / PR | No |
| Tier 2 | Daily / PR | scheduled / manual | Yes |
| Tier 3 | Weekly / release | scheduled | Yes |

Tier 1 is the gatekeeper. No code merges if Tier 1 fails. Tier 2 and Tier 3 are quality monitors — their results inform but don't block.

## 10. Sources

- Tier 1 design: confidence high — 65 passing mock tests in mfangdai-agent demonstrate the pattern
- Tier 2 design: confidence high — LLM accuracy measurement is a standard NLP evaluation pattern
- Tier 3 design: confidence medium — dual-LLM conversation testing is novel; completion rate targets (70%) are provisional
- LayerTrace: confidence high — implemented and verified in mfangdai-agent sim tests
- Scenario catalog: confidence high — derived from Postman collection (42 use cases) adapted to generic form
- 举一反三 principle: confidence high — demonstrated in 34 FT scenarios with 2-3 inference variants each
