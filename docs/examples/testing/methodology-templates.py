"""Reference implementation templates for the three-tier testing methodology.
These are CONCRETE EXAMPLES — NOT part of the framework spec.
Copy and adapt for your project. See docs/specs/2026-06-19-three-tier-agent-testing-methodology.md for the methodology.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── §3.2: MockGateway Template (Tier 1) ──

class MockGateway:
    """Drop-in replacement for the real LLM Gateway. Keyword-based, deterministic."""

    def _extract_message(self, prompt: str) -> str:
        """Extract just the user message from the classify prompt template."""
        marker = 'User message: "'
        if marker in prompt:
            start = prompt.index(marker) + len(marker)
            end = prompt.index('"', start)
            return prompt[start:end]
        return prompt

    def call(self, prompt: str, output_schema: type, temperature: float = 0):
        """Return a pre-determined intent based on keyword matching."""
        msg = self._extract_message(prompt).lower()
        # --- REPLACE BELOW with your domain's intent keywords ---
        if "hello" in msg or "hi" in msg:
            return output_schema(intent="greet", confidence=1.0)
        if "help" in msg:
            return output_schema(intent="help", confidence=1.0)
        entities = {}
        return output_schema(
            intent="provide_loan_info" if entities else "ask_about_rates",
            confidence=1.0, entities=entities,
        )


# ── §5.2: SimClient Template (Tier 3) ──

class SimClient:
    """LLM-powered simulated user. Takes a persona, runs conversation loop."""

    def __init__(self, gateway, persona: dict):
        self.gateway = gateway
        self.persona = persona
        self.history = []

    def _build_prompt(self, agent_response: str) -> str:
        prompt = self.persona["system_prompt"].format(**self.persona["situation"])
        for turn in self.history[-6:]:
            prompt += f"\nUser: {turn['user']}\nAgent: {turn['agent']}"
        prompt += f"\n\nLast agent message: {agent_response}"
        prompt += "\n\nYour natural response (1-2 sentences, stay in character):"
        return prompt

    def next_message(self, agent_response: str) -> str:
        return self.gateway.call_text(self._build_prompt(agent_response), temperature=0.3)

    def record_turn(self, user_msg: str, agent_response: str):
        self.history.append({"user": user_msg, "agent": agent_response})

    def run(self, agent, opening_message: str, max_turns: int = 15) -> dict:
        state = None
        user_msg = opening_message
        for turn in range(max_turns):
            result = agent.process(user_msg, "sim_user", self.persona["user_type"],
                                   self.persona.get("name", ""), state)
            self.record_turn(user_msg, result["response"])
            state = result["state"]
            if result["phase"] == "completed":
                return {"success": True, "turns": self.history, "state": state}
            if result["phase"] == "error":
                return {"success": False, "turns": self.history, "state": state}
            user_msg = self.next_message(result["response"])
        return {"success": False, "turns": self.history, "state": state}


# ── §7: LayerTrace Dataclass ──

@dataclass
class LayerTrace:
    """Deterministic workflow layer trace for test visibility."""
    layer1_intent: str = ""
    layer1_confidence: float = 0.0
    layer1_entities: dict = field(default_factory=dict)
    layer2_phase_before: str = ""
    layer2_phase_after: str = ""
    layer2_decision: str = ""
    layer2_validation: str = ""
    layer3_response_type: str = "deterministic"
    layer3_template: str = ""

    def to_log(self) -> str:
        return (
            f"[L1:LLM] intent={self.layer1_intent}, conf={self.layer1_confidence:.2f}, "
            f"entities={self.layer1_entities}\n"
            f"[L2:CODE] phase: {self.layer2_phase_before} → {self.layer2_phase_after}, "
            f"decision={self.layer2_decision}, validation={self.layer2_validation}\n"
            f"[L3:CODE] type={self.layer3_response_type}, template={self.layer3_template}"
        )


# ── §10: FlakyMockGateway (Gateway Retry Testing) ──

class FlakyMockGateway:
    """Simulates LLM API failures for retry testing."""
    def __init__(self, fail_count: int = 2, max_retries: int = 3):
        self.call_count = 0
        self.fail_count = fail_count
        self.max_retries = max_retries

    def call(self, prompt, output_schema, temperature=0):
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise ConnectionError("simulated network failure")
        return output_schema(intent="greet", confidence=1.0)


# ── §14: API Mock Templates ──

from datetime import datetime

class MockSMSClient:
    """Drop-in replacement for SMS API. Same interface, zero network."""
    def __init__(self):
        self.sent = []

    def send(self, to: str, body: str) -> dict:
        self.sent.append({"to": to, "body": body, "timestamp": datetime.utcnow()})
        return {"status": "sent", "message_id": f"mock-{len(self.sent)}"}


class MockBalanceLedger:
    """In-memory balance ledger. Replaces payment processor API."""
    def __init__(self, initial_balance: float = 0):
        self.balance = initial_balance
        self.transactions = []

    def deduct(self, amount: float, reason: str) -> bool:
        if self.balance < amount:
            return False
        self.balance -= amount
        self.transactions.append({"type": "deduct", "amount": amount, "reason": reason})
        return True

    def recharge(self, amount: float) -> None:
        self.balance += amount
        self.transactions.append({"type": "recharge", "amount": amount})


# ── §4.2: Tier 2 Script Format ──

TIER2_SCRIPT_EXAMPLE = [
    {
        "message": "Hi, I want to check rates",
        "expect": {"intent": "ask_about_rates", "phase_after": "collecting_info"},
    },
    {
        "message": "I'm buying a home in California, worth $500k",
        "expect": {
            "intent": "provide_loan_info",
            "entities": {"loan_purpose": "purchase", "state": "CA", "home_value": 500000},
        },
    },
]

# Soft matching (ambiguous intent):
TIER2_SOFT_MATCH = {"expect": {"intent": ["ask_about_rates", "help"]}}


# ── §5.2: Tier 3 Persona Dict ──

PERSONA_EXAMPLE = {
    "id": "persona_name",
    "user_type": "borrower",
    "goal": "get a mortgage rate quote",
    "system_prompt": "You are a home buyer. Respond naturally. Be concise.",
    "situation": {
        "loan_purpose": "purchase",
        "home_value": 500000,
        "loan_amount": 300000,
        "state": "California",
        "credit_score": "around 720",
    },
    "success_criteria": {"phase": "completed", "quote_not_null": True},
}


# ── §13: Multi-Turn State Assertions ──

def example_state_assertions(state):
    """State accumulation across turns."""
    # After turn 2: initial data collected
    assert state.collected_data == {"loan_purpose": "purchase"}
    # After turn 3: new data added, old preserved
    assert state.collected_data == {"loan_purpose": "purchase", "home_value": 500000}
    # After diversion: data survives
    assert state.collected_data["loan_purpose"] == "purchase"
    # After completion: full state
    assert state.phase == "completed"
    assert state.lead_id is not None
    assert state.quote["interest_rate"] > 0


# ── §18: Consolidated Report Template ──

REPORT_TEMPLATE = """# Test Report — {project} — {date}

## Summary
| Tier | Tests | Passed | Key Metric |
|------|-------|--------|------------|
| Tier 1 | {n} | {n} | 100% pass (deterministic) |
| Tier 2 | {n} scripts | {n} | {x}% intent accuracy |
| Tier 3 | {n} personas × {n} runs | {n} | {x}% completion rate |

## Tier 2 — LLM Accuracy
- Intent accuracy: {x}% (target: ≥85%)
- Mismatches ({n}):
  | Script | Turn | Message | Expected | Got |
  |--------|------|---------|----------|-----|

## Tier 3 — Completion
- Completion rate: {x}% (target: ≥70%)
- Avg turns: {x} (target: ≤12)

## Verdict
PRODUCTION-READY / NEEDS IMPROVEMENT / BLOCKED
"""
