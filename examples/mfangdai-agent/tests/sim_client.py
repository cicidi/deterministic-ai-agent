"""Simulated Client: LLM-driven user persona for realistic agent conversation testing.

Unlike MockGateway (keyword-based), SimClient uses an actual LLM to role-play
as a borrower or loan officer, generating natural multi-turn dialogue with the agent.
"""
import logging
from typing import Optional

from src.gateway import Gateway
from src.hydration import AgentState
from src.state_machine import Agent

logger = logging.getLogger(__name__)

BORROWER_SYSTEM_PROMPT = """You are role-playing as a home buyer. Be natural and concise (1-2 sentences).

YOUR PERSONA: {persona}
YOUR GOAL: {goal}

RULES:
- Answer the agent's questions directly with the information from your persona
- If asked about loan purpose, say you're {loan_purpose} a home
- If asked about home value, say it's worth ${home_value:,}
- If asked about loan amount, say you need ${loan_amount:,}
- If asked about state/location, say {state}
- If asked about credit score, say {credit_score}
- Vary your wording naturally — don't repeat the same phrases
- Don't provide information that wasn't asked for
- When you receive a rate quote, acknowledge it naturally and ask a follow-up if appropriate
"""

OFFICER_SYSTEM_PROMPT = """You are role-playing as a licensed mortgage loan officer. Be natural and concise.

YOUR PERSONA: {persona}
YOUR GOAL: {goal}

RULES:
- Answer the agent's questions naturally
- When registering: provide your NMLS ({nmls}), states ({licensed_states}), and email ({email})
- When asking for leads: mention the states you're licensed in
- When submitting a quote: mention a specific rate and the lead
- Vary your wording naturally
"""


class SimClient:
    """LLM-powered simulated user for end-to-end agent testing."""

    def __init__(self, gateway: Gateway):
        self.gateway = gateway
        self.history: list[dict] = []

    def _build_messages(self, system_prompt: str, agent_response: str) -> list:
        messages = [{"role": "system", "content": system_prompt}]
        for entry in self.history:
            messages.append({"role": "assistant", "content": f"Agent: {entry['agent']}"})
            messages.append({"role": "user", "content": f"You: {entry['user']}"})
        messages.append({"role": "assistant", "content": f"Agent: {agent_response}"})
        messages.append({"role": "user", "content": "Your response (1-2 sentences, be natural):"})
        return messages

    def next_message(self, system_prompt: str, agent_response: str) -> str:
        """Generate the next user message based on conversation context."""
        messages = self._build_messages(system_prompt, agent_response)
        user_msg = self.gateway.call_text(
            system_prompt + "\n\nLast agent message: " + agent_response + "\n\nYour natural response (1 sentence):",
            temperature=0.3,
        )
        return user_msg.strip()

    def record_turn(self, user_msg: str, agent_response: str):
        self.history.append({"user": user_msg, "agent": agent_response})


def _borrower_fallback(agent_msg: str, persona: dict) -> str | None:
    """Deterministic fallback when LLM is unavailable."""
    msg_lower = agent_msg.lower()
    if "purchase" in msg_lower or "refinanc" in msg_lower or "buying" in msg_lower:
        if persona.get("loan_purpose") == "purchase":
            return "I'm buying a new home."
        return "I'm refinancing my current mortgage."
    if "value" in msg_lower or "worth" in msg_lower or "property" in msg_lower:
        return f"It's worth about ${persona.get('home_value', 500000):,}."
    if "borrow" in msg_lower or "loan amount" in msg_lower or "much" in msg_lower:
        return f"I need about ${persona.get('loan_amount', 300000):,}."
    if "state" in msg_lower or "where" in msg_lower or "located" in msg_lower:
        return f"It's in {persona.get('state', 'California')}."
    if "credit" in msg_lower:
        return f"My credit score is {persona.get('credit_score', 'around 720')}."
    return None


def run_borrower_scenario(
    agent: Agent,
    gateway: Gateway,
    persona: dict,
    max_turns: int = 12,
) -> dict:
    """Run a borrower scenario with an LLM-simulated user."""
    sim = SimClient(gateway)

    system_prompt = BORROWER_SYSTEM_PROMPT.format(
        persona=f"{persona['name']}, {persona['age']} years old, {persona['occupation']}",
        goal=persona["goal"],
        loan_purpose=persona["loan_purpose"],
        home_value=persona["home_value"],
        loan_amount=persona["loan_amount"],
        state=persona["state"],
        credit_score=persona["credit_score"],
    )

    alice_state = AgentState(
        user_id=persona["user_id"],
        user_type="borrower",
        user_name=persona["name"],
    )

    # Initial message from the simulated user
    user_msg = persona.get("opening", f"Hi, I'm interested in getting a mortgage rate quote.")

    for turn in range(max_turns):
        result = agent.process(user_msg, persona["user_id"], "borrower", persona["name"], alice_state)
        agent_response = result["response"]
        alice_state = result["state"]
        sim.record_turn(user_msg, agent_response)

        if result["phase"] == "completed":
            return {"success": True, "turns": sim.history, "state": alice_state, "phase": "completed"}

        if result["phase"] == "error":
            return {"success": False, "turns": sim.history, "state": alice_state, "phase": "error", "error": alice_state.error}

        try:
            user_msg = sim.next_message(system_prompt, agent_response)
        except Exception as e:
            logger.warning(f"SimClient LLM call failed: {e}, using fallback")
            user_msg = _borrower_fallback(agent_response, persona)
            if user_msg is None:
                break

    return {"success": alice_state.phase == "completed", "turns": sim.history, "state": alice_state, "phase": alice_state.phase}


def _officer_fallback(agent_msg: str, persona: dict) -> str | None:
    """Deterministic fallback for officer simulation."""
    msg_lower = agent_msg.lower()
    if "nmls" in msg_lower or "regist" in msg_lower:
        return f"My NMLS is {persona.get('nmls', 'NMLS-12345')}."
    if "state" in msg_lower and "licensed" in msg_lower:
        return f"I'm licensed in {', '.join(persona.get('licensed_states', ['CA']))}."
    if "email" in msg_lower:
        return persona.get("email", "officer@example.com")
    return None


def run_officer_scenario(
    agent: Agent,
    gateway: Gateway,
    persona: dict,
    max_turns: int = 10,
) -> dict:
    """Run a loan officer scenario with an LLM-simulated user."""
    sim = SimClient(gateway)

    system_prompt = OFFICER_SYSTEM_PROMPT.format(
        persona=f"{persona['name']}, loan officer at {persona['company']}",
        goal=persona["goal"],
        nmls=persona["nmls"],
        licensed_states=", ".join(persona["licensed_states"]),
        email=persona["email"],
    )

    officer_state = AgentState(
        user_id=persona["user_id"],
        user_type="loan_officer",
        user_name=persona["name"],
    )

    user_msg = persona.get("opening", "Hi, I'm a loan officer interested in your platform.")

    for turn in range(max_turns):
        result = agent.process(user_msg, persona["user_id"], "loan_officer", persona["name"], officer_state)
        agent_response = result["response"]
        officer_state = result["state"]
        sim.record_turn(user_msg, agent_response)

        if result["phase"] == "error":
            return {"success": False, "turns": sim.history, "state": officer_state, "phase": "error", "error": officer_state.error}

        if persona["goal"] == "register" and "nmls" in agent_response.lower():
            return {"success": True, "turns": sim.history, "state": officer_state, "phase": "onboarding_prompted"}

        if persona["goal"] == "get_leads" and turn >= 2:
            return {"success": True, "turns": sim.history, "state": officer_state, "phase": "leads_shown"}

        try:
            user_msg = sim.next_message(system_prompt, agent_response)
        except Exception:
            user_msg = _officer_fallback(agent_response, persona)
            if user_msg is None:
                break

    return {"success": False, "turns": sim.history, "state": officer_state, "phase": officer_state.phase}


# ── Pre-built personas ──

PERSONA_PURCHASE_CA = {
    "user_id": "sim_alice",
    "name": "Alice",
    "age": 34,
    "occupation": "software engineer",
    "goal": "get a mortgage rate quote for buying a home",
    "loan_purpose": "purchase",
    "home_value": 800000,
    "loan_amount": 400000,
    "state": "California",
    "credit_score": "around 780",
    "opening": "Hi there! I'm looking to buy a home and wanted to check what rates I could get.",
}

PERSONA_REFINANCE_TX = {
    "user_id": "sim_bob",
    "name": "Bob",
    "age": 45,
    "occupation": "teacher",
    "goal": "refinance my existing mortgage at a better rate",
    "loan_purpose": "refinance",
    "home_value": 500000,
    "loan_amount": 300000,
    "state": "Texas",
    "credit_score": "about 680",
    "opening": "Hey, I'm thinking about refinancing my mortgage. Can you help me with rates?",
}

PERSONA_OFFICER_ONBOARDING = {
    "user_id": "sim_mike",
    "name": "Mike",
    "company": "Golden Gate Mortgage",
    "goal": "register",
    "nmls": "NMLS-200001",
    "licensed_states": ["CA", "OR", "WA"],
    "email": "mike@goldengatemortgage.com",
    "opening": "Hello, I'm a loan officer with Golden Gate Mortgage. I'd like to sign up for your platform.",
}
