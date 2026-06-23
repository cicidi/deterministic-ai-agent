# Tier 2 + Tier 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Tier 2 (LLM accuracy tests) and Tier 3 (completion tests) for mfangdai-agent per the three-tier testing methodology spec.

**Architecture:** Create `tests/tier2/` with scripted dialogue scenarios (hardcoded client, real LLM L1, hardcoded L3) and `tests/tier3/` with SimClient persona conversations (dual LLM). Shared fixtures in conftest.py, metrics collectors, and API mocks.

**Tech Stack:** Python, pytest, DeepSeek API (via LLM_Gateway), SimClient, LayerTrace

---

### Task 1: Create Tier 2 directory structure and conftest

**Files:**
- Create: `tests/tier2/__init__.py`
- Create: `tests/tier2/conftest.py`

- [ ] **Step 1: Create directory and empty __init__.py**

```bash
mkdir -p /home/cicidi/project/mfangdai-ai-agent/tests/tier2/scenarios
touch /home/cicidi/project/mfangdai-ai-agent/tests/tier2/__init__.py
touch /home/cicidi/project/mfangdai-ai-agent/tests/tier2/scenarios/__init__.py
```

- [ ] **Step 2: Write conftest.py with LiveAgent fixture and metrics collector**

```python
# tests/tier2/conftest.py
import os
import pytest
from dataclasses import dataclass, field

from src.db import init_db, get_session, seed_loan_officers, Base
from src.gateway import Gateway
from src.state_machine import Agent
from src.hydration import AgentState


@dataclass
class Tier2Metrics:
    scripts_run: int = 0
    scripts_passed: int = 0
    total_turns: int = 0
    expected_turns: int = 0
    intent_matches: int = 0
    intent_mismatches: int = 0
    entities_extracted: int = 0
    entities_expected: int = 0
    mismatches: list[dict] = field(default_factory=list)

    @property
    def intent_accuracy(self) -> float:
        total = self.intent_matches + self.intent_mismatches
        return self.intent_matches / total if total > 0 else 0.0

    @property
    def entity_extraction_rate(self) -> float:
        return self.entities_extracted / self.entities_expected if self.entities_expected > 0 else 0.0


@pytest.fixture(scope="module")
def live_agent():
    init_db("sqlite:///mfangdai_t2.db")
    session = get_session()
    try:
        Base.metadata.create_all(session.get_bind())
        seed_loan_officers(session)
    finally:
        session.close()
    gw = Gateway(
        model=os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.environ.get("LLM_API_KEY", "sk-placeholder"),
    )
    return Agent(gw)


@pytest.fixture(scope="module")
def metrics():
    return Tier2Metrics()


needs_llm = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set",
)
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier2/
git commit -m "test: add Tier 2 directory structure and conftest with metrics collector"
```

---

### Task 2: Tier 2 runner helper

**Files:**
- Create: `tests/tier2/runner.py`

- [ ] **Step 1: Write the runner**

```python
# tests/tier2/runner.py
"""Tier 2 runner: executes scripted dialogues against live agent."""
from src.hydration import AgentState


def run_t2_script(agent, script: list[dict], user_id: str, user_type: str,
                  user_name: str = "", metrics=None) -> dict:
    """Execute a Tier 2 script and collect metrics.

    Args:
        agent: live Agent instance
        script: list of {"message": str, "expect": dict} per turn
        user_id: unique user identifier
        user_type: "borrower" or "loan_officer"
        user_name: display name
        metrics: Tier2Metrics instance (optional)

    Returns:
        {"success": bool, "turns": list, "state": AgentState, "trace": list}
    """
    state = AgentState(user_id=user_id, user_type=user_type, user_name=user_name)
    traces = []
    
    for i, step in enumerate(script):
        msg = step["message"]
        expected = step.get("expect", {})
        
        result = agent.process(msg, user_id, user_type, user_name, state)
        state = result["state"]
        trace = result.get("trace")
        traces.append(trace)
        
        if result["phase"] == "error":
            return {"success": False, "turns": traces, "state": state,
                    "trace": traces, "error_at_turn": i, "error": state.error}
        
        # Collect metrics
        if metrics and trace:
            metrics.total_turns += 1
            if expected.get("intent"):
                expected_turns = expected.get("expected_turns", len(script))
                metrics.expected_turns += expected_turns
                if trace.layer1_intent == expected["intent"]:
                    metrics.intent_matches += 1
                else:
                    metrics.intent_mismatches += 1
                    metrics.mismatches.append({
                        "script_turn": i,
                        "message": msg[:80],
                        "expected_intent": expected["intent"],
                        "actual_intent": trace.layer1_intent,
                    })
            
            if expected.get("entities"):
                expected_entities = expected["entities"]
                metrics.entities_expected += len(expected_entities)
                for key, val in expected_entities.items():
                    if trace.layer1_entities.get(key) == val:
                        metrics.entities_extracted += 1
    
    # Final check
    final_expected = script[-1].get("expect", {})
    final_phase = final_expected.get("phase_after")
    if final_phase and state.phase != final_phase:
        return {"success": False, "turns": traces, "state": state,
                "trace": traces, "expected_phase": final_phase, "actual_phase": state.phase}
    
    return {"success": True, "turns": traces, "state": state, "trace": traces}
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier2/runner.py
git commit -m "test: add Tier 2 script runner with metrics collection"
```

---

### Task 3: Tier 2 borrower scenarios (6 scripts)

**Files:**
- Create: `tests/tier2/scenarios/test_borrower_scenarios.py`

- [ ] **Step 1: Write 6 borrower scripts**

```python
# tests/tier2/scenarios/test_borrower_scenarios.py
"""Tier 2: Borrower scenarios — scripted dialogue with real LLM L1, hardcoded L3."""
import pytest
from tests.tier2.conftest import needs_llm
from tests.tier2.runner import run_t2_script


# ── S01: Happy path — purchase, CA, 780 credit ──

S01_PURCHASE_CA = [
    {"message": "Hi, I want to check mortgage rates",
     "expect": {"intent": "ask_about_rates", "phase_after": "collecting_info"}},
    {"message": "I'm buying a new home",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "purchase"}}},
    {"message": "The property is worth about $500,000",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 500000}}},
    {"message": "I need to borrow $300,000",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 300000}}},
    {"message": "It's in California",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "CA"}}},
    {"message": "My credit score is around 720",
     "expect": {"intent": "provide_loan_info", "phase_after": "completed"}},
]

# ── S02: Purchase, TX, 680 credit ──

S02_PURCHASE_TX = [
    {"message": "Can you tell me what mortgage rates look like right now?",
     "expect": {"intent": "ask_about_rates"}},
    {"message": "I want to purchase a property",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "purchase"}}},
    {"message": "The house is valued around $350,000",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 350000}}},
    {"message": "Looking to borrow about $250,000",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 250000}}},
    {"message": "The property is located in Texas",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "TX"}}},
    {"message": "I think my credit score is 680",
     "expect": {"intent": "provide_loan_info", "phase_after": "completed"}},
]

# ── S03: Refinance, NY, 720 credit ──

S03_REFINANCE_NY = [
    {"message": "I'm thinking about refinancing my mortgage, what rates can I get?",
     "expect": {"intent": "ask_about_rates"}},
    {"message": "I want to refinance my current home",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "refinance"}}},
    {"message": "My home is worth approximately $600,000",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 600000}}},
    {"message": "I need a loan of $400,000",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 400000}}},
    {"message": "I'm in New York state",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "NY"}}},
    {"message": "My credit score is about 720",
     "expect": {"intent": "provide_loan_info", "phase_after": "completed"}},
]

# ── S04: First-time buyer, FL, 620 credit ──

S04_FIRST_TIME_FL = [
    {"message": "Hi, I'm a first time home buyer, never done this before. Can you help?",
     "expect": {"intent": "ask_about_rates"}},
    {"message": "I'm looking to purchase my first home",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "purchase"}}},
    {"message": "The property I'm looking at is worth $200,000",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 200000}}},
    {"message": "I want to borrow $180,000",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 180000}}},
    {"message": "The house is in Florida",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "FL"}}},
    {"message": "My credit is not great, around 620",
     "expect": {"intent": "provide_loan_info", "phase_after": "completed"}},
]

# ── S05: Vague customer — needs guidance ──

S05_VAGUE = [
    {"message": "I want to buy a house, can you help?",
     "expect": {"intent": "ask_about_rates"}},
    {"message": "I'm not sure, I just want to buy something",
     "expect": {"intent": "provide_loan_info" or "ask_about_rates"}},
    {"message": "The home is maybe worth $400,000 or so",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 400000}}},
    {"message": "I guess I need maybe $300,000?",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 300000}}},
    {"message": "I'm located in Georgia",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "GA"}}},
    {"message": "I don't really know my credit, is that bad?",
     "expect": {"intent": "provide_loan_info"}},
]

# ── S06: Correction mid-flow ──

S06_CORRECTION = [
    {"message": "I want to check mortgage rates",
     "expect": {"intent": "ask_about_rates"}},
    {"message": "I'm buying a home",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "purchase"}}},
    {"message": "Actually wait, I want to refinance, not buy",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_purpose": "refinance"}}},
    {"message": "My home is worth $500,000",
     "expect": {"intent": "provide_loan_info", "entities": {"home_value": 500000}}},
    {"message": "Need about $350,000",
     "expect": {"intent": "provide_loan_info", "entities": {"loan_amount": 350000}}},
    {"message": "In Washington state",
     "expect": {"intent": "provide_loan_info", "entities": {"state": "WA"}}},
    {"message": "Credit score is 720",
     "expect": {"intent": "provide_loan_info", "phase_after": "completed"}},
]


SCRIPTS = [
    ("S01_purchase_ca", S01_PURCHASE_CA, "s01_purchase", "borrower", "Alice"),
    ("S02_purchase_tx", S02_PURCHASE_TX, "s02_purchase", "borrower", "Bob"),
    ("S03_refinance_ny", S03_REFINANCE_NY, "s03_refi", "borrower", "Carol"),
    ("S04_first_time_fl", S04_FIRST_TIME_FL, "s04_first", "borrower", "Dave"),
    ("S05_vague", S05_VAGUE, "s05_vague", "borrower", "Eva"),
    ("S06_correction", S06_CORRECTION, "s06_correction", "borrower", "Frank"),
]


class TestBorrowerTier2:
    @needs_llm
    @pytest.mark.parametrize("name,script,uid,utype,uname", SCRIPTS)
    def test_script(self, live_agent, metrics, name, script, uid, utype, uname):
        result = run_t2_script(live_agent, script, uid, utype, uname, metrics)
        assert result["success"], (
            f"Script {name} failed. "
            f"Phase: {result['state'].phase}, "
            f"Error: {result.get('error', 'none')}"
        )
        metrics.scripts_passed += 1
        metrics.scripts_run += 1
```

- [ ] **Step 2: Run Tier 2 borrower tests**

```bash
cd /home/cicidi/project/mfangdai-ai-agent && rm -f mfangdai_t2.db
export LLM_API_KEY=sk-97fa4f09f0e54caaa4346fb9b832f7bc
.venv/bin/python -m pytest tests/tier2/scenarios/test_borrower_scenarios.py -v -s
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier2/scenarios/
git commit -m "test: add 6 Tier 2 borrower scripts — purchase, refinance, first-time, vague, correction"
```

---

### Task 4: Tier 2 officer scenarios (4 scripts)

**Files:**
- Create: `tests/tier2/scenarios/test_officer_scenarios.py`

- [ ] **Step 1: Write 4 officer scripts**

```python
# tests/tier2/scenarios/test_officer_scenarios.py
"""Tier 2: Loan officer scenarios."""
import pytest
from tests.tier2.conftest import needs_llm
from tests.tier2.runner import run_t2_script

S07_REGISTER = [
    {"message": "Hi, I'm a mortgage broker, I'd like to register on your platform",
     "expect": {"intent": "register_loan_officer"}},
]

S08_LEADS_CA = [
    {"message": "Do you have any mortgage leads available in California?",
     "expect": {"intent": "ask_for_leads", "entities": {"state": "CA"}}},
]

S09_LEADS_MULTI = [
    {"message": "Show me what leads you have in Texas and Florida",
     "expect": {"intent": "ask_for_leads"}},
]

S10_SWITCH_LEAD = [
    {"message": "Show me my available leads",
     "expect": {"intent": "ask_for_leads"}},
    {"message": "Let me switch to lead number 1",
     "expect": {"intent": "switch_lead"}},
]

SCRIPTS = [
    ("S07_register", S07_REGISTER, "s07", "loan_officer", "Mike"),
    ("S08_leads_ca", S08_LEADS_CA, "s08", "loan_officer", "Sarah"),
    ("S09_leads_multi", S09_LEADS_MULTI, "s09", "loan_officer", "David"),
    ("S10_switch", S10_SWITCH_LEAD, "s10", "loan_officer", "Emily"),
]

class TestOfficerTier2:
    @needs_llm
    @pytest.mark.parametrize("name,script,uid,utype,uname", SCRIPTS)
    def test_script(self, live_agent, metrics, name, script, uid, utype, uname):
        result = run_t2_script(live_agent, script, uid, utype, uname, metrics)
        assert result["success"], (
            f"Script {name} failed. Phase: {result['state'].phase}"
        )
        metrics.scripts_passed += 1
        metrics.scripts_run += 1
```

- [ ] **Step 2: Run Tier 2 officer tests**

```bash
.venv/bin/python -m pytest tests/tier2/scenarios/test_officer_scenarios.py -v -s
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier2/scenarios/
git commit -m "test: add 4 Tier 2 officer scripts — register, leads discovery, lead switching"
```

---

### Task 5: Tier 2 metrics report

**Files:**
- Modify: `tests/tier2/conftest.py`

- [ ] **Step 1: Add session-scoped metrics summary**

```python
# Add to conftest.py after the metrics fixture:

def pytest_sessionfinish(session, exitstatus):
    """Print Tier 2 metrics summary after all tests."""
    metrics = None
    for item in session.items:
        if hasattr(item, "funcargs") and "metrics" in (getattr(item, "funcargs", {}) or {}):
            metrics = item.funcargs.get("metrics")
            break
    
    if metrics and hasattr(metrics, "scripts_run") and metrics.scripts_run > 0:
        print(f"\n{'='*60}")
        print(f"  Tier 2 Metrics Summary")
        print(f"{'='*60}")
        print(f"  Scripts: {metrics.scripts_passed}/{metrics.scripts_run} passed")
        print(f"  Intent Accuracy: {metrics.intent_accuracy:.1%}")
        print(f"  Entity Extraction Rate: {metrics.entity_extraction_rate:.1%}")
        print(f"  Turn Matches: {metrics.intent_matches}/{metrics.intent_matches + metrics.intent_mismatches}")
        if metrics.mismatches:
            print(f"  Mismatches:")
            for m in metrics.mismatches:
                print(f"    Turn {m['script_turn']}: '{m['message']}'")
                print(f"      Expected: {m['expected_intent']}, Got: {m['actual_intent']}")
        print(f"{'='*60}\n")
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier2/conftest.py
git commit -m "test: add Tier 2 metrics summary on session finish"
```

---

### Task 6: Tier 3 directory structure and SimClient

**Files:**
- Create: `tests/tier3/__init__.py`
- Create: `tests/tier3/conftest.py`
- Create: `tests/tier3/personas/__init__.py`

- [ ] **Step 1: Create directories**

```bash
mkdir -p /home/cicidi/project/mfangdai-ai-agent/tests/tier3/personas
touch /home/cicidi/project/mfangdai-ai-agent/tests/tier3/__init__.py
touch /home/cicidi/project/mfangdai-ai-agent/tests/tier3/personas/__init__.py
```

- [ ] **Step 2: Write conftest.py**

```python
# tests/tier3/conftest.py
import os
import pytest
from dataclasses import dataclass, field
from tests.sim_client import SimClient
from src.db import init_db, get_session, seed_loan_officers, Base
from src.gateway import Gateway
from src.state_machine import Agent
from src.hydration import AgentState


@dataclass
class Tier3Metrics:
    total_runs: int = 0
    completed_runs: int = 0
    errored_runs: int = 0
    looped_runs: int = 0
    total_turns: int = 0
    turn_histogram: dict = field(default_factory=dict)

    @property
    def completion_rate(self) -> float:
        return self.completed_runs / self.total_runs if self.total_runs > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return self.errored_runs / self.total_runs if self.total_runs > 0 else 0.0

    @property
    def avg_turns(self) -> float:
        return self.total_turns / self.total_runs if self.total_runs > 0 else 0.0


@pytest.fixture(scope="module")
def live_agent():
    init_db("sqlite:///mfangdai_t3.db")
    session = get_session()
    try:
        Base.metadata.create_all(session.get_bind())
        seed_loan_officers(session)
    finally:
        session.close()
    gw = Gateway(
        model=os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.environ.get("LLM_API_KEY", "sk-placeholder"),
    )
    return Agent(gw)


@pytest.fixture(scope="module")
def t3_metrics():
    return Tier3Metrics()


needs_llm = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set",
)
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier3/
git commit -m "test: add Tier 3 directory structure and conftest"
```

---

### Task 7: Tier 3 run harness

**Files:**
- Create: `tests/tier3/runner.py`

This task is skipped for brevity in this plan — use tests/sim_client.py SimClient.run() as the harness, already implemented.

- [ ] **Step 1: Copy existing sim_client.py harness into tier3 runner**

```bash
# SimClient.run() in tests/sim_client.py already implements the conversation loop.
# Tier 3 tests will import and use it directly.
```

---

### Task 8: Tier 3 borrower personas (2 personas × 3 runs)

**Files:**
- Create: `tests/tier3/personas/test_borrower_personas.py`

- [ ] **Step 1: Write 2 borrower personas with run loop**

```python
# tests/tier3/personas/test_borrower_personas.py
import pytest
from tests.sim_client import run_borrower_scenario
from tests.tier3.conftest import needs_llm

PERSONA_ALICE_CA = {
    "user_id": "t3_alice", "name": "Alice", "age": 34,
    "occupation": "software engineer",
    "goal": "get a mortgage rate quote for buying a home",
    "loan_purpose": "purchase", "home_value": 800000,
    "loan_amount": 400000, "state": "California",
    "credit_score": "around 780",
    "opening": "Hi there! I'm looking to buy a home and wanted to check what rates I could get.",
}

PERSONA_BOB_TX = {
    "user_id": "t3_bob", "name": "Bob", "age": 45,
    "occupation": "teacher",
    "goal": "refinance my existing mortgage at a better rate",
    "loan_purpose": "refinance", "home_value": 500000,
    "loan_amount": 300000, "state": "Texas",
    "credit_score": "about 680",
    "opening": "Hey, I'm thinking about refinancing my mortgage. Can you help me with rates?",
}

PERSONAS = [
    ("p01_alice_ca", PERSONA_ALICE_CA),
    ("p02_bob_tx", PERSONA_BOB_TX),
]
RUNS_PER_PERSONA = 3


class TestBorrowerTier3:
    @needs_llm
    @pytest.mark.parametrize("pname,persona", PERSONAS)
    @pytest.mark.parametrize("run_id", range(RUNS_PER_PERSONA))
    def test_persona(self, live_agent, t3_metrics, pname, persona, run_id):
        result = run_borrower_scenario(live_agent, live_agent.gateway, persona, max_turns=15)
        t3_metrics.total_runs += 1

        if result["success"]:
            t3_metrics.completed_runs += 1
            turns = len(result["turns"])
            t3_metrics.total_turns += turns
            t3_metrics.turn_histogram[turns] = t3_metrics.turn_histogram.get(turns, 0) + 1
        elif result.get("phase") == "error":
            t3_metrics.errored_runs += 1

        assert result["success"], (
            f"{pname} run {run_id} failed. "
            f"Phase: {result.get('phase')}, Turns: {len(result.get('turns', []))}"
        )
```

- [ ] **Step 2: Run Tier 3 borrower tests**

```bash
cd /home/cicidi/project/mfangdai-ai-agent && rm -f mfangdai_t3.db
export LLM_API_KEY=sk-97fa4f09f0e54caaa4346fb9b832f7bc
.venv/bin/python -m pytest tests/tier3/personas/test_borrower_personas.py -v -s
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier3/
git commit -m "test: add Tier 3 borrower personas — 2 personas × 3 runs each"
```

---

### Task 9: Tier 3 metrics report

**Files:**
- Modify: `tests/tier3/conftest.py`

- [ ] **Step 1: Add session finish hook for Tier 3 metrics**

```python
# Add to tests/tier3/conftest.py after fixtures:

def pytest_sessionfinish(session, exitstatus):
    metrics = None
    for item in session.items:
        if hasattr(item, "funcargs") and "t3_metrics" in (getattr(item, "funcargs", {}) or {}):
            metrics = item.funcargs.get("t3_metrics")
            break
    
    if metrics and metrics.total_runs > 0:
        print(f"\n{'='*60}")
        print(f"  Tier 3 Metrics Summary")
        print(f"{'='*60}")
        print(f"  Completion Rate: {metrics.completion_rate:.1%} ({metrics.completed_runs}/{metrics.total_runs})")
        print(f"  Error Rate: {metrics.error_rate:.1%} ({metrics.errored_runs}/{metrics.total_runs})")
        print(f"  Avg Turns: {metrics.avg_turns:.1f}")
        print(f"  Turn Distribution: {dict(sorted(metrics.turn_histogram.items()))}")
        
        if metrics.completion_rate >= 0.70:
            print(f"  Verdict: PASS (>=70%)")
        elif metrics.completion_rate >= 0.50:
            print(f"  Verdict: WARN (50-69%)")
        else:
            print(f"  Verdict: FAIL (<50%)")
        print(f"{'='*60}\n")
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/conftest.py
git commit -m "test: add Tier 3 metrics summary on session finish"
```

---

### Task 10: Final integration — run all 3 tiers

- [ ] **Step 1: Run Tier 1 (no API key)**

```bash
rm -f mfangdai_test.db mfangdai_ft.db
.venv/bin/python -m pytest tests/test_workflow.py tests/test_functional.py -v -q
```
Expected: 65 passed

- [ ] **Step 2: Run Tier 2 (needs API key)**

```bash
rm -f mfangdai_t2.db
export LLM_API_KEY=sk-97fa4f09f0e54caaa4346fb9b832f7bc
.venv/bin/python -m pytest tests/tier2/ -v -s
```
Expected: 10 scripts pass, metrics summary printed

- [ ] **Step 3: Run Tier 3 (needs API key)**

```bash
rm -f mfangdai_t3.db
.venv/bin/python -m pytest tests/tier3/ -v -s
```
Expected: 6 runs (2 personas × 3), metrics summary printed

- [ ] **Step 4: Commit all**

```bash
git add .
git commit -m "test: complete Tier 2 + Tier 3 implementation — 10 scripts + 6 persona runs"
```
