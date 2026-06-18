# Deterministic Workflow Framework

> A guided reference architecture for building auditable, deterministic agentic workflows in regulated industries.

## What This Is

A **guided framework** for designing enterprise chatbot workflows where correctness is non-negotiable. It provides architectural patterns, design schemas, and concrete examples—not a pre-built, plug-and-play library.

Use this framework to **learn the architecture**, then **adapt it** to your own industry and use case.

For project principles that guide all decisions, see [CLAUDE.md](./CLAUDE.md).

## Architecture

Three-layer deterministic workflow:

```
User Input -> [Layer 1: UNDERSTAND] -> [Layer 2: DECIDE] -> [Layer 3: RESPOND]
              Intent + Entities       Routing + Execution   Message Generation
              (LLM)                   (State Machine + LLM) (LLM)
```

**Per-node granularity:** each node independently chooses LLM or deterministic execution. Layers describe *what* happens; nodes describe *how*.

## Project Vision

This project produces **two deliverables**:

1. **Framework Specs** — comprehensive design documents for a deterministic AI agent framework (in `docs/specs/`)
2. **Spec Generator Skill** — a downstream tool that loads these specs and interviews a developer to produce a concrete product specification, ready for code implementation planning

```
Developer describes their product (e.g., "insurance claims chatbot")
    → Skill loads framework specs as interview template
    → Skill asks spec-by-spec questions (domain model, intents, states, transitions...)
    → Skill outputs a complete, product-specific spec
    → Developer proceeds to implementation planning
```

## Documentation

### Design Docs (`docs/specs/`)

| Document | Content |
|----------|---------|
| [High-Level Design](./docs/specs/2026-06-16-deterministic-workflow-framework-design.md) | Problem statement, three-layer architecture, per-node control, non-FSM open questions, downstream skill vision |
| [State Machine Design](./docs/specs/2026-06-16-state-machine-design.md) | transitions + LangGraph fusion, state metadata, intent+state resolution, FSM open questions |
| [Intent Classification](./docs/specs/2026-06-16-intent-classification-design.md) | Layer 1 intent classification: LLM-first + keyword fallback |
| [Extraction Layer](./docs/specs/2026-06-17-extraction-layer-design.md) | Layer 1 entity extraction: Extract/Validate/Transform pipeline, 3+ implementation options per interface |
| [Domain Model](./docs/specs/2026-06-17-domain-model-design.md) | Single source of truth: Entity + State + Transition schemas, cross-workflow reuse |
| [Routing & Execution](./docs/specs/2026-06-17-routing-execution-layer-design.md) | Layer 2: code executors, decision nodes, sticky mode, sub-workflow, retry/errorNode, permission model, tool system |
| [Response Generation](./docs/specs/2026-06-17-response-generation-layer-design.md) | Layer 3: goal setting (async), response generation (LLM/template/hybrid), goal completion check (parallel, 422), frontmatter protocol, PII scrubbing |
| [Tool Ecosystem](./docs/specs/2026-06-17-tool-ecosystem.md) | Visual editor (LangFlow), dev server (LangGraph CLI), debug (LangSmith), rule engines, MCP servers, Claude Desktop integration |
| [Environment Config](./docs/specs/2026-06-17-environment-config.md) | Three environments (dev / e2e / prod), env variable hierarchy, per-env thresholds, framework.yaml sections |
| [LLM Gateway](./docs/specs/2026-06-17-llm-gateway.md) | Mandatory structured JSON output — output_schema required for every LLM call, framework validates before returning |
| [Auth & Token Verification](./docs/specs/2026-06-17-auth-token-verification.md) | OAuth/OIDC login, JWT verification, API key, user context injection, multi-tenant isolation, per-environment auth |

### Examples (`docs/examples/home-insurance/`)

| File | Content |
|------|---------|
| [README](./docs/examples/home-insurance/README.md) | Overview and workflow diagram |
| [workflow.yaml](./docs/examples/home-insurance/workflow.yaml) | Complete home insurance workflow (quote + claim branches) |
| [intent-definitions.md](./docs/examples/home-insurance/intent-definitions.md) | Custom intents for home insurance domain |
| [e2e-scenarios.md](./docs/examples/home-insurance/e2e-scenarios.md) | End-to-end walkthroughs (quote, claim, high-risk routing) |
| [audit-log-sample.json](./docs/examples/home-insurance/audit-log-sample.json) | Sample audit log |

## Tech Stack

| Category | Tool | Purpose |
|----------|------|---------|
| **Runtime** | Python + LangGraph | State graph execution, checkpoint, streaming |
| **State Machine** | transitions | Deterministic FSM, Graphviz export |
| **Visual Editor** | LangFlow | Drag-and-drop graph building |
| **Dev Server** | LangGraph CLI | Hot reload + graph visualization |
| **Debug & Monitor** | LangSmith Studio | Trace, time-travel debug, eval |
| **Rule Engines** | durable_rules / business-rules / pyknow | Validation + decision rules |
| **PII Detection** | Microsoft Presidio | Sensitive data detection, redaction |
| **Tool Protocol** | MCP / REST / CLI | External capability integration |

## Topics for Architect Discussions

Detailed open questions are maintained in the spec documents:

- **State machine topics** — guards, nesting, parallel states, version migration, static verification -> [State Machine Design, Appendix C](./docs/specs/2026-06-16-state-machine-design.md#appendix-c-implementation-planning--open-questions-state-machine)
- **LLM, security & operations topics** — PII, tool permissions, human-in-the-loop, deployment -> [High-Level Design, Appendix](./docs/specs/2026-06-16-deterministic-workflow-framework-design.md#appendix-implementation-planning--open-questions-non-state-machine)

These are deferred for architect-level discussions during adoption, not solved upfront.

## License

[MIT](./LICENSE)
