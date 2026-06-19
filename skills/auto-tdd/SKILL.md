---
name: auto-tdd
description: |
  Use when implementing features or fixing bugs with a continuous multi-agent TDD loop that never stops until the work is truly complete. Dispatches Agent-A (impl), Agent-B (test), Agent-C (arbitration judge), and Agent-D (quality judge) in a self-perpetuating cycle. Enforces deterministic fixed-scenario tests before simulated LLM tests. Quality judge evaluates every test round for turn coherence, response quality, and errors.
user-invocable: true
---

# Auto-TDD — Continuous Multi-Agent Arbitration Loop

Continuous multi-agent test-driven development with automatic arbitration and quality evaluation. The loop NEVER declares "done" until all tiers of testing pass and the quality judge signs off. When new issues are discovered mid-loop, they are automatically added to the task queue — the agent keeps working.

## Philosophy

Most TDD workflows stop too early. They declare "done" after the first green bar, leaving edge cases untested, quality unevaluated, and loose ends uncommitted. Auto-TDD is different: **the agent does not stop until the work is truly, verifiably complete.** Every deficiency becomes a new task. Every test round is judged for quality. The loop only terminates when there is literally nothing left to do.

## When to Use

- Building a new feature from spec with TDD
- Fixing bugs discovered by test failures
- Implementing changes where code and tests need to co-evolve
- Developer wants automated quality gates with human-like review
- Need to run a continuous fix-test loop without manual intervention
- Converting a spec into a fully-tested, production-ready implementation

## When NOT to Use

- Pure research or exploration with no tests
- Single-line config changes
- Tasks where test expectations are perfectly known upfront
- Writing documentation or non-code artifacts

## Common Rationalizations (and why they are wrong)

| Rationalization | Reality |
|-----------------|---------|
| "Tests are green, we're done" | Edge cases, FT scenarios, sim tests, and quality evaluation may still be missing |
| "One happy path test covers it" | You must draw inferences (举一反三): change one dimension at a time and write variant tests until exhausted |
| "That edge case is too unlikely" | Edge cases are where bugs live. Draw 2-3 inferences from every edge case too |
| "That's a nice-to-have, not MVP" | If the user specified it, it's required. Add it to the task list |
| "I'll add those tests later" | Later never comes. Add them now or create a tracked task |
| "The mock tests are good enough" | Mock tests are Tier 1. Simulated LLM tests are Tier 2. Both are required |
| "The quality check is subjective, skip it" | Quality judge finds patterns humans miss. It's part of the process |
| "This is just a simple change" | Simple changes cascade. Every change triggers the full loop |

## Process

### Phase 0: Setup & Commitment

1. Load all spec documents and understand the full requirements
2. Create a comprehensive todo list with **every** known task, user-specified and spec-derived
3. Define completion criteria explicitly:
   - All tiers of tests pass (mock FT → simulated LLM → quality evaluation)
   - All user-specified scenarios are covered
   - No uncommitted changes remain
   - Quality judge has signed off on every test round
4. **COMMIT to the loop**: The agent will not stop until all criteria are met. If the user interrupts, save state and resume.

### Phase 1: Agent-A — Implementation

Agent-A writes or refines code following framework conventions:
- File ≤ 1000 lines, method ≤ 50 lines
- Layer 2 (business logic) must be 100% deterministic
- All LLM output must be JSON via Gateway
- Copy-on-Write for state mutations
- Every method has a clear single responsibility

**Output:** list of files created/modified, known open questions.

**Anti-stall rule:** If Agent-A finds a pre-existing bug, it adds a "fix:" task to the todo list and fixes it — it does NOT skip it because "that's not what I was asked to do."

### Phase 2: Agent-B — Test Writing (Three-Tier Protocol)

Tests are written in strict priority order. Each tier must pass before the next tier is run.

#### Tier 1: Deterministic Fixed-Scenario Tests (MUST pass first)

These tests use a **MockGateway** with fixed, keyword-based intent classification. The same inputs always produce the same outputs. Every run is identical.

**Writing protocol for Tier 1 — "举一反三" (draw inferences from one case):**

For EVERY test you write, immediately write 2-3 variant tests by changing one dimension at a time. Never stop at "one test covers it."

**Step 1 — Happy path, then draw inferences:**

Write the base happy path. Then ask: "What if the same scenario played out with different values?" and write those too.

```
Base happy path (purchase, CA, $800k home, $400k loan, 780 credit)
  → Inference 1: same flow, refinance instead of purchase
  → Inference 2: same flow, TX instead of CA (different state)
  → Inference 3: same flow, $500k home, $300k loan (different amounts)
  → Inference 4: same flow, 620 credit (different credit tier)
  → Inference 5: same flow, multi-family instead of single-family
```

**Step 2 — Edge cases by analogy, then draw inferences:**

For each edge case you identify, ask "what else could go wrong at this step?" and write tests. Then for each of those, draw 2-3 inferences.

```
Base edge case: customer says $800k home, then corrects to $500k
  → Inference 1: customer corrects loan amount instead of home value
  → Inference 2: customer corrects state (CA → NY)
  → Inference 3: customer corrects loan purpose (purchase → refinance)

Base edge case: customer asks clarifying question mid-flow
  → Inference 1: customer asks about fees
  → Inference 2: customer asks about loan types
  → Inference 3: customer asks about the company/agent identity

Base edge case: customer gives vague answer ("I don't know")
  → Inference 1: customer is vague about credit score
  → Inference 2: customer is vague about home value
  → Inference 3: customer is vague about everything
```

**Step 3 — The exhaustion check:**

After writing tests, ask: "What haven't I tested?" Go through each field in the domain model and verify:
- Is there a test where this field is missing?
- Is there a test where this field is wrong/corrected?
- Is there a test where this field is at its boundary (min, max, empty)?
- Is there a test where multiple fields are provided at once?
- Is there a test where the order of field collection changes?

If ANY answer is "no," write that test now.

**Fixed language, fixed order:** Every test message is a literal string. The conversation always follows the same sequence. No randomization, no LLM generation. This guarantees deterministic behavior — the same test run 100 times produces the same result 100 times.

#### Tier 2: Simulated LLM Client Tests (run AFTER Tier 1 passes)

These tests use an actual LLM to role-play as the user. The SimClient generates responses based on the agent's output. Each run may produce different but valid conversations.

**Writing protocol for Tier 2 — "举一反三":**

Same inference principle applies. For each persona:
```
Base persona (Alice, purchase, CA, 780 credit)
  → Inference 1: Bob, refinance, TX, 680 credit
  → Inference 2: Carol, first-time buyer, FL, 620 credit
  → Inference 3: Dave, jumbo loan, NY, 800 credit
  → Inference 4: Eva, self-employed, IL, unknown credit
```

**Persona definition:**
1. Define a **persona** (name, situation, goal, key numbers)
2. Define a **system prompt** that instructs the LLM how to behave
3. Include **fallback responses** for when the LLM is unavailable (deterministic canned responses)
4. Run multiple times to verify consistency
5. Test with different LLM models (via `LLM_MODEL` env var)

**Multi-model requirement:** Tier 2 tests must be run against at least 2 different models (e.g., deepseek-v4-flash + gpt-5-nano) to verify model-agnostic behavior.

#### Tier 3: Quality Judge (Agent-D) — per-round evaluation (run AFTER Tier 1 and Tier 2)

After all tests pass, Agent-D evaluates quality. **举一反三 applies here too:** for every issue found, ask "where else could this same problem occur?" and check those places.

Agent-D reviews:
1. **Turn-by-turn analysis**: For each turn in each scenario:
   - Did the agent ask the right question given the state?
   - Did the simulated user respond naturally?
   - Was any turn redundant or confusing?
2. **Response quality**: For each agent response:
   - Was the information accurate (rate quote math correct)?
   - Was the tone appropriate (professional, warm)?
   - Was the response concise (no unnecessary text)?
3. **Error detection**: Any pattern of:
   - Repeatedly asking the same question (stuck loop)
   - Missing fields that should have been collected
   - Incorrect state transitions
4. **Multi-turn coherence**: Does the full conversation make sense as a human dialogue?

**Agent-D's output is a quality report** with:
- Overall score (1-10)
- Per-scenario breakdown
- Specific recommendations for improvement
- Any new tasks to add to the todo list

If Agent-D finds issues, they become new tasks and the loop continues.

### Phase 3: Test Execution & Loop

Run `python -m pytest tests/ -v`. For each outcome:

**All three tiers pass → DONE.** The quality judge has signed off. Commit.

**Any tier fails → enter arbitration:**

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  1. Agent-A reads the failing test                  │
│  2. Agent-B reads the failing test                  │
│  3. Both analyze root cause:                        │
│     - Is the test wrong? (bad expectation)           │
│     - Is the code wrong? (bug / missing logic)       │
│  4. If they AGREE:                                  │
│     → Wrong agent fixes it immediately              │
│     → Loop back to test execution                   │
│  5. If they DISAGREE:                               │
│     → Agent-C (Judge) reviews both arguments        │
│     → Judge rules: "Fix X in file Y: line Z"        │
│     → Wrong agent fixes it                          │
│     → Loop back to test execution                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Phase 4: Agent-C — Arbitration Judge

When Agent-A and Agent-B cannot agree on root cause:

1. Read the failing test, implementation code, and the spec
2. Review both agents' arguments
3. Apply these heuristics (in order):
   - **Spec wins** over implementation preference
   - **Framework conventions** win over stylistic choice
   - **Test should match actual behavior**, not ideal behavior
   - If ambiguous: fix the code to make the test pass, then review if the test expectation is too strict
4. Issue ruling: "Fix X in file Y: line Z" with specific instruction
5. The losing agent implements the fix immediately

**Judge must cite the spec section or convention** that supports the ruling. No "I think" — only "per spec §X.Y".

### Phase 5: Agent-D — Quality Judge

After all tests pass, Agent-D evaluates the **quality** of the test rounds themselves. This is NOT about pass/fail — it's about coherence, accuracy, and completeness.

Agent-D reviews:
1. **Turn-by-turn analysis**: For each turn in each scenario:
   - Did the agent ask the right question given the state?
   - Did the simulated user respond naturally?
   - Was any turn redundant or confusing?
2. **Response quality**: For each agent response:
   - Was the information accurate (rate quote math correct)?
   - Was the tone appropriate (professional, warm)?
   - Was the response concise (no unnecessary text)?
3. **Error detection**: Any pattern of:
   - Repeatedly asking the same question (stuck loop)
   - Missing fields that should have been collected
   - Incorrect state transitions
4. **Multi-turn coherence**: Does the full conversation make sense as a human dialogue?

**Agent-D's output is a quality report** with:
- Overall score (1-10)
- Per-scenario breakdown
- Specific recommendations for improvement
- Any new tasks to add to the todo list

If Agent-D finds issues, they become new tasks and the loop continues. The quality judge has veto power over "done."

### Phase 6: Self-Managing Task Queue

During any phase, agents may discover new issues. These are **immediately** added to the todo list — never deferred or skipped.

| Discovered by | Example | Priority |
|--------------|---------|----------|
| Agent-A finds a bug | "create_borrower email collision" | high |
| Agent-B finds an untested path | "gateway retry exhaustion untested" | high |
| Agent-C finds a spec violation | "state.user_id overwritten violates CoW" | high |
| Agent-D finds a quality issue | "turn 3 is redundant, asking twice" | medium |
| Test run reveals missing feature | "no restart-flow after completed phase" | medium |
| User gives new requirement mid-loop | "add data validation layer" | high |

**The loop continues until the todo list is empty AND all three test tiers pass AND Agent-D signs off.**

## Anti-Stall Protocol

**Why tasks stalled previously and how to prevent it:**

| Failure Mode | Prevention |
|-------------|------------|
| Agent declared "done" after first green bar, ignoring edge cases | Phase 2 Tier 1 step 2: edge cases by analogy, write until exhausted |
| Agent skipped FT because "mock tests are enough" | Tier 2 (sim LLM) is MANDATORY, not optional |
| Agent stopped after commit without quality review | Phase 5 Agent-D must run before declaring done |
| User's verbal requirements were not converted to tasks | Phase 0: every user requirement = a todo item, verified by checklist |
| Agent rationalized "that's out of scope" for user-specified work | Common Rationalizations table above — check against it |
| Loop stopped because agent didn't know what to do next | If todo is empty but work feels incomplete, re-read user requirements and add missing items |
| Tasks were completed but never verified | Every "completed" task must have evidence: test passing, file committed, or output shown |

## Rules

1. **Never stop before complete.** The loop terminates ONLY when: todo list is empty, all three test tiers pass, Agent-D signs off.
2. **Tests before code, deterministic before simulated.** Tier 1 → Tier 2 → Tier 3. Never skip tiers.
3. **Sequential agents only.** Agent-A and Agent-B never modify code simultaneously.
4. **Judge cites spec.** Agent-C rulings must reference specific spec sections.
5. **Every failure is a task.** If a test fails, it becomes a tracked task with priority.
6. **Quality is not optional.** Agent-D runs after every test pass. Its findings become new tasks.
7. **Commit with proof.** Every commit message includes the number of passing tests and the current tier.
8. **User requirements are binding.** If the user said "do X," X must be done. If it can't be done, explain why and offer alternatives — don't silently drop it.
9. **Self-audit every 30 minutes.** If no progress in the last interval, analyze why and add corrective tasks.

## Sources

- 3-agent architecture: confidence high — demonstrated in mfangdai-agent development (commits: 5b7d929, 53c778b, f11301b)
- Arbitration heuristics: confidence high — spec-over-preference from VISION.md architecture decisions
- Self-managing todo: confidence high — P0/P1 test gaps auto-added during mfangdai-agent loop
- Three-tier test protocol: confidence high — derived from the Tier 1 (mock) → Tier 2 (sim LLM) → Tier 3 (quality judge) progression used in mfangdai-agent
- Anti-stall analysis: confidence high — based on observed failure modes where tasks stalled after "yolo aggressive" shortcut
- Quality judge (Agent-D): confidence medium — concept proven in this conversation but formal protocol is new
- Multi-model requirement: confidence medium — practical necessity discovered when deepseek-v4-flash JSON mode incompatibility surfaced
