

## Project Principles

1. **Architecture-First.** Clean, well-structured architecture is the foundation of every decision. Prefer clarity over cleverness.
2. **Fintech-First, Industry-Agnostic.** Primary use case targets fintech (insurance, banking, payment). Architecture must remain generic enough to extend to any regulated industry's agentic workflow (healthcare, legal, government).
3. **Guided Framework, Not Out-of-the-Box.** This is a reference architecture and design pattern framework—not a pre-built, plug-and-play solution. It provides the *how* and *why*; users adapt it to their industry. Detailed implementation questions are deferred for architect-level discussions during adoption, not solved upfront.
4. **Actionable & Extensible.** Every design decision must result in something that can be built and extended. Framework-level concerns (security, multi-tenancy, deployment) are identified early but not prematurely solved.
5. **Learnable.** Documentation, examples, and API design must guide users from understanding to adoption. A new developer should be able to read the spec and understand *what* to build and *why*.
6. **Framework as Interface + Pattern Injection.** The framework exposes clean interfaces but internally injects proven patterns (state-aware prompting, deterministic fallback, sticky mode, sub-workflow reuse). It absorbs the "dirty work" — LLM guardrails, permission enforcement, retry budgets, audit trail — so the developer focuses on business logic.
7. **Code Conventions.** Every method ≤ 50 lines. Every file ≤ 1000 lines. Executors are small, composable, and single-responsibility. Complex workflows are split across files and sub-workflows.
8. **LLM Output is JSON.** All LLM interactions produce structured JSON output. The framework enforces output validation guardrails (schema check, field presence, type coercion). Free-text generation is limited to Layer 3 (Response).
9. **Follow VISION.md.** [docs/VISION.md](./docs/VISION.md) is the authoritative master reference and guiding direction for this project. All design decisions must align with the vision. If you believe the vision itself has a flaw, raise the concern at any time — otherwise, every design must strictly follow it. When writing specs: (a) check the Vision checklist before declaring a spec complete, (b) record every significant design decision with its rationale (WHY) in the Architecture Decisions table AND inline in the relevant spec — accuracy/cost/latency trade-offs must be explicit.
10. **English-Only Commits.** Every file committed to the GitHub repository must be in English. Non-English content belongs only in directories listed in `.gitignore`. Never commit non-English files to the repo.

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


## Project Context
- Language: Python
- Repo: git@github.com:cicidi/deterministic-ai-agent.git
- IDEs: claude, opencode, gemini


<!-- PROTECTED:CRITICAL-RULES -->

## Local Override

CRITICAL: If `CLAUDE.local.md` exists in this project root, use Read tool to load it now before doing anything else.
- Claude Code: natively auto-loads this file
- OpenCode: must use Read tool explicitly

Contains personal working context — active initiative, task state, config paths, workflow preferences, available skills.

## Mandatory Guardrails

ALL team members must follow these. No exceptions.

### Git Safety
- Never push to main/master — all changes through PR
- Never force push. Never delete remote branches without confirmation
- Never merge PRs without human approval
- Branch: `{type}/{issue-id}-{short-description}`
- Commit: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)

### Code Safety
- Never hardcode secrets or tokens — use env vars
- Never commit `.env` files or credentials
- Never log passwords, tokens, or PII
- Never bypass auth checks — always validate permissions
- Always use parameterized queries — never interpolate user input into SQL/shell/HTML

### Code Quality
- Code must pass lint and format checks before commit
- No commented-out code in PRs
- No `TODO` without a linked GitHub issue
- Don't modify PROTECTED blocks (`<!-- PROTECTED -->` to `<!-- END PROTECTED -->`)
- Don't fabricate information — ask when uncertain

## Compaction & State Persistence

1. **Save on compaction / session end**: Run `coworker state-update {descriptive-name} -s "one-line summary"` before stopping. Use a descriptive task name (e.g. `fix-state-paths`, `add-oauth-flow`). If no name is given, a timestamp is auto-generated to ensure uniqueness.
2. **Manual milestone save**: Run `coworker state-update {task-name} -s "what I finished"` after completing a milestone.
3. **After compaction**: CLAUDE.md is re-injected but prior conversation is gone. Re-read the most recent `docs/state/state-*.md` and `CLAUDE.local.md`. Re-run the Context Self-Assessment Checklist.
4. **Compact early**: Write state at 50-70% of context window — before model performance degrades.

## Context Management

MANDATORY: Before starting any non-trivial task, run this checklist:

1. **Goal clarity** — Is the goal clear? If not, ask user. Current task details are in `CLAUDE.local.md`.
2. **Find spec** — Does `docs/specs/` contain PRD or design docs for this task? Read them before coding.
3. **Check discussions** — Were there prior discussions? Check `docs/discussion/` and Team Links below.
4. **Recall state** — Was this task started before? Check state file path in `CLAUDE.local.md`, then read it.
5. **Verify reads** — Are ALL referenced documents actually read? Do not proceed until confirmed.

### Information Flow
| What | Where | Notes |
|------|-------|-------|
| Project identity, repo, relationships | This file | Slow-changing, shared by all |
| Design docs, specs, discussion logs | `docs/specs/`, `docs/discussion/` | Shared, committed |
| Team wikis, Slack, external links | Team Links section below | Shared references |
| Task goal, testing approach | `CLAUDE.local.md` | Changes per task, personal |
| Current workflow, skills in use | `CLAUDE.local.md` | Changes per session |
| Initiative context, reference docs | `CLAUDE.local.md` | Injected by coworker |
| Work-in-progress, temp artifacts | `CLAUDE.local.md` or `docs/state/` | Discardable after completion |

## Workflow Selection

For every new task, scan these characteristics and decide:

### Auto-execute (no prompt needed)
- Clear requirements, simple change, low risk → Just do it
- Bug fix with clear reproduction steps → bug-hunt, fix, verify
- Minor refactoring, tests pass → Edit, run tests, done

### Suggest workflow, then confirm
- Unclear requirements, large scope → brainstorming → spec → implement
- Clear requirements, complex/high-risk code → TDD + loop engineering
- Large feature, lots of discussion needed → brainstorming + TDD + loop
- Documentation work → doc conventions skill

**Decision logic**: If requirements AND scope AND risk are all clear/small/low → auto. Otherwise → suggest + confirm.

**Reality check**: These are heuristics, not iron laws. For reversible ops (reading files, `ls`, `grep`, `git status`) just proceed. Don't overthink trivial work.

## Auto Memory

- Read this CLAUDE.md first (upfront rules), then check auto-memory for past learnings
- Conflict: upfront rules override auto-memory. Never let auto-memory write back into CLAUDE.md

<!-- END PROTECTED:CRITICAL-RULES -->



## Project Identity



_Repo URL auto-discovered by AI._



## Project Relationships

_(none configured)_



## Knowledge Repo

_(run `coworker init` to scan docs/ structure)_



## Team Links

_(none configured — add shared wikis, Slack channels, design docs)_
