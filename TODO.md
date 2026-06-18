# TODO — Deterministic Workflow Framework

Last updated: 2026-06-17

---

## Skills — Done

| Skill | Description |
|-------|-------------|
| ✅ **issue-create** | Generate structured GitHub issues from spec discussions |
| ✅ **implement-interview** | Interview-based loading of 11 specs + brainstorming, produces product-level implement plan. **This is the spec-generator (VISION.md core vision)** |
| ✅ **evals-create** | Generate goal definition + goal check eval + response eval + intent eval + decision eval |
| ✅ **ai-cowork-install** | Install and configure ai-coworker, register MCP server, sync to all AI tools |

---

## Skills — Planned

| Skill | Description | Priority |
|-------|-------------|----------|
| 🔲 **intent-analysis** | Analyze prod logs, discover unhandled intents, generate gap report. Principle: better than yesterday | P0 |
| 🔲 **tdd** | Define test cases first (user dialogue, extract node, validate node, decision node, response node), mock LLM to save tokens | P0 |
| 🔲 **test-client-create** | Simulate LLM test client chatting with agent, measure complete transaction rate | P1 |
| 🔲 **code-gen** | Generate Python code from implement plan (reference CrewAI's 4 coding skills) | P1 |
| 🔲 **spec-generator** | ✅ Merged into `implement-interview` — brainstorming + 11 specs → product-level spec | P0 |
| 🔲 **ask-docs** | MCP server for real-time latest spec API lookup (similar to CrewAI's ask-docs skill) | P2 |
| 🔲 **crewai-adaptor** | Enable our workflow to run as a CrewAI Flow/Crew step, mutual invocation | P1 |
| 🔲 **history-labeler** | Based on history turns, label correctly-handled as positive example, incorrect as negative, generate training/test datasets. Existing frameworks: **Argilla** (data labeling platform), **Label Studio** | P1 |
| 🔲 **multi-llm-runner** | Run test set across multiple LLMs simultaneously (e.g., `deepseek-v4 / gpt-4o / claude-sonnet`), compare accuracy side-by-side; also test whether client-side LLM correctly understands our response. Existing frameworks: **promptfoo** (multi-LLM comparison), **DeepEval** (metric-based evaluation), **RAGAS** (RAG evaluation) | P1 |

---

## Spec Documents — Done

| # | Spec | Version |
|---|------|---------|
| 1 | [HLD](docs/specs/2026-06-16-deterministic-workflow-framework-design.md) | v0.7.0 |
| 2 | [Intent Classification](docs/specs/2026-06-16-intent-classification-design.md) | v0.3.0 |
| 3 | [State Machine](docs/specs/2026-06-16-state-machine-design.md) | v0.6.0 |
| 4 | [Extraction Layer](docs/specs/2026-06-17-extraction-layer-design.md) | v0.4.0 |
| 5 | [Domain Model](docs/specs/2026-06-17-domain-model-design.md) | v0.3.0 |
| 6 | [Routing & Execution](docs/specs/2026-06-17-routing-execution-layer-design.md) | v0.3.0 |
| 7 | [Response Generation](docs/specs/2026-06-17-response-generation-layer-design.md) | v0.4.0 |
| 8 | [LLM Gateway](docs/specs/2026-06-17-llm-gateway.md) | v0.1.0 |
| 9 | [Tool Ecosystem](docs/specs/2026-06-17-tool-ecosystem.md) | v0.3.0 |
| 10 | [Environment Config](docs/specs/2026-06-17-environment-config.md) | v0.3.0 |
| 11 | [Auth & Token Verification](docs/specs/2026-06-17-auth-token-verification.md) | v0.2.0 |

## Spec Documents — Planned

| # | Spec | Status | Description |
|---|------|--------|-------------|
| 12 | MCP API Protocol | 🔲 draft v0.1 | Framework API via MCP, compatible with Claude/OpenAI/Google |
| 13 | Conversation Lifecycle | 🔲 draft v0.1 | create/active/paused/resume/timeout, trace_id=user_id |
| 14 | Observability & Monitoring | 🔲 draft v0.1 | Grafana dashboards, Prometheus metrics, alert rules |
| 15 | CI/CD (Jenkins) | 🔲 draft v0.1 | Jenkins pipeline, eval→deploy, mrratequote chat example |
| 16 | A2A Protocol | 🔲 draft v0.1 | Agent-to-Agent communication, sub-workflow = A2A |
| 17 | Rate Limiting | 🔲 draft v0.1 | per-user/per-tenant/per-tool, interview integration |
| 18 | Widget Templates | 🔲 draft v0.1 | A2A chatbot template + Claude-generated widgets for mrratequote |

---

## Future Work

- [ ] **CrewAI Compatibility** — Export domain model → CrewAI config. Register pipeline as CrewAI tool. Mutual invocation between our deterministic sub-workflow and CrewAI Crew.
- [ ] RoleResolver implementation (Auth spec §5.1 interface placeholder)
- [ ] Python reference implementation
- [ ] LangFlow custom components for framework nodes
- [ ] `agentState` reducer conflict detection for async sub-workflow + parent concurrent writes
- [ ] Token refresh support for long-running conversations
