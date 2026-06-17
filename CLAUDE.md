

<!-- INITIATIVE:chat-experience-deterministic-work-flow START -->
## Active Initiative: chat-experience-deterministic-work-flow

> Design and build a deterministic workflow framework for enterprise chatbots in regulated industries. Three-layer architecture (NLU/Extraction → Routing/Execution → Response) with per-node LLM/deterministic switch. Outcome: spec documents (no implementation code yet).

### Projects in scope
| Project | Role | Branches |
|---------|------|----------|
| deterministic-workflow | peer | main, feat/deterministic-framework |
| saas-app | peer | main |

### Key Decisions
- Python + LangGraph, generic framework (not single-industry)
- LLM-assisted NLU with deterministic core workflows
- Per-node control granularity (not per-layer binary switch)
- Sub-workflow reuse for shared capabilities
- Spec-first with Python reference implementation
- Design docs: schemas + samples only. No implementation code until requested.
- Docs/comments in English, discussion in Chinese.

### References
- [Primary] zelkim/langgraph-insurance-chatbot (TypeScript, LangGraph.js, insurance quote)
- [Secondary] Prodigal Payment Collection Agent (Python FSM, payment collection)
- [Supplementary] chatbot-FSM-experiment (FastAPI+Next.js, healthcare scheduler)

<!-- INITIATIVE:chat-experience-deterministic-work-flow END -->

