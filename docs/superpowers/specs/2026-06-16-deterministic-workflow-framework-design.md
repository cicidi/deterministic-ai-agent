# Deterministic Workflow Framework — High-Level Design

> A general-purpose framework for building deterministic chatbot workflows targeting regulated industries
> (finance, health, insurance) where conversation behavior must be auditable, predictable, and compliant.

**Design Scope:** Architecture, schemas, and conceptual samples only. No implementation code.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-16 | 0.1.0 | Initial design — three-layer architecture, node-level switch matrix |
| 2026-06-16 | 0.1.1 | Replaced implementation code with declarative YAML sample and interface schemas |
| 2026-06-16 | 0.2.0 | Reorganized as original design; removed inline project references; structured as progressive decomposition from high-level to detailed |

---

## 1. Problem Domain and Motivation

Enterprise chatbots operating in regulated industries—insurance underwriting, payment collection, healthcare scheduling—face a fundamental tension:

- **Natural language is ambiguous.** Users express the same intent in countless ways.
- **Business rules are not.** Compliance requires exact verification, audit trails, and deterministic outcomes.

A purely LLM-driven chatbot can understand the user but cannot guarantee correctness. A purely rule-based chatbot can guarantee correctness but cannot understand the user. The gap between these two extremes is where enterprise chatbots live.

### 1.1 What We Mean by "Deterministic Workflow"

A deterministic workflow is a conversation path where, for any given state and validated input, the next action is unambiguously defined. This does not mean the entire system is rule-based. It means:

- **Understanding** may be probabilistic (LLM-powered) — extracting intent and entities from natural language.
- **Execution** must be deterministic — state transitions, validation rules, business calculations.
- **Fallback is mandatory** — when LLM understanding fails or is uncertain, the system degrades to explicit rules.

### 1.2 Design Goals

| Goal | Description |
|------|-------------|
| **Auditability** | Every state transition, extracted entity, and validation decision is traceable |
| **Predictability** | Same state + same input = same output, regardless of LLM provider or model version |
| **Composability** | Workflows can be composed from reusable steps; shared capabilities (e.g., question-answering) are defined once |
| **Graceful Degradation** | LLM unavailability must not break core flows; deterministic fallback for every LLM-dependent step |
| **Configurability** | Domain experts define workflows declaratively; developers override with code where needed |

---

## 2. Core Architecture

### 2.1 System Decomposition — Largest Blocks

At the highest level, the system is a pipeline of three sequential stages. Every user utterance flows through all three stages before a response is produced.

```
┌──────────────────────────────────────┐
│            User Utterance            │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│   Stage 1: UNDERSTAND                │
│   What does the user want?           │
│   → Intent + Entities                │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│   Stage 2: DECIDE                    │
│   What should we do about it?        │
│   → State transition + Side effects  │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│   Stage 3: RESPOND                   │
│   What do we say back?               │
│   → User-visible message             │
└──────────────────┬───────────────────┘
                   ▼
              Next turn
```

### 2.2 The LLM/Deterministic Boundary

Each stage, and each node within a stage, independently declares its stance toward LLM usage. This is not a binary "entire layer uses LLM or not" — it is a per-node property.

```
                   LLM Usage Spectrum
                   │
    Pure LLM       │  Hybrid            Pure Deterministic
    ───────────────┼──────────────────────────────────────
    Intent         │  Entity           Routing
    classification │  extraction       Field validation
    Response       │  (LLM → regex     Business formulas
    generation     │   fallback)       Template responses
                   │
```

A node that uses LLM must declare:
1. **Primary strategy** — the LLM call configuration (model, temperature, structured output schema)
2. **Fallback strategy** — the deterministic path taken when the LLM call fails or returns low confidence
3. **Merge strategy** — how LLM and fallback results are combined (LLM wins, fallback wins, union, intersection)

A node that does not use LLM must declare:
1. **Rule set** — the deterministic logic (conditions, formulas, templates)
2. **Input contract** — which fields from state it reads
3. **Output contract** — which fields to state it writes

---

## 3. Stage 1 — Understanding (NLU and Extraction)

### 3.1 Purpose

Convert an unstructured natural language utterance into a structured representation the system can act on:

```
User: "I want to insure my 2020 Honda Civic, comprehensive coverage, I'm 28"

        Stage 1: UNDERSTAND
              │
              ▼
        ┌─────────────────┐
        │ intent: get_quote  │
        │ confidence: 0.94   │
        │                    │
        │ entities:          │
        │  vehicleYear: 2020 │
        │  vehicleMake: Honda│
        │  vehicleModel: Civic│
        │  coverageLevel: cmp│
        │  driverAge: 28     │
        └─────────────────┘
```

### 3.2 Sub-Components

#### 3.2.1 Intent Classifier

Classifies the user's goal into a predefined intent label, with a confidence score.

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| LLM classification | Structured output with `{intent, confidence, reasoning}` | Free-form user input; requires semantic understanding |
| Keyword matching | Regex or keyword list against user input | Narrow domains with predictable phrasing |
| Fast-path detection | Pattern match on structured payloads (e.g., button clicks) | UI-driven interactions with known message format |

**Confidence threshold:** When an LLM-based classifier returns confidence below a configurable threshold, the system must treat the intent as "unknown" and trigger a clarification response rather than guessing.

**Sticky intent:** Once a transactional intent is confirmed and the user enters a multi-step workflow, intent re-classification is suppressed. The system stays in the current workflow until it terminates or the user explicitly exits. This prevents mid-flow utterances like "what does basic coverage mean?" from derailing the conversation into a different branch.

#### 3.2.2 Entity Extractor (Slot Filling)

Extracts structured field values from the user's utterance. Unlike intent classification—which produces a single label—entity extraction populates a dynamic set of slots that varies by workflow and current state.

**Schema Requirements:**

| Requirement | Rationale |
|-------------|-----------|
| Field definitions per workflow | Different workflows need different data (auto insurance needs vehicle details; payment needs card info) |
| Descriptions per field | Guides LLM extraction by explaining what each field means |
| Nullable fields | `null` means "not mentioned" (distinct from empty string or zero) |
| Type constraints | `string`, `number`, `enum`, `date` — framework uses these for both LLM prompt construction and deterministic validation |

**Dynamic Schema Principle:**

When a workflow has multiple product types with different field sets, entity extraction must not expose all possible field names to the LLM simultaneously. Doing so biases extraction toward the product type with the most field names in the schema.

Instead, extraction follows a two-phase approach:

```
Phase 1: Classify product type
  → Schema contains ONLY the type enum and reasoning fields
  → No product-specific field names appear
  → LLM cannot be biased by field density

Phase 2: Extract fields for the classified type
  → Schema is dynamically built to include ONLY that product's fields
  → Unrelated product fields never appear in the prompt
```

**Incremental Extraction:**

Once a workflow has collected some fields, subsequent extraction calls must:

1. Include only still-missing fields in the extraction schema
2. Pass already-collected fields as "DO NOT re-extract" context
3. Search the full conversation history (user + assistant messages), not just the latest utterance

#### 3.2.3 State-Aware Prompting

The extraction prompt must include the current workflow state. A digit string like "2027" means "expiry year" when collecting card details but "policy year" when collecting vehicle information. Without state context, the LLM has no way to disambiguate.

#### 3.2.4 Deterministic Fallback Pipeline

For every entity field, a deterministic extractor runs as a safety net:

| Field Type | Fallback Strategy |
|------------|-------------------|
| Account/ID numbers | Regex: `ACC\d+`, `\d{15,16}` (card numbers) |
| Dates | Multi-format parser: ISO (`YYYY-MM-DD`), ordinal DMY (`14th May 1990`), MDY (`May 14, 1990`), numeric DMY (`14/05/1990`) |
| Names | Case-sensitive substring match against known values |
| Numeric amounts | Regex: `\d+(\.\d+)?` |
| Enum values | Substring match against valid enum members |
| Spoken digits | Word-to-digit mapping: "one two three" → "123" |

The fallback pipeline runs regardless of LLM success. If the LLM returned a value, the fallback acts as validation. If the LLM failed or returned nothing, the fallback is the primary extractor.

---

## 4. Stage 2 — Deciding (Routing and Execution)

### 4.1 Purpose

Given the understanding from Stage 1, determine what happens next: which state to transition to, what validations to run, what business calculations to perform, and what side effects to trigger.

### 4.2 Sub-Components

#### 4.2.1 State Machine

The conversation state machine owns:

- **Current state** — which step in the workflow the user is at
- **Collected data** — all fields extracted so far (the "working memory" of the conversation)
- **Retry counters** — per-phase attempt tracking (reset on state transition)
- **Workflow metadata** — session ID, timestamps, debug context

**State Schema:**

```
DialogState {
  workflow_id:    string           // which workflow is active
  current_step:   string           // current node within the workflow
  mode:           "idle" | "conversational" | "transactional"
  collected_fields: {
    [field_name]: any              // extracted and validated data
  }
  validation_errors: string[]      // errors from last validation pass
  history:        Message[]        // full conversation transcript
  metadata: {
    retry_count:  number
    max_retries:  number
    started_at:   timestamp
  }
}
```

**Transition Rules:**

- Transitions are one-way within a workflow — no backtracking across steps that trigger side effects
- Terminal states (success, failure) are sticky — subsequent inputs return the terminal message without state changes
- Mode transitions: `idle → conversational` OR `idle → transactional`; once transactional, the mode is locked
- A state transition resets the retry counter for the new state

#### 4.2.2 Router

The router determines which node executes next based on the current state and the results of the previous node.

Routes are defined as ordered condition lists:

```
Route = [
  { condition: <predicate on state>,  target: <next_node> },
  { condition: <predicate on state>,  target: <next_node> },
  { default:                          target: <next_node> }
]
```

**Router types:**

| Router | How It Decides | When to Use |
|--------|---------------|-------------|
| Decision tree | Ordered `if/elif/else` predicates on state fields | Known, bounded transition logic |
| LLM router | LLM evaluates state and returns next node | Semantic routing (e.g., "does this sound like a complaint?") |
| Lookup router | Map intent label to node | Simple intent→node dispatch |

The framework must support nesting: a router can delegate to a sub-workflow, which returns control to the parent at a specified re-entry point.

#### 4.2.3 Field Validator

Validates collected field values against declared rules before they are accepted as final.

**Validation Rule Schema:**

```
ValidationRule {
  field:    string              // field name
  type:     "range" | "enum" | "regex" | "custom" | "luhn"
  params: {
    min?:   number
    max?:   number
    values?: string[]
    pattern?: string
  }
  message:  string              // human-readable error message
}
```

Validation is always deterministic — no LLM involved. If a field requires semantic validation (e.g., "does this address look real?"), that is a separate node with its own LLM/deterministic declaration.

#### 4.2.4 Business Computation

Pure deterministic calculations that produce derived data from collected fields. Examples: premium calculation from risk factors, payment amount from balance and user input, scheduling conflict resolution.

These nodes:
- Have zero LLM involvement
- Take collected fields as input
- Produce computed fields as output
- Are the most auditable part of the system — given the same inputs, they must always produce the same outputs

---

## 5. Stage 3 — Responding (Response Generation)

### 5.1 Purpose

Produce the user-visible message for the current turn. This stage decides both *what* to show and *how* to show it.

### 5.2 Sub-Components

#### 5.2.1 Response Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| LLM generation | Conversational model (e.g., temperature 0.4) generates natural language | Conversational Q&A, mid-flow guidance |
| Template interpolation | Hardcoded string with `{field}` placeholders | Critical compliance messages, error messages, confirmation text |
| Structured component | Deterministic frontmatter block + optional markdown body | Quote cards, payment confirmations, calendar pickers — anything rendered as a custom UI component |

A single response may combine strategies: a structured component (frontmatter) carries machine-readable data for the frontend, while an LLM-generated body provides the human-readable text.

#### 5.2.2 Structured Component Protocol

When the response must include structured data for client-side rendering (e.g., a quote card with interactive elements), the message uses a frontmatter protocol:

```
message format:
  ---
  component: <component_type>
  <key>: <value>
  ...
  ---
  <optional markdown body>
```

The frontend parses this and renders the designated component instead of plain text. The backend never needs to know what the frontend will render — it only declares the component name and its data.

**Component examples:**

| Component | Data Fields | Purpose |
|-----------|------------|---------|
| `quote_card` | insurance_type, annual_premium, monthly_premium, breakdown, collected_fields | Interactive quote summary |
| `payment_confirmation` | transaction_id, amount, account_id | Payment success confirmation |
| `scheduler` | available_slots, selected_date | Appointment time slot picker |
| `error_panel` | errors[], retries_remaining | Structured error display |

#### 5.2.3 Context Injection

When an LLM-generated response needs grounding (e.g., answering a product question while in a transactional flow), the response node must be able to fetch and inject context. This context comes from:

- **Knowledge base (RAG):** Similarity search against product documentation
- **Current state:** Collected fields, current step, validation errors
- **Workflow definition:** What the user still needs to provide

---

## 6. Cross-Cutting Concerns

### 6.1 Sensitive Field Handling

Some fields contain data that must never persist beyond their moment of use: credit card numbers, CVV codes, personal identification numbers, health data.

**Framework responsibility:**

1. **Marking:** Fields declared as `sensitive` in the workflow definition
2. **Automatic scrubbing:** On node exit, sensitive fields are set to null
3. **Response filtering:** Sensitive field values must never appear in response messages (LLM-generated or template)
4. **Log exclusion:** Debug/log output must exclude sensitive field values; only field names and null status are logged

### 6.2 Retry Budgets

Each state in the state machine carries an independent retry budget. When a user provides invalid input (wrong name, wrong verification code), the retry counter increments. On the Nth failure, the system transitions to a terminal failure state.

```
State: AWAITING_NAME, retry_count=0, max=3
  → invalid name → retry_count=1 → "Try again"
  → invalid name → retry_count=2 → "Try again"
  → invalid name → retry_count=3 → TERMINATED_FAILURE

On successful transition to AWAITING_SECONDARY: retry_count resets to 0
```

Retry budgets are per-state, not global. A user who struggles with name entry should not have fewer attempts for secondary verification.

### 6.3 Sub-Workflow Reuse

A sub-workflow is a self-contained workflow that can be invoked from any point in a parent workflow, executes to completion, and returns control to the parent at a designated re-entry point.

```
Parent: Insurance Quote workflow
  │
  ├─ collect_details (user asks "what does comprehensive cover?")
  │      │
  │      ▼
  │  Sub: QuestionAnswering workflow
  │      ├─ rag_lookup
  │      ├─ respond
  │      └─ return to parent.collect_details
  │
  └─ continue quote flow...
```

The same QuestionAnswering sub-workflow can also be the entry point from the conversational (non-transactional) path. This eliminates the common anti-pattern of duplicating question-answering logic in multiple branches.

### 6.4 State Persistence and Checkpointing

Conversation state must survive across turns, across process restarts, and potentially across deployment boundaries.

- **Session identity:** Each conversation has a unique `thread_id`
- **Checkpoint strategy:** After each node execution, state is written to a configurable backend (in-memory, Redis, Postgres)
- **Recovery:** On any turn, the framework reads the last checkpoint for the `thread_id` and resumes from that state
- **TTL:** Sessions have configurable time-to-live; expired sessions return a "session expired, please start over" message

---

## 7. Declarative Workflow Definition

### 7.1 Step Schema

Every step in a workflow is defined by a common structure:

```
Step {
  name:              string                  // unique within workflow
  type:              "intent" | "slot" | "validate" | "compute" | "respond" | "sub_workflow"
  description:       string                  // human-readable purpose

  // LLM configuration (absent = deterministic)
  llm?: {
    strategy:        "primary" | "hybrid" | "none"
    model?:          string                  // model identifier
    temperature?:    number                  // 0.0 - 1.0
    structured_output?: Schema               // for extraction/classification
    prompt_template?: string                 // optional override
  }

  // Deterministic configuration
  deterministic?: {
    rules?:          ValidationRule[]        // for validate steps
    formula?:        string                  // for compute steps
    template?:       string                  // for respond steps (template response)
    routes?:         RouteRule[]             // for routing
  }

  // Fallback (when llm.strategy = "hybrid")
  fallback?: {
    strategy:        "regex" | "keyword" | "substring" | "none"
    rules?:          FallbackRule[]
  }

  // Data contract
  fields?:           FieldSpec[]             // fields to extract / validate
  sensitive_fields?: string[]                // auto-wipe on step exit

  // Flow control
  retry?: {
    max:             number
    reset_on_transition: boolean
  }

  // Sub-workflow linkage
  sub_workflow?:     string                  // workflow name to delegate to
  return_to?:        string                  // step to return to after sub-workflow
}
```

### 7.2 Field Specification

```
FieldSpec {
  name:              string
  description:       string                  // guides LLM extraction
  type:              "string" | "number" | "boolean" | "date" | "enum"
  enum_values?:      string[]                // valid values for enum type
  required:          boolean
  sensitive:         boolean                 // auto-wipe after use
  group?:            string                  // logical grouping for UI/validation
}
```

### 7.3 Route Rule

```
RouteRule {
  condition:         string                  // expression evaluated against state
  target:            string                  // next step name or sub-workflow name
  description?:      string                  // human-readable explanation
}
```

---

## 8. Sample: Insurance Quote Workflow

The following is a complete declarative definition of an insurance quote workflow, demonstrating how the schema above is used in practice.

```yaml
# Sample: Insurance quote workflow (declarative)
# This demonstrates the schema, not a reference to any specific implementation.

workflow:
  id: insurance_quote
  version: "1.0"
  description: Collects insurance quote details and generates a premium estimate.

  steps:

    # ── Intent Detection ──────────────────────────────────────────
    - name: detect_intent
      type: intent
      description: Classifies user's goal from their utterance.
      llm:
        strategy: primary
        temperature: 0.0
        structured_output:
          intent: { enum: [ask_question, get_quote, unknown] }
          confidence: number
      fallback:
        strategy: keyword
        rules:
          - patterns: ["quote", "price", "cost", "how much"]
            intent: get_quote
          - patterns: ["what is", "how does", "explain", "coverage"]
            intent: ask_question
      routes:
        - condition: intent == "ask_question"
          target: answer_question
        - condition: intent == "get_quote"
          target: classify_product
        - condition: intent == "unknown"
          response: "I can help with insurance questions or getting a quote. What would you like to do?"

    # ── Product Type Classification (two-phase slot filling) ─────
    - name: classify_product
      type: slot
      description: Identifies which insurance product the user wants (Phase 1).
      llm:
        strategy: primary
        temperature: 0.0
        # Phase 1: minimal schema — only type classification, no product fields
        structured_output:
          product_type: { enum: [auto, home, life, unknown] }
          reasoning: string
      routes:
        - condition: product_type == "unknown"
          response: "Which type of insurance are you interested in — auto, home, or life?"
        - condition: product_type in ["auto", "home", "life"]
          target: extract_fields

    # ── Field Extraction (Phase 2 of slot filling) ──────────────
    - name: extract_fields
      type: slot
      description: Extracts product-specific fields using a dynamic schema built from the classified type.
      llm:
        strategy: primary
        temperature: 0.0
        dynamic_schema: true          # Schema built at runtime from fields_by_type[product_type]
        state_aware_prompt: true      # Prompt includes current state and product_type
      fields_by_type:
        auto:
          - { name: vehicleYear,    type: number, description: "Year vehicle was manufactured" }
          - { name: vehicleMake,    type: string, description: "Manufacturer (e.g. Honda)" }
          - { name: vehicleModel,   type: string, description: "Model name (e.g. Civic)" }
          - { name: driverAge,      type: number, description: "Age of primary driver" }
          - { name: drivingHistory, type: string, description: "clean, minor incidents, or major" }
          - { name: coverageLevel,  type: enum, enum_values: [basic, standard, comprehensive] }
        home:
          - { name: propertyType,   type: string, description: "house, condo, townhouse, etc." }
          - { name: location,       type: string, description: "City and state" }
          - { name: estimatedValue, type: number, description: "Estimated property value" }
          - { name: coverageLevel,  type: enum, enum_values: [basic, standard, comprehensive] }
        life:
          - { name: applicantAge,   type: number, description: "Age of applicant" }
          - { name: healthStatus,   type: string, description: "excellent, good, fair, poor" }
          - { name: coverageAmount, type: number, description: "Desired coverage amount" }
          - { name: termLength,     type: number, description: "Term length in years" }
      fallback:
        strategy: regex
      routes:
        - condition: all_fields_collected
          target: validate_input
        - condition: missing_fields
          target: extract_fields       # loop — next turn re-extracts

    # ── Validation ──────────────────────────────────────────────
    - name: validate_input
      type: validate
      description: Validates collected fields against business rules.
      llm:
        strategy: none
      rules_by_type:
        auto:
          - { field: vehicleYear,   type: range, min: 1980, max: "$currentYear" }
          - { field: driverAge,     type: range, min: 18, max: 99 }
          - { field: coverageLevel, type: enum, values: [basic, standard, comprehensive] }
        home:
          - { field: estimatedValue, type: range, min: 1 }
          - { field: coverageLevel,  type: enum, values: [basic, standard, comprehensive] }
        life:
          - { field: applicantAge,   type: range, min: 18, max: 99 }
          - { field: coverageAmount, type: range, min: 1 }
          - { field: termLength,     type: range, min: 5, max: 40 }
      routes:
        - condition: has_errors
          target: extract_fields       # re-collect with error feedback
        - condition: valid
          target: calculate_premium

    # ── Business Computation ────────────────────────────────────
    - name: calculate_premium
      type: compute
      description: Computes insurance premium from collected fields.
      llm:
        strategy: none
      formula:
        auto: "800 * (currentYear - vehicleYear + 1) * coverageMultiplier"
        home: "estimatedValue * 0.005 * coverageMultiplier"
        life: "(coverageAmount / 1000) * (applicantAge * 0.8) * termMultiplier * coverageMultiplier"
      constants:
        coverageMultiplier: { basic: 0.8, standard: 1.0, comprehensive: 1.3 }
        termMultiplier: { "5-10": 0.7, "11-20": 1.0, "21-30": 1.4, "31-40": 1.8 }
      routes:
        - default:
            target: present_quote

    # ── Response (structured component) ─────────────────────────
    - name: present_quote
      type: respond
      description: Presents the computed premium as a structured component.
      llm:
        strategy: none
      response:
        component: quote_card
        template: |
          ---
          component: quote_card
          product_type: "{$product_type}"
          coverage_level: "{$coverageLevel}"
          annual_premium: "{$annualPremium}"
          monthly_premium: "{$monthlyPremium}"
          fields: "{$collectedFields}"
          ---
          Here is your personalized quote based on the details you provided.

    # ── Sub-Workflow: Question Answering (reusable) ─────────────
    - name: answer_question
      type: sub_workflow
      description: Answers product questions using knowledge base retrieval.
      llm:
        strategy: primary
        temperature: 0.3
      knowledge_base:
        source: knowledge-base/
        retrieval:
          top_k: 3
          similarity_threshold: 0.8
        prompt: "Answer the user's question using ONLY the provided knowledge base context."
      return_to: "$parent_step"      # Returns to the step that invoked it
```

---

## 9. What This Framework Provides vs. What Users Build

| Layer | Framework Provides | User Defines |
|-------|-------------------|-------------|
| **Understanding** | Intent classifier interface, entity extractor with dynamic schema, fallback pipeline runtime, state-aware prompt injection | Intent labels, field definitions, fallback regex rules, classification prompts |
| **Deciding** | State machine engine, router evaluator, validation rule executor, computation engine, retry budget tracker, checkpoint manager | State names and transitions, validation rules, business formulas, route conditions |
| **Responding** | Response builder (LLM template → structured component → plain template), context injector, sensitive field filter | Response templates, component schemas, knowledge base documents, LLM prompts |

---

## 10. References

1. **LangGraph** — Low-level state graph execution framework providing StateGraph, conditional edges, checkpointing, and streaming primitives. Serves as the runtime substrate for this framework. *github.com/langchain-ai/langgraph*

2. **Rasa CALM (Conversational AI with Language Models)** — Architecture philosophy: "The LLM understands the user; the code enforces the rules." Independent inspiration for the LLM/deterministic boundary concept. *rasa.com*

3. **zelkim/langgraph-insurance-chatbot** — TypeScript implementation of an insurance quote chatbot using LangGraph.js. Demonstrates intent detection, two-phase slot filling, deterministic premium calculation, and frontmatter component protocol. *github.com/zelkim/langgraph-insurance-chatbot*

4. **Prodigal Payment Collection AI Agent** — Python implementation of a payment collection agent using a custom FSM. Demonstrates state-aware NLU prompting, multi-layer deterministic fallback, sensitive field scrubbing, per-phase retry budgets, and PII leak detection. *github.com/AvnishChitrigi/Prodigal-Assignment-Production-Ready-Payment-Collection-AI-Agent*

5. **VicentePareja/chatbot-FSM-experiment** — FSM-based healthcare scheduling chatbot using FastAPI + Next.js + PostgreSQL. *github.com/VicentePareja/chatbot-FSM-experiment*

---

## 11. Referenced Documents

| Document | Relationship |
|----------|-------------|
| `docs/superpowers/specs/2026-06-16-extraction-layer-design.md` | Child: detailed spec for Stage 1 |
| `docs/superpowers/specs/2026-06-16-routing-execution-layer-design.md` | Child: detailed spec for Stage 2 |
| `docs/superpowers/specs/2026-06-16-response-generation-layer-design.md` | Child: detailed spec for Stage 3 |
| `docs/superpowers/specs/2026-06-16-framework-api-design.md` | Child: interface schemas and API contract |
