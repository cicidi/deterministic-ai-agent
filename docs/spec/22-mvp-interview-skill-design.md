# MVP Interview Skill — Design

**Topic:** Redesign `implement-interview` skill from document-output to code-output, with time-boxed adaptive interview depth
**Status:** Design approved, pending implementation
**Date:** 2026-06-18

## 1. Motivation

The existing `implement-interview` skill produces a Markdown implementation plan document. Developers then manually implement the agent from that plan. The goal is to upgrade the skill to generate runnable Python code directly, with an interview process that adapts its depth to the developer's available time budget and focuses exclusively on MVP essentials.

## 2. Core Changes

| Dimension | Before | After |
|-----------|--------|-------|
| Output | Markdown Implementation Plan | Runnable Python project (`python main.py`) |
| Interview structure | 6 fixed phases (all asked) | 4-level priority layers, depth determined by time budget |
| Defaults | None (every question asked) | Smart defaults from spec for all non-MVP decisions |
| File size enforcement | None | Auto-split at 1000 lines per file, 50 lines per method |

## 3. Architecture Decisions

### AD-1: Time-boxed adaptive depth
- **Decision:** Interview starts with a single meta question: "How much time do you have?"
- **Rationale:** Developers have varying time availability. Forcing a 1-hour interview on someone with 15 minutes causes abandonment. Adapting depth preserves completion rate.
- **Trade-off:** Less depth = more default assumptions = potentially more post-generation edits.

### AD-2: 4-level question priority
- **Decision:** Questions are grouped into 4 priority levels. Level N is only asked if time budget allows.
- **Level 1 (always asked):** Product goal, users, core workflow
- **Level 2 (30min+):** Domain model — entities, states, transitions
- **Level 3 (30min+ partial, 1h+ full):** LLM provider, auth, external APIs, RAG
- **Level 4 (1h+ only):** Second workflow, env config, observability

### AD-3: All strategy decisions default to spec recommendations
- **Decision:** Extract strategy (`hybrid`), Validate strategy (`durable_rules`), Rule engine (`durable_rules`), Permission engine (`native`), LLM Gateway strategy (`hybrid`), Response strategy (`pure_message`) — all use spec default. Only override if developer explicitly brings it up.
- **Rationale:** These are framework-level concerns. A developer building an MVP doesn't need to decide them. They can change config later.

### AD-4: No prompt engineering in interview
- **Decision:** LLM prompts (intent classification, extraction, response generation) are generated from templates, not discussed in interview.
- **Rationale:** Prompt engineering is an optimization task, not an MVP definition task. Templates based on spec examples suffice.

## 4. Interview Flow

```
START
  │
  ▼
META: "How much time do you have?" → 15min / 30min / 1h+
  │
  ▼
LEVEL 1 — Goal & Product (always)
  ├─ Q1: What product are you building?
  ├─ Q2: Who are the users?
  ├─ Q3: What is the primary goal? (successful interaction = ?)
  └─ Q4: What is the #1 MVP workflow? (describe step by step)
  │
  ▼
LEVEL 2 — Domain Model (30min+ only)
  ├─ Q5: What entities does the workflow operate on? (name + key fields)
  ├─ Q6: What phases/states does the workflow have?
  └─ Q7: Key transitions: "if X, go to Y"
  │
  ▼
LEVEL 3 — Strategy (30min+: choose 1-2 most important; 1h+: all)
  ├─ Q8: LLM provider? (default: deepseek-v4)
  ├─ Q9: Auth method? (default: API key for dev)
  ├─ Q10: External APIs? (payment, CRM, policy lookup...)
  └─ Q11: Need RAG / knowledge base?
  │
  ▼
LEVEL 4 — Extended (1h+ only)
  ├─ Q12: Second workflow?
  ├─ Q13: Environment differences (dev/e2e/prod)?
  └─ Q14: Observability tool? (LangSmith / LangFuse)
  │
  ▼
GENERATE
  └─ Produce Python project in target directory
```

### Per-level rules
- Level 1: 2-3 minutes. Must complete even at 15min budget.
- Level 2: 5-8 minutes. If developer doesn't know exact fields, generate a reasonable skeleton they can fill.
- Level 3: 3-5 minutes. Each question offers a shortcut: "default" or "skip."
- Level 4: 5-8 minutes. Exploratory; developer can skip any question.

## 5. Code Generation Output

### Generated project structure

```
{product-slug}/
├── config/
│   ├── domain_model.yaml
│   ├── workflow.yaml
│   └── intents.yaml
├── src/
│   ├── state_machine.py
│   ├── executors/
│   │   ├── extract.py
│   │   ├── classify.py
│   │   ├── decide.py
│   │   └── respond.py
│   ├── gateway.py
│   └── hydration.py
├── tests/
│   └── test_workflow.py
└── main.py
```

### Generated content guarantees
- `state_machine.py`: LangGraph StateGraph with nodes, edges, conditional routing
- `executors/decide.py`: Skeleton with placeholder business logic
- `executors/extract.py`: E→V→T pipeline with LLM call + type coercion
- `executors/classify.py`: Intent classification prompt with system intents + custom intents
- `executors/respond.py`: Response generation with goal checker call
- `gateway.py`: `output_schema`, JSON validation, retry on violation
- `hydration.py`: Selectively refresh AgentState
- `config/domain_model.yaml`: Entity, State, Transition definitions
- `config/workflow.yaml`: Strategy selections, env config, tool registry
- `config/intents.yaml`: Custom intent definitions
- `tests/test_workflow.py`: Happy-path test with mocked LLM
- `main.py`: Runnable entry point

### File size enforcement
- **File ≤ 1000 lines:** If domain_model.yaml would exceed 1000 lines, split by workflow (`domain_model_quote.yaml`, `domain_model_claim.yaml`) with `$ref` references in the parent.
- **Method ≤ 50 lines:** If any executor method exceeds 50 lines, split into sub-modules (`extract_validator.py`, `extract_transformer.py`).
- **Warning not error:** If a file would exceed 1000 lines, emit a warning and offer the split strategy rather than silently truncating.

### Code conventions (per project principles)
- All LLM output is JSON, validated through LLM Gateway
- Decision nodes are 100% deterministic code (no LLM fallback in Layer 2)
- AgentState uses Copy-on-Write + reducer merge (LangGraph semantics)
- Every LLM node gets +1 extra retry in retry budget
- Mermaid state diagram auto-generated as comment at top of `state_machine.py`

## 6. Scope: What Is NOT Generated

The following are explicitly out of scope for MVP code generation:
- CI/CD pipeline configuration
- Production deployment manifests (Docker, K8s)
- LangSmith/LangFuse integration wiring (config stubs only)
- Rate limiting implementation (config stubs only)
- A2A/MCP protocol server code
- pycasbin RBAC/ABAC rules (native YAML allowlists only)
- PII scrubbing integration (Microsoft Presidio — config stub only)

These are documented as "next steps" in a generated README.

## 7. Success Criteria

1. A developer with a product idea can complete the interview and have a runnable `python main.py` agent in the target time budget
2. Generated code follows all project conventions (file ≤1000 lines, method ≤50 lines, JSON-only LLM output, deterministic Layer 2)
3. The `tests/test_workflow.py` passes out of the box (mocked LLM responses)
4. A developer who says "I don't know" receives reasonable defaults for all questions
5. The interview never asks framework-level strategy questions (extract strategy, rule engine, etc.) unless the developer brings it up first

## 8. Open Decisions (for implementation phase)

- Whether to use Jinja2 templates for code generation or string interpolation
- Whether `python main.py` runs as CLI, FastAPI server, or both
- Exact prompt templates for intent classification and extraction (generated from spec examples)
