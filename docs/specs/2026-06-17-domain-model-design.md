# Domain Model Specification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Domain model as the single source of truth for entities, states, and transitions.
> **This spec defines schemas and interfaces — not a single solution.**

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial domain model spec: Entity + State + Transition schema |
| 2026-06-17 | 0.2.0 | Add implementation options (flat vs nested vs code-first); agentState.phase mapping; errorNode as standard transition target |
| 2026-06-17 | 0.3.0 | Add Section 1.1: Implementation Approaches (Flat YAML vs Nested/Hierarchical vs Code-First) |

---

## 1. Role

The Domain Model is the **single source of truth** for a deterministic workflow. It defines *what* the workflow operates on — data entities, valid states, and transition rules — independent of *how* the framework executes extraction, validation, or routing.

```
Domain Model (WHAT)               Workflow Config (HOW)
────────────────────────          ──────────────────────
Entities + fields + types         extraction_strategy
States + state_hint                validate_strategy
Transitions + guards              transform_strategy
                                   context_window_size
                                   max_transform_attempts
                                   on_transform_failure
```

**Separation principle:** The Domain Model is reusable across workflows and products. The workflow configuration adds runtime strategy selection on top. This separation enables:

1. **Cross-workflow reuse** — a `property_info` entity used in both `home_insurance_quote` and `home_insurance_refinance`
2. **Product-agnostic models** — same domain model across different implementations
3. **Skill-driven generation** — a downstream skill can interview a developer to fill in the domain model, then the framework provides sensible defaults for the how

### 1.1 Implementation Approaches

Three architectural options for authoring domain models. All three share the same entity/state/transition schema; they differ in *how* the definition is structured and maintained.

#### Option A: Flat YAML Domain Model (Current Approach)

Entities are defined as flat field lists. Every field is a top-level key under the entity. No nesting or compound field support.

```yaml
entities:
  property_info:
    fields:
      property_type: { type: enum, values: [apartment, house, villa] }
      address:       { type: string, required: true }
      postal_code:   { type: string, pattern: "^[0-9]{6}$" }
      building_age:  { type: int, range: { min: 0, max: 200 } }
```

**Pros:** Simple to read and write. Tooling is straightforward — every field is a single key. LLM extraction prompts map 1:1 to field descriptions.

**Cons:** No way to represent compound data (e.g., `address` as `{street, city, province, postal_code}`). Entity schemas grow flat and can become unwieldy for large entities.

#### Option B: Nested/Hierarchical Domain Model

Entities support compound fields. A field can contain sub-fields, enabling structured nested data.

```yaml
entities:
  property_info:
    fields:
      property_type: { type: enum, values: [apartment, house, villa] }
      address:
        type: object
        required: true
        fields:
          street:      { type: string, required: true }
          city:        { type: string, required: true }
          province:    { type: string, required: true }
          postal_code: { type: string, pattern: "^[0-9]{6}$" }
      building_age: { type: int, range: { min: 0, max: 200 } }
```

**Pros:** Natural modeling of structured data (addresses, personal info with first_name/last_name, policy details with nested coverage). LLM extraction can target sub-fields independently. Validation rules apply per sub-field.

**Cons:** More complex YAML structure. Tooling must handle recursive field expansion. Guard expressions become more verbose (`address.city` vs flat `city`).

#### Option C: Code-First Model Generation

Entities are defined as Python dataclasses or Pydantic models. The YAML domain model is auto-generated from the code definitions.

```python
from pydantic import BaseModel, Field

class PropertyInfo(BaseModel):
    property_type: Literal["apartment", "house", "villa"]
    address: str = Field(min_length=5)
    postal_code: str = Field(pattern=r"^\d{6}$")
    building_age: int = Field(ge=0, le=200)
```

```yaml
# Auto-generated domain model YAML
entities:
  property_info:
    fields:
      property_type: { type: enum, values: [apartment, house, villa], required: true }
      address:       { type: string, required: true, min_length: 5 }
      postal_code:   { type: string, required: true, pattern: "^\\d{6}$" }
      building_age:  { type: int, required: true, range: { min: 0, max: 200 } }
```

**Pros:** Full IDE support (autocomplete, type-checking, refactoring). Validation logic is native Python. Pydantic's built-in serialization produces structured outputs suitable for LangGraph state.

**Cons:** Requires a code-generation step. Non-Python developers cannot author or review the domain model. Generated YAML may be less readable than hand-crafted YAML.

### Comparison Matrix

| Dimension | Option A: Flat YAML | Option B: Nested YAML | Option C: Code-First |
|-----------|-------------------|----------------------|----------------------|
| **Complexity** | Low — flat key-value | Medium — recursive field structure | Medium-High — requires Python + codegen |
| **Readability** | High — simple, flat structure | Medium — nesting adds depth but clarity for compound data | Low — source of truth is Python, not YAML |
| **Tooling Support** | High — simple YAML parsing | Medium — recursive processing needed | High — Pydantic ecosystem, IDE support |
| **Dynamic Schema Support** | Low — flat only | High — nested fields match real-world data | Medium — Pydantic supports nested models |
| **IDE Support** | Low — raw YAML | Low — raw YAML | High — full Python type-checking, autocomplete |

**Default recommendation: Option A (Flat YAML) for most use cases. Use Option B (Nested YAML) when entities contain compound fields like addresses or personal info with sub-fields. Option C (Code-First) is available for teams that prefer Python-native development and do not need non-developer stakeholder review of domain models.**

## 2. Domain Model Schema

A Domain Model is defined in an independent YAML file:

```
DomainModel {
  domain:      string              // unique identifier (e.g., "home_insurance")
  version:     string              // semantic version
  description: string              // human-readable description of the domain
  entities:    Map<string, EntityDef>  // data entities in this domain
  states:      Map<string, StateDef>   // workflow states
  transitions: TransitionDef[]         // allowed state transitions
}
```

### 2.1 File Location

```
docs/domain-models/
  home-insurance.yaml
  banking-kYC.yaml
  healthcare-intake.yaml
```

### 2.2 Registration

Domain models are registered globally. Workflows reference them by `domain` name:

```yaml
# workflow.yaml
workflow: home_insurance_quote
domain_model: home-insurance          # references docs/domain-models/home-insurance.yaml
```

---

## 3. Entity Definition

### 3.1 EntityDef Schema

```
EntityDef {
  name:        string              // entity name (e.g., "property_info")
  description: string              // guides LLM extraction + documentation
  fields:      Map<string, FieldDef> // ordered field definitions
}
```

### 3.2 FieldDef Schema

```
FieldDef {
  type:        string              // "string" | "int" | "float" | "date" | "boolean" | "enum" | "list"
  required:    boolean             // true → null triggers validation error
  description: string              // guides LLM extraction
  values?:     string[]            // valid values (for type: enum)
  range?:      { min?: number, max?: number }  // (for type: int, float)
  pattern?:    string              // regex pattern (for type: string)
  min_length?: int                 // minimum string length
  deterministic_fallback?: {       // deterministic extraction fallback
    keywords?: string[]
    regex?:    string
    priority?: "llm_wins" | "regex_wins"
  }
  transform?:  TransformOp[]       // type coercion / normalization pipeline
  examples?:   string[]            // few-shot examples for LLM prompt
}

TransformOp {
  type:   "cast" | "normalize" | "parse" | "lookup" | "default" | "external"
  config: Record<string, any>      // type-specific configuration
}
```

### 3.3 Type System

| Type | Validation | Transform (default) |
|------|-----------|---------------------|
| `string` | non-empty if required | `trim` |
| `int` | integer, optional range | `cast: int` |
| `float` | numeric, optional range | `cast: float` |
| `date` | ISO 8601 format | `parse: date` |
| `boolean` | true/false/yes/no/1/0 | `cast: boolean` |
| `enum` | must be in `values[]` | `normalize: lowercase` + `lookup` |
| `list` | array of items | `split: ","` |

### 3.4 Example: home-insurance domain

```yaml
domain: home_insurance
version: 1.0.0
description: "Home insurance quote, claim, and policy management"

entities:
  property_info:
    description: "Property information for home insurance"
    fields:
      property_type:
        type: enum
        values: [apartment, house, villa]
        required: true
        description: "Type of property being insured"
        examples: ["I live in a house", "3-bedroom apartment", "my villa"]
        deterministic_fallback:
          keywords: [apartment, house, villa, condo, flat]
        transform:
          - type: normalize
            config: { op: lowercase }
          - type: lookup
            config:
              mapping:
                condo: apartment
                flat: apartment
                "single family": house

      address:
        type: string
        required: true
        description: "Full address including street, city, province, postal code"
        min_length: 5

      postal_code:
        type: string
        required: true
        description: "6-digit postal code"
        pattern: "^[0-9]{6}$"
        deterministic_fallback:
          regex: "\\b[0-9]{6}\\b"
          priority: regex_wins

      building_age:
        type: int
        required: true
        description: "Age of the building in years"
        range: { min: 0, max: 200 }
        examples: ["built in 2010", "15 years old", "brand new"]
        transform:
          - type: cast
            config: { to: int }

      floor_area:
        type: float
        required: false
        description: "Floor area in square meters"
        range: { min: 1, max: 100000 }
        transform:
          - type: cast
            config: { to: float }

      construction_material:
        type: enum
        values: [brick, concrete, wood_frame, steel]
        required: false
        description: "Primary construction material"

  coverage_needs:
    description: "Coverage requirements for a quote"
    fields:
      coverage_type:
        type: enum
        values: [building_only, contents_only, both]
        required: true
        description: "What type of coverage the user wants"

      building_coverage:
        type: float
        required: true
        description: "Coverage amount for building (CNY)"
        range: { min: 0 }

      contents_coverage:
        type: float
        required: false
        description: "Coverage amount for contents (CNY)"
        range: { min: 0 }

      deductible:
        type: enum
        values: [low, standard, high]
        required: true
        description: "Deductible preference"

      riders:
        type: list
        required: false
        description: "Additional rider coverage (fire, theft, water_damage, earthquake, liability)"

  claim_details:
    description: "Claim filing information"
    fields:
      incident_type:
        type: enum
        values: [fire, water_damage, theft, natural_disaster, other]
        required: true
        description: "Type of incident being claimed"

      incident_date:
        type: date
        required: true
        description: "Date the incident occurred"

      damage_description:
        type: string
        required: true
        description: "Description of the damage"

      estimated_loss:
        type: float
        required: true
        description: "Estimated loss amount (CNY)"
        range: { min: 0 }
```

---

## 4. State Definition

### 4.1 StateDef Schema

```
StateDef {
  name:         string    // state name (e.g., "collect_property_info")
  description:  string    // human-readable description of what this state expects
  entity:       string    // which entity this state extracts (references EntityDef.name)
  state_hint:   string    // disambiguation hint injected into LLM extraction prompt
  max_retries?: int       // max retries before escalating (default: from framework config)
}
```

### 4.2 State → Entity Binding

Each state binds to exactly one entity. The framework uses this binding to:

1. Generate `ExtractionRule[]` from the entity's `FieldDef[]`
2. Generate `ValidationRule[]` from field types, required flags, patterns, and ranges
3. Generate `TransformRule[]` from field `transform` declarations
4. Inject `state_hint` into the LLM prompt when extracting data in this state

### 4.3 Example

```yaml
states:
  collect_property_info:
    description: "Collect property details from the user"
    entity: property_info
    state_hint: >
      The user is providing property information for a home insurance quote.
      Address may include street, city, province, postal code.
      Building age is in years. "Brand new" or "newly built" means age 0.

  collect_coverage_needs:
    description: "Collect coverage preferences"
    entity: coverage_needs
    state_hint: >
      The user is choosing coverage type and amount.
      Deductible options: low (500 CNY), standard (2000 CNY), high (5000 CNY).

  file_claim:
    description: "File a new claim"
    entity: claim_details
    state_hint: >
      The user is reporting an incident for a claim.
      Incident type must be one of: fire, water_damage, theft, natural_disaster, other.
      Date should be in YYYY-MM-DD format.
```

### 4.4 State Name → agentState.phase Mapping

At runtime, the framework maps each `StateDef.name` to the `agentState.phase` field on the shared state object. This mapping is direct and automatic:

```
# Domain model state definition
states:
  collect_property_info:
    ...

# Runtime behavior
agentState.phase = "collect_property_info"
```

The `agentState.phase` value is used by:
- **LangGraph conditional edges** — route to the correct node based on current phase
- **Sub-workflow dispatch** — match the current phase to a sub-workflow handler
- **Audit/logging** — record which phase the conversation is in at each step
- **Resumption** — when resuming a conversation, the stored phase determines which state to re-enter

No explicit mapping configuration is needed. The framework derives the phase value from `StateDef.name` during domain model loading (step 3 of the framework consumption flow).

---

## 5. Transition Definition

### 5.1 TransitionDef Schema

```
TransitionDef {
  from:      string    // source state name
  to:        string    // target state name
  guard:     string    // guard expression (see Section 6)
  priority?: int       // higher = checked first (for conflict resolution)
  label?:    string    // optional label for documentation / conditional edge naming
}
```

### 5.2 Transition Semantics

- **Self-loop**: `from: collect_property_info, to: collect_property_info, guard: "context_incomplete"` — stay in current state until all required fields are filled
- **Advance**: `from: collect_property_info, to: assess_risk, guard: "property_type != null AND address != null AND building_age != null"` — move forward when entity fields are complete
- **Conditional branch**: multiple transitions from the same state with non-overlapping guards decide the next state

### 5.3 Conflict Resolution

When multiple transitions from the same state have guards that could both be true:

1. **Priority ordering** — higher `priority` value is checked first
2. **First-match wins** — the first guard that evaluates true determines the transition
3. **Unreachable fallback** — if all guards fail, the framework uses the `on_nomatch` transition (explicitly defined or `on_transform_failure` node)

### 5.4 Example

```yaml
transitions:
  # Quote flow
  - from: collect_property_info
    to: collect_coverage_needs
    guard: "property_type != null AND address != null AND building_age != null"
    label: "property_info_complete"
    priority: 10

  - from: collect_property_info
    to: collect_property_info
    guard: "context_incomplete"
    label: "still_collecting"
    priority: 5

  - from: collect_coverage_needs
    to: assess_risk
    guard: "coverage_type != null AND building_coverage != null"
    label: "coverage_needs_complete"

  - from: collect_coverage_needs
    to: collect_coverage_needs
    guard: "context_incomplete"

  # Claim flow
  - from: file_claim
    to: validate_claim
    guard: "incident_type != null AND incident_date != null AND estimated_loss != null"

  - from: file_claim
    to: file_claim
    guard: "context_incomplete"
```

### 5.5 Reserved Transition Target: `errorNode`

The transition target name `errorNode` is reserved for error handling. Behavior:

- **Always reachable**: Any state can transition to `errorNode` regardless of its explicit transition allowlist. No transition rule with `to: errorNode` needs to be declared in the domain model.
- **Automatic routing**: When extraction, validation, or transformation fails and retries are exhausted, the framework automatically routes the conversation to the `errorNode`.
- **Escalation path**: The `errorNode` serves as a catch-all escalation path. It can be configured per-workflow (e.g., hand off to a human agent, log the failure, terminate gracefully).
- **Do not declare**: Do not declare `errorNode` as a state in the domain model. It is a framework-level primitive, not a domain state.

```yaml
# NO need to declare this in transitions:
# transitions:
#   - from: collect_property_info
#     to: errorNode       # ← NOT needed; errorNode is always reachable
```

The `errorNode` is resolved by the framework (step 6 of the consumption flow) and injected into the LangGraph state machine alongside the domain-defined states.

---

## 6. Guard Expression Syntax

Guards are boolean expressions evaluated against the current entity state. The framework provides a minimal expression language for guards.

### 6.1 Syntax

```
Expr     = Comparison (BoolOp Comparison)*
BoolOp   = "AND" | "OR"
Comparison = Operand RelOp Literal | "context_incomplete" | "context_complete"
RelOp    = "==" | "!=" | ">" | "<" | ">=" | "<="
Operand  = field_name                      // references entity field
Literal  = null | number | string | boolean
```

### 6.2 Built-in Meta-Variables

| Variable | Evaluates to |
|----------|-------------|
| `context_incomplete` | `true` if any required field is null/empty |
| `context_complete` | `true` if all required fields are non-null and non-empty |

### 6.3 Examples

```
# Simple required check
"address != null"

# Multiple required fields
"property_type != null AND address != null AND building_age != null"

# Composite
"incident_type != null AND estimated_loss > 0"

# Meta-variable
"context_incomplete"

# Enum check
"coverage_type == 'building_only' OR coverage_type == 'both'"
```

### 6.4 Extensibility

The guard expression syntax is intentionally minimal. For complex business rules (e.g., "risk_score < 80 AND coverage_amount > 500000"), the framework delegates to:
- **Custom guard functions** — registered Python callable referenced by function name
- **Rule engine guards** — when `validate_strategy` uses a rule engine, guards can be compiled into the engine's native format

---

## 7. Relationship with Workflow YAML

### 7.1 Merge Strategy

At framework startup, the domain model and workflow config are merged:

```
Domain Model (entity/state/transition schemas)
         +
Workflow Config (strategy choices, runtime params)
         ↓
Framework resolves to concrete ExtractionNode / ValidateNode / TransformNode instances
```

### 7.2 What the Workflow Config Adds

| Configured By | Domain Model | Workflow Config |
|---------------|-------------|-----------------|
| Entity field schemas | ✅ | — |
| State definitions | ✅ | — |
| Transition guards | ✅ | — |
| State hints | ✅ | — |
| Extraction strategy | — | ✅ |
| Validation strategy | — | ✅ |
| Transform strategy | — | ✅ |
| Rule engine selection | — | ✅ |
| Context window size | — | ✅ |
| Max transform attempts | — | ✅ |
| On-failure routing | — | ✅ |

### 7.3 Example: Referencing a Domain Model

```yaml
# workflow_home_insurance_quote.yaml
workflow: home_insurance_quote
domain_model: home-insurance        # loads docs/domain-models/home-insurance.yaml

nodes:
  collect_property_info_extract:
    entity: property_info
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    context_window_size: 6
    max_transform_attempts: 2
    on_transform_failure: ask_missing_property_info

  collect_coverage_needs_extract:
    entity: coverage_needs
    extract_strategy: hybrid
    validate_strategy: durable_rules
    transform_strategy: hybrid
    on_transform_failure: ask_missing_coverage
```

---

## 8. Cross-Workflow Reuse

A domain model is globally registered. Multiple workflows can reference it, with different strategy configurations.

```
domain-models/home-insurance.yaml
    ├── workflow_home_insurance_quote.yaml     (extract_strategy: hybrid)
    ├── workflow_home_insurance_refinance.yaml  (extract_strategy: llm_primary)
    └── workflow_home_insurance_renewal.yaml    (extract_strategy: deterministic)
```

### 8.1 Versioning

Domain models use semantic versioning. Workflows pin to a version:

```yaml
domain_model: home-insurance@1.2.0
```

Breaking changes to entity schemas (field removal, type change) require a major version bump.

### 8.2 Namespacing

When two domain models define entities with the same name, the framework disambiguates by domain prefix:

```yaml
entity: home_insurance.property_info
```

---

## 9. Framework Consumption Flow

When the framework loads a workflow that references a domain model:

```
1. Load domain model YAML → parse entities, states, transitions
2. Load workflow YAML → parse nodes, strategy configs
3. For each state → look up bound entity → expand FieldDef[] to:
   a. ExtractionRule[]  (from field name, type, description, deterministic_fallback, examples)
   b. ValidationRule[]  (from field required, type, pattern, range, min_length)
   c. TransformRule[]   (from field transform)
4. Merge with node-level overrides (context_window_size, max_transform_attempts, etc.)
5. Instantiate Extract / Validate / Transform nodes via ExtractionFactory(strategy)
6. Generate LangGraph nodes + conditional edges from transition definitions
```

### 9.1 Entity → Rules Expansion

The framework performs automatic expansion. For example, given the `property_type` field:

```yaml
# Domain model entity field
property_type:
  type: enum
  values: [apartment, house, villa]
  required: true
  description: "Type of property"
  deterministic_fallback:
    keywords: [apartment, house, villa, condo, flat]
  transform:
    - type: normalize
      config: { op: lowercase }
    - type: lookup
      config: { mapping: { condo: apartment, flat: apartment, "single family": house } }
```

The framework auto-generates:

```
ExtractionRule {
  field: "property_type"
  description: "Type of property (apartment, house, villa)"
  type: "enum"
  required: true
  fallback_keywords: ["apartment", "house", "villa", "condo", "flat"]
}

ValidationRule {
  field: "property_type"
  required: true
  enum: ["apartment", "house", "villa"]
}

TransformRule {
  field: "property_type"
  rules: [
    { type: "normalize", config: { op: "lowercase" } },
    { type: "lookup", config: { mapping: { condo: "apartment", flat: "apartment", "single family": "house" } } }
  ]
}
```

---

## 10. Edge Cases

### 10.1 Optional vs. Required Fields

Fields marked `required: false` are extracted and validated if present, but `context_complete` evaluates true even if they are null. Optional fields do not block state transition.

### 10.2 Cross-Entity Data

When a state collects `coverage_needs` but the transition guard references a field from `property_info` (collected in a previous state), the framework evaluates the guard against the accumulated `collectedFields` across all entities. This enables guards like `"building_age > 10 AND building_coverage > 500000"`.

### 10.3 Dynamic Entity Selection

For scenarios where the entity schema depends on a prior decision (e.g., auto vs home insurance), use two-stage domain models:

```yaml
# Stage 1 entity
insurance_type:
  fields:
    product_type:
      type: enum
      values: [auto, home, life]
      required: true

# Stage 2 — dynamic entity binding
states:
  classify_product:
    entity: insurance_type  # Stage 1

  collect_auto_details:
    entity: auto_info        # Selected only if product_type == "auto"

  collect_home_details:
    entity: property_info    # Selected only if product_type == "home"
```

The transition guard on the classify state determines which entity is used next:

```yaml
transitions:
  - from: classify_product
    to: collect_home_details
    guard: "product_type == 'home'"
  - from: classify_product
    to: collect_auto_details
    guard: "product_type == 'auto'"
```

---

## 11. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should entities support nested/compound fields (e.g., `address: { street, city, postal_code }`)? | Schema complexity |
| 2 | Should domain models support inheritance (e.g., `auto_info extends base_insurance_info`)? | Reuse granularity |
| 3 | For guard expressions — how much expressiveness before we defer to rule engines? | Language complexity vs. power |
| 4 | Should the domain model include computed fields (fields populated by code, not by user extraction)? | Entity purity |
| 5 | Cross-domain model references — should an entity in `banking` reference an entity in `kyc`? | Modularity |
| 6 | Migration strategy when a domain model version changes while conversations are in-flight? | Deployment safety |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — parent architecture document
- [Extraction Layer Design](./2026-06-17-extraction-layer-design.md) — Extract/Validate/Transform interfaces
- [State Machine Design](./2026-06-16-state-machine-design.md) — guard expression base, intent+state resolution
- [Home Insurance Workflow](../../examples/home-insurance/workflow.yaml) — reference domain model instantiation
- zelkim/langgraph-insurance-chatbot — two-stage dynamic entity selection (auto vs home vs life)
