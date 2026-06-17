# Deterministic Workflow Framework

> A guided reference architecture for building auditable, deterministic agentic workflows in regulated industries.

## What This Is

A **guided framework** for designing enterprise chatbot workflows where correctness is non-negotiable. It provides architectural patterns, design schemas, and concrete examples—not a pre-built, plug-and-play library.

Use this framework to **learn the architecture**, then **adapt it** to your own industry and use case.

For project principles that guide all decisions, see [CLAUDE.md](./CLAUDE.md).

## Architecture

Three-layer deterministic workflow:

```
User Input → [Layer 1: UNDERSTAND] → [Layer 2: DECIDE] → [Layer 3: RESPOND]
              Intent + Entities       Routing + Execution   Message Generation
              (LLM)                   (State Machine + LLM) (LLM)
```

**Per-node granularity:** each node independently chooses LLM or deterministic execution. Layers describe *what* happens; nodes describe *how*.

## Getting Started

Read the specs in `docs/superpowers/specs/`:

| Document | Content |
|----------|---------|
| [High-Level Design](./docs/superpowers/specs/2026-06-16-deterministic-workflow-framework-design.md) | Problem statement, three-layer architecture, per-node control, non-FSM open questions |
| [State Machine Design](./docs/superpowers/specs/2026-06-16-state-machine-design.md) | transitions + LangGraph fusion, state metadata, invoice & payment use cases, FSM open questions |

## Tech Stack

- **Python** — reference implementation language
- **transitions** — deterministic FSM layer (state definition source of truth)
- **LangGraph** — LLM infrastructure (streaming, checkpointing, human-in-the-loop, tool use)

## Topics for Architect Discussions

Detailed open questions are maintained in the spec documents:

- **State machine topics** — guards, nesting, parallel states, version migration, static verification → [State Machine Design, Appendix C](./docs/superpowers/specs/2026-06-16-state-machine-design.md#appendix-c-implementation-planning--open-questions)
- **LLM, security & operations topics** — PII, tool permissions, human-in-the-loop, deployment → [High-Level Design, Appendix](./docs/superpowers/specs/2026-06-16-deterministic-workflow-framework-design.md#appendix-implementation-planning--open-questions-non-state-machine)

These are deferred for architect-level discussions during adoption, not solved upfront.
