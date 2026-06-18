# TODO — Deterministic Workflow Framework

Last updated: 2026-06-17

---

## Skills (Planned)

### 1. intent-analysis

**Status:** 🔲 TODO

**What:** Analyzes production conversation logs to find intents the current intent classifier cannot handle. Outputs a prioritized list of gaps with recommendations.

**Process:**
1. Load production conversation logs
2. For each conversation, check: did the intent classifier produce `unrecognized_intent`? Did the user rephrase or retry?
3. Group unrecognized utterances by semantic similarity
4. For each cluster, determine:
   - Is this a new intent we should add?
   - Is this an edge case of an existing intent?
   - Is this out of scope (should not handle)?
5. Output prioritized report: "Today we missed X intents. Yesterday we missed Y. Change: +/-Z"

**Principle:** We can't handle all intents. Target = today better than yesterday.

**When to run:** After each prod deployment, or weekly.

---

### 2. tdd (Test-Driven Development for Workflows)

**Status:** 🔲 TODO

**What:** After the implement-interview skill produces an implementation plan, this skill generates test cases BEFORE any code is written. Mocks LLMs to save tokens — only calls real LLM when explicitly requested.

**Process:**
1. Load the implementation plan (from implement-interview)
2. For each workflow, generate:
   - **User dialog test cases** — what users say, expected agent responses
   - **Extract node test cases** — mock user input → expected extracted entities
   - **Validate node test cases** — entity values → expected validation errors/passes
   - **Decision node test cases** — entity state → expected routing decisions
   - **Response node test cases** — outcomes → expected response themes
3. Mock LLM by default:
   - `mock_llm = lambda prompt, schema: pre_canned_response_for_this_test_case`
   - Only when `--use-real-llm` flag is set → call actual LLM API
4. Run tests:
   ```
   uv run pytest tests/ --mock-llm          # fast, free, deterministic
   uv run pytest tests/ --use-real-llm      # integration test, costs tokens
   ```
5. Enforce red-green-refactor cycle

**Principles:**
- Tests defined before implementation
- Mock LLM saves tokens (same as traditional API integration test mocking)
- Only call real LLM when user explicitly says so

---

### 3. test-client-create

**Status:** 🔲 TODO

**What:** Creates a simulated test client that plays the role of "the user." The client receives our agent's response, understands the conversation state, and generates the next user message — measuring end-to-end transaction completion rate.

**Process:**
1. Load the workflow definition (domain model + YAML)
2. Create a test client LLM with a specific persona:
   ```
   You are a test user. Your goal is to complete the "{goal}" workflow.
   You will receive the agent's response and must respond naturally.
   Follow the conversation to completion. Do NOT cooperate artificially —
   act like a real user: sometimes change your mind, ask questions, provide
   partial info.
   ```
3. Run N parallel conversation sessions:
   ```
   Session 1: User wants a home insurance quote → agent responds → user replies → ... → complete or abandon
   Session 2: User wants to file a claim → ...
   ...
   Session N: ...
   ```
4. Measure:
   - **Transaction completion rate**: % of sessions that reached a terminal state
   - **Average turns to completion**
   - **Drop-off point**: which step users abandon at
   - **Intent switch frequency**: how often users change their mind mid-flow
   - **Clarification rate**: how often the agent had to re-ask
5. Output report + conversation transcripts

**When to run:** Before each production deployment, or as part of CI.

---

## Spec Documents (Done)

- [x] HLD (v0.7.0)
- [x] Intent Classification (v0.3.0)
- [x] State Machine Design (v0.6.0)
- [x] Extraction Layer (v0.4.0)
- [x] Domain Model (v0.3.0)
- [x] Routing & Execution (v0.3.0)
- [x] Response Generation (v0.4.0)
- [x] LLM Gateway (v0.1.0)
- [x] Tool Ecosystem (v0.3.0)
- [x] Environment Config (v0.3.0)
- [x] Auth & Token Verification (v0.2.0)

## Skills (Done)

- [x] issue-create
- [x] implement-interview
- [x] evals-create
- [x] ai-cowork-install

---

## Future Work

- [ ] RoleResolver implementation (auth spec §5.1 interface placeholder)
- [ ] Python reference implementation
- [ ] Code-gen skill (downstream from implement-interview)
- [ ] MCP server for real-time spec queries (like CrewAI's ask-docs)
- [ ] LangFlow custom components for framework nodes
