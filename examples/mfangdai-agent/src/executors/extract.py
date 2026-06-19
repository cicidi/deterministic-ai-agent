"""Layer 1: Entity Extraction — E→V→T pipeline with hybrid fallback."""
import re

from src.hydration import AgentState
from src.executors.classify import LEAD_REQUIRED_FIELDS, IntentClassificationResult


# ── Regex-based deterministic fallback extraction ──

HOME_VALUE_PATTERNS = [
    (r'(?:home|house|property|condo)(?:\s+is)?\s*(?:worth|valued?\s*(?:at)?|price(?:d?\s*(?:at)?)?)\s*\$?(\d[\d,.]*(?:\s*k)?)', 1),
    (r'\$?(\d[\d,.]*(?:\s*k)?)\s*(?:home|house|property)', 1),
    (r'(?:worth|value)\s*(?:is|about|around|of)?\s*\$?(\d[\d,.]*(?:\s*k)?)', 1),
]

LOAN_AMOUNT_PATTERNS = [
    (r'(?:need|want|borrow|loan\s*(?:amount|of)?)\s*\$?(\d[\d,.]*(?:\s*k)?)', 1),
    (r'(?:borrowing|looking\s*(?:for|at|to\s*borrow))\s*\$?(\d[\d,.]*(?:\s*k)?)', 1),
    (r'loan\s*(?:of|for|amount)?\s*\$?(\d[\d,.]*(?:\s*k)?)', 1),
]

STATE_PATTERNS = [
    (r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b', 0),
]

LOAN_PURPOSE_PATTERNS = [
    (r'\b(buy|buying|purchas\w*|new\s*(?:home|house|property))\b', "purchase"),
    (r'\b(refinanc\w*|refi)\b', "refinance"),
]

CREDIT_SCORE_PATTERNS = [
    (r'(?:credit\s*(?:score)?\s*(?:is|of|about|around)?)\s*(\d{3})\b', 1),
    (r'(?:score\s*(?:is|of)?)\s*(\d{3})\b', 1),
]


def _parse_number(text: str) -> float:
    """Parse a number string, handling commas, spaces, and k/m suffixes."""
    clean = text.replace(",", "").replace(" ", "").lower()
    if clean.endswith("k"):
        return float(clean[:-1]) * 1000
    if clean.endswith("m"):
        return float(clean[:-1]) * 1000000
    return float(clean)


def _deterministic_extract(user_message: str) -> dict:
    """Extract entities from raw user message using regex patterns.
    
    This is the deterministic fallback when LLM extraction fails or returns empty.
    """
    entities = {}

    # Home value
    for pattern, group_idx in HOME_VALUE_PATTERNS:
        m = re.search(pattern, user_message, re.IGNORECASE)
        if m:
            try:
                entities["home_value"] = _parse_number(m.group(group_idx))
            except ValueError:
                pass
            break

    # Loan amount
    for pattern, group_idx in LOAN_AMOUNT_PATTERNS:
        m = re.search(pattern, user_message, re.IGNORECASE)
        if m:
            try:
                entities["loan_amount"] = _parse_number(m.group(group_idx))
            except ValueError:
                pass
            break

    # State
    for pattern, group_idx in STATE_PATTERNS:
        m = re.search(pattern, user_message)
        if m:
            entities["state"] = m.group(group_idx)
            break

    # Loan purpose
    for pattern, value in LOAN_PURPOSE_PATTERNS:
        if re.search(pattern, user_message, re.IGNORECASE):
            entities["loan_purpose"] = value
            break

    # Credit score
    for pattern, group_idx in CREDIT_SCORE_PATTERNS:
        m = re.search(pattern, user_message, re.IGNORECASE)
        if m:
            entities["credit_score_range"] = _normalize_credit_score(m.group(group_idx))
            break

    return entities


# ── Field prompts ──

NEXT_FIELD_PROMPTS = {
    "loan_purpose": "Are you buying a new home (purchase) or refinancing an existing mortgage?",
    "home_value": "What is the estimated value of the property?",
    "loan_amount": "How much are you looking to borrow?",
    "state": "Which state is the property located in? (e.g., CA, NY, TX)",
    "credit_score_range": "What is your approximate credit score range? (e.g., 700-719, 720-739, or just give me a number)",
}


CREDIT_SCORE_MAP = {
    300: "below_620", 350: "below_620", 400: "below_620", 450: "below_620",
    500: "below_620", 550: "below_620", 580: "below_620", 600: "below_620",
    620: "620_639", 640: "640_659", 660: "660_679", 680: "680_699",
    700: "700_719", 720: "720_739", 740: "740_759", 760: "760_779",
    780: "780_799", 800: "800_plus", 850: "800_plus",
}


def _normalize_credit_score(score_str: str) -> str:
    """Deterministic fallback: map numeric score or hyphen range to range bucket."""
    import re
    hyphen = re.match(r"(\d+)\s*[-–]\s*(\d+)", str(score_str))
    if hyphen:
        score_str = f"{hyphen.group(1)}_{hyphen.group(2)}"
    if score_str in CREDIT_SCORE_MAP.values():
        return score_str
    try:
        score = int(float(score_str))
    except (ValueError, TypeError):
        return score_str
    closest = min(CREDIT_SCORE_MAP.keys(), key=lambda k: abs(k - score))
    return CREDIT_SCORE_MAP[closest]


def _normalize_state(state_str: str) -> str:
    """Deterministic: normalize state to 2-letter code."""
    state_str = state_str.strip().upper()
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    }
    if state_str in us_states:
        return state_str
    state_names = {
        "CALIFORNIA": "CA", "TEXAS": "TX", "NEW YORK": "NY", "FLORIDA": "FL",
        "ILLINOIS": "IL", "PENNSYLVANIA": "PA", "OHIO": "OH", "GEORGIA": "GA",
        "NORTH CAROLINA": "NC", "MICHIGAN": "MI", "NEW JERSEY": "NJ",
        "VIRGINIA": "VA", "WASHINGTON": "WA", "ARIZONA": "AZ",
        "MASSACHUSETTS": "MA", "TENNESSEE": "TN", "INDIANA": "IN",
        "MISSOURI": "MO", "MARYLAND": "MD", "WISCONSIN": "WI",
        "COLORADO": "CO", "MINNESOTA": "MN", "SOUTH CAROLINA": "SC",
        "ALABAMA": "AL", "LOUISIANA": "LA", "KENTUCKY": "KY", "OREGON": "OR",
        "OKLAHOMA": "OK", "CONNECTICUT": "CT", "IOWA": "IA", "UTAH": "UT",
        "NEVADA": "NV", "ARKANSAS": "AR", "MISSISSIPPI": "MS", "KANSAS": "KS",
        "NEW MEXICO": "NM", "NEBRASKA": "NE", "IDAHO": "ID",
        "WEST VIRGINIA": "WV", "HAWAII": "HI", "NEW HAMPSHIRE": "NH",
        "MAINE": "ME", "RHODE ISLAND": "RI", "MONTANA": "MT", "DELAWARE": "DE",
        "SOUTH DAKOTA": "SD", "NORTH DAKOTA": "ND", "ALASKA": "AK",
        "VERMONT": "VT", "WYOMING": "WY",
    }
    return state_names.get(state_str, state_str)


def _normalize_loan_purpose(purpose_str: str) -> str:
    """Deterministic: normalize loan purpose."""
    p = purpose_str.strip().lower()
    if p in ("purchase", "buy", "buying", "new home", "purchasing"):
        return "purchase"
    if p in ("refinance", "refi", "refinancing", "refinance mortgage"):
        return "refinance"
    return purpose_str


def extract_and_merge(
    state: AgentState,
    intent_result: IntentClassificationResult,
) -> tuple[dict, list[str]]:
    """Extract entities from LLM + deterministic fallback, merge with collected_data."""
    extracted = dict(intent_result.entities) if intent_result.entities else {}

    # Hybrid fallback: if LLM extracted nothing, try deterministic regex
    if not extracted and state.messages:
        user_msg = state.messages[-1].get("content", "")
        extracted = _deterministic_extract(user_msg)

    merged = {**state.collected_data, **extracted}

    # Deterministic transforms
    if "credit_score_range" in merged and merged["credit_score_range"]:
        merged["credit_score_range"] = _normalize_credit_score(str(merged["credit_score_range"]))
    if "state" in merged and merged["state"]:
        merged["state"] = _normalize_state(str(merged["state"]))
    if "loan_purpose" in merged and merged["loan_purpose"]:
        merged["loan_purpose"] = _normalize_loan_purpose(str(merged["loan_purpose"]))

    missing = [f for f in LEAD_REQUIRED_FIELDS if f not in merged or not merged[f]]
    return merged, missing


def get_next_missing_field(missing_fields: list[str]) -> str | None:
    """Return the next required field to ask for."""
    if not missing_fields:
        return None
    return missing_fields[0]


def get_prompt_for_field(field_name: str) -> str:
    """Get the prompt text for asking a specific field."""
    return NEXT_FIELD_PROMPTS.get(field_name, f"Please provide your {field_name}.")
