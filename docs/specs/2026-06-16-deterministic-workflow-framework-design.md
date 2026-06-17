# Deterministic Workflow Framework — High-Level Design

**Design Scope:** Architecture discussions only. No implementation code.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-16 | 0.1.0 | Initial three-layer architecture |
| 2026-06-16 | 0.2.0 | Reset to minimal version for step-by-step discussion |
| 2026-06-16 | 0.3.0 | Add cross-reference to state machine design; translate appendix to English |
| 2026-06-16 | 0.4.0 | Add examples reference; unify all examples under home insurance domain |

---

## 1. Problem Statement

Enterprise chatbots in regulated industries (finance, health, insurance) need to be auditable and predictable—but users speak natural language. A purely rule-based system can't understand users; a purely LLM-driven system can't guarantee correctness.

## 2. Core Architecture: Three Layers

```
User Input
   |
   v
+-----------------------+
| Layer 1: UNDERSTAND   |  -> "What does the user want?"
| Intent + Entities     |
+-----------+-----------+
            v
+-----------------------+
| Layer 2: DECIDE        |  -> "What should we do?"
| Routing + Execution    |
+-----------+-----------+
            v
+-----------------------+
| Layer 3: RESPOND       |  -> "What do we say back?"
| Message Generation     |
+-----------------------+
```

- **Layer 1** extracts intent and structured entities from free-form user input.
- **Layer 2** decides the next state, validates data, and performs deterministic business logic.
- **Layer 3** produces the user-visible response.

## 3. Key Insight: Per-Node Control, Not Per-Layer

The LLM/deterministic decision is not made at the layer level. Each individual node within each layer independently chooses whether to use LLM or deterministic rules.

For example, within Layer 2, a routing node might be a pure `switch` statement (deterministic), while the node next to it might use LLM for semantic validation (LLM). Layers describe *what* happens; nodes describe *how*.

## 4. Related Design Documents

- **[State Machine Design](./2026-06-16-state-machine-design.md)** — Detailed FSM layer design: transitions + LangGraph fusion, state metadata (preconditions, guards, invariants), intent+state resolution, and FSM-specific open questions.
- **[Intent Classification Design](./2026-06-16-intent-classification-design.md)** — Layer 1 intent classification strategy: LLM-first + keyword fallback, output contract, conversation context.
- **[Home Insurance Examples](../examples/home-insurance/)** — Complete workflow definition (`workflow.yaml`), intent catalog, end-to-end scenarios, and audit log sample.

---

## References

1. LangGraph — State graph execution framework (runtime substrate). *github.com/langchain-ai/langgraph*
2. Rasa CALM — "The LLM understands; the code enforces." *rasa.com*
3. zelkim/langgraph-insurance-chatbot — LangGraph.js insurance quote chatbot. *github.com/zelkim/langgraph-insurance-chatbot*
4. Prodigal Payment Collection Agent — Python FSM payment agent. *github.com/AvnishChitrigi/Prodigal-Assignment-Production-Ready-Payment-Collection-AI-Agent*

---

## Appendix: Implementation Planning — Open Questions (Non-State-Machine)

> Questions identified during design but deferred for implementation planning.
> For state machine specific questions, see [State Machine Design](./2026-06-16-state-machine-design.md) Appendix C.

### A.1 LLM Integration

| # | Question | Impact |
|---|----------|--------|
| 1 | LLM node error handling — recovery strategies for timeout, hallucination, tool call failure | Conversation continuity |
| 2 | LLM node testing — how to verify behavior without real LLM calls | Test stability, CI speed |
| 3 | LLM scope enforcement — how to ensure LLM only handles Layer 1 (understanding) and Layer 3 (response), not Layer 2 (decisions) | Architecture enforceability |
| 4 | Context filtering — what data can be passed to LLM, sensitive field masking rules | PII/GDPR compliance |

### A.2 Security & Compliance

| # | Question | Impact |
|---|----------|--------|
| 5 | Tool permissions — who can call what tool in which state, allowlist granularity and management | Prevent LLM overreach |
| 6 | PII handling — tokenization, encryption in transit, storage strategy | PCI DSS / SOC2 / GDPR |

### A.3 Human-in-the-Loop

| # | Question | Impact |
|---|----------|--------|
| 7 | Approval UI design — what the approver sees, whether they can modify data | Approval effectiveness |
| 8 | Approval timeout — auto-approve, reject, or delegate when approver is unavailable | Business continuity |
| 9 | Approval delegation chain — who to escalate to and in what order | Organizational fit |

### A.4 Testing & Quality

| # | Question | Impact |
|---|----------|--------|
| 10 | Deterministic node (code executor) unit testing strategy | Core business logic correctness |
| 11 | Generated graph integration testing — how to verify auto-generated LangGraph behavior | End-to-end correctness |

### A.5 Deployment & Operations

| # | Question | Impact |
|---|----------|--------|
| 12 | Blue-green deployment — routing conversations when old and new workflows coexist | Zero-downtime updates |
| 13 | Multi-tenant isolation — how to isolate workflow instances across customers | Security, resource management |
| 14 | Audit log storage — format, retention period, query API | Regulatory compliance review |
