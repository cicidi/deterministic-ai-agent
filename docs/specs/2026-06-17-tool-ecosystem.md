# Tool Ecosystem Integration

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Visual editor, graph debugger, rule engines, MCP servers, and all third-party tools that integrate with the framework.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial tool ecosystem spec |
| 2026-06-17 | 0.2.0 | Replace Python code blocks with YAML config examples; add errorNode failure routing (Section 6.4); add Open Questions (Section 13) |
| 2026-06-17 | 0.3.0 | Section 2.2 LangFlow mapping table: change "Error Handler" → "ErrorNode"; add Section 6 Permission Enforcement (pycasbin) |

---

## 1. Tool Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPER WORKFLOW                        │
├───────────────┬───────────────────┬─────────────────────────┤
│   Design      │   Debug / Test    │   Deploy / Monitor      │
├───────────────┼───────────────────┼─────────────────────────┤
│  LangFlow     │  LangGraph CLI    │  LangSmith Studio       │
│  (drag-drop   │  (graph view +    │  (trace, eval,          │
│   visual edit)│   hot reload)     │   prompt engineering)    │
├───────────────┴───────────────────┴─────────────────────────┤
│                    RUNTIME ENGINE                             │
├───────────────┬───────────────────┬─────────────────────────┤
│  LangGraph    │  Rule Engines     │  Tool Servers           │
│  (state graph │  durable_rules    │  MCP servers            │
│   execution)  │  business-rules   │  API endpoints          │
│               │  pyknow           │  Claude Desktop         │
├───────────────┴───────────────────┴─────────────────────────┤
│                    DETERMINISTIC FRAMEWORK                    │
│  (domain model, extraction, routing, response, permission)   │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Visual Editor** | LangFlow | Drag-and-drop graph building, node configuration |
| **Dev Server** | LangGraph CLI (`langgraph dev`) | Local dev with hot reload + graph visualization |
| **Debug & Monitor** | LangSmith Studio | Trace execution, time-travel debug, eval datasets |
| **State Machine** | `transitions` | Deterministic FSM definition + Graphviz export |
| **Graph Runtime** | LangGraph | State graph execution, checkpoint, streaming |
| **Rule Engines** | durable_rules, business-rules, pyknow | Validation + decision rules |
| **Tool Servers** | MCP servers, REST APIs, CLI commands | External capability integration |
| **LLM Providers** | OpenAI, Anthropic (Claude), local models | NLU, extraction, response generation |
| **PII Detection** | Presidio, spaCy, custom NER | Sensitive data detection, redaction |

---

## 2. LangFlow — Visual Editor

### 2.1 Role

Drag-and-drop visual builder for LangGraph workflows. Developers can:
- Visually design graph topology (nodes + edges)
- Configure node parameters (state, strategies, permissions)
- Export as LangGraph graph code or JSON
- Test interactively in the playground

### 2.2 Integration with Our Framework

```
LangFlow UI
    │
    │  drag-and-drop nodes: extract, validate, transform, decide, respond
    │  configure: strategy, retry, permission, tool allowlist
    │
    ▼
Export as YAML → domain_model.yaml + workflow.yaml
    │
    ▼
Our Framework loads YAML → generates LangGraph graph
```

**Node palette mapping:**

| LangFlow Node Type | Framework Interface | Configurable In |
|--------------------|--------------------|-----------------|
| `Extract` | `ExtractionNode` | extract_strategy, extract_rules |
| `Validate` | `ValidationNode` | validate_strategy, validation_rules |
| `Transform` | `TransformNode` | transform_strategy, transform_rules |
| `Code Executor` | `CodeExecutor` | execute function, input/output schema |
| `Decision` | `DecisionNode` | rule engine, LLM fallback |
| `Sub-Workflow` | `SubWorkflowInvoker` | sub_workflow name, sync/async, input_mapping |
| `Respond` | `ResponseGenerator` | response_strategy (pure_message / widget) |
| `ErrorNode` | `ErrorNode` | strategy (clarify / escalate / terminate) |

### 2.3 Installation

```bash
pip install langflow
langflow run
# → http://localhost:7860
```

### 2.4 LangFlow Custom Component

Register framework nodes as LangFlow custom components via YAML:

```yaml
# langflow_components/extract_node.yaml
name: ExtractEntity
display_name: "Extract Entity"
description: "Extract structured entities from user input"
icon: Search
category: DeterministicWorkflow

parameters:
  - name: strategy
    display_name: "Strategy"
    type: dropdown
    options: [llm_primary, deterministic, hybrid]
    default: hybrid
  - name: entity
    display_name: "Entity"
    type: str
    info: "Domain model entity name"
  - name: state_hint
    display_name: "State Hint"
    type: text
    multiline: true

outputs:
  - name: message
    type: Message
    description: "Extracted entity data"
```

---

## 3. LangGraph CLI — Dev Server

### 3.1 Role

Local development server with hot reloading and built-in graph visualization. The `langgraph dev` command starts an API server that hosts the LangGraph graph, with a browser-based UI showing:
- Graph topology (nodes + edges)
- Current state at each node
- Stream trace of execution

### 3.2 Integration

```bash
# Start dev server with our framework graph
langgraph dev --config langgraph.json
```

```json
// langgraph.json
{
  "dependencies": ["langchain_openai", "./deterministic_workflow"],
  "graphs": {
    "home_insurance_quote": "./deterministic_workflow/graph.py:build_graph"
  },
  "env": "./.env"
}
```

The `build_graph` entry point loads config from YAML and compiles the LangGraph `StateGraph`:

```yaml
# deterministic_workflow/config.yaml — engine bootstrap config
engine:
  domain_model: "domain-models/home-insurance.yaml"
  workflow_config: "workflows/home_insurance_quote.yaml"
  checkpoint_backend: "postgresql://localhost:5432/langgraph"
  rule_engine: durable_rules

langgraph:
  entry_point: "deterministic_workflow.graph:build_graph"
  # build_graph() reads engine config, creates WorkflowEngine, returns compiled graph
```

### 3.3 Capabilities

| Feature | Command / API |
|---------|--------------|
| Start dev server | `langgraph dev` |
| Hot reload on change | Default (watch mode) |
| View graph | Browser at `http://localhost:2024` |
| Test conversation | Built-in chat UI |
| Inspect state | Click any node to view state snapshot |
| Time travel | Replay from any checkpoint |
| Deploy to Docker | `langgraph build -t myimage` |

---

## 4. LangSmith Studio — Debug & Monitor

### 4.1 Role

Cloud-based IDE for debugging, testing, and monitoring LangGraph agents. Features:
- Execution trace with node-level detail
- Time-travel debugging (replay from any checkpoint)
- Eval dataset management
- Prompt engineering playground
- One-click deploy

### 4.2 Integration

```yaml
# framework.yaml — LangSmith tracing configuration
langsmith:
  api_key: "${LANGSMITH_API_KEY}"
  tracing: true
  project: "home-insurance-quote"
  # Framework auto-traces all LLM calls and graph execution.
  # Every conversation.send() creates a trace in LangSmith Studio.
```

### 4.3 Eval Integration

Run eval datasets against our workflow to verify goal check accuracy and response quality:

```yaml
# langsmith/eval_config.yaml
evaluators:
  - goal_completion_accuracy
  - response_pii_leakage
  - decision_correctness

dataset: "home-insurance-eval-dataset"

experiment:
  name: "home-insurance-v1.0"
  description: "Baseline eval for home insurance quote workflow"
  metadata:
    domain: home_insurance
    version: "1.0.0"

# Run via: langsmith eval run --config langsmith/eval_config.yaml
```

---

## 5. Rule Engines

### 5.1 Role

Three pluggable rule engines for validation and decision nodes:

| Engine | Install | Best For |
|--------|---------|----------|
| `durable_rules` | `pip install durable-rules` | When/then inference, cross-field rules |
| `business-rules` | `pip install business-rules` | Simple YAML/JSON rules, no inference |
| `pyknow` | `pip install pyknow` | Expert system, Fact/KnowledgeEngine |

### 5.2 Configuration

```yaml
# workflow.yaml
nodes:
  validate_property_info:
    rule_engine: durable_rules    # per-node override

# framework.yaml (global default)
rule_engine:
  default: durable_rules
  available: [durable_rules, business-rules, pyknow]
```

### 5.3 Custom Rule Engine Registration

Register custom rule engines via YAML configuration:

```yaml
# framework.yaml
rule_engine:
  default: durable_rules
  available:
    - durable_rules
    - business-rules
    - pyknow
    - custom_engine:
        module: "my_package.custom_rules"
        class: "CustomRuleEngine"
        # Must implement: compile(ruleset_name, rules) -> None, execute(ruleset_name, facts) -> dict
```

---

## 6. Permission Enforcement — pycasbin

### 6.1 Role

Our framework has a two-level permission model (see Routing & Execution spec §7). The config-level enforcement (per-node `allowed_tools` + `allowed_transitions` YAML lists) is simple. For deployments with complex access patterns (many roles × many tools), `pycasbin` provides a configurable authorization engine.

### 6.2 When to Use pycasbin

| Scenario | Tool |
|----------|------|
| Simple: 1-2 roles, <10 tools | YAML allowlists (built-in) — no external library needed |
| Medium: 3-10 roles, <50 tools | pycasbin with CSV policies |
| Complex: role hierarchy, attribute-based rules | pycasbin with database adapter |

### 6.3 Installation

```bash
pip install pycasbin
```

### 6.4 Casbin Model Definition

The Casbin model defines the access control pattern. Written once, not changed at runtime:

```ini
# model.conf
[request_definition]
r = sub, obj, act        # subject (user/role), object (tool/transition), action (read/write)

[policy_definition]
p = sub, obj, act        # policy rule: who can do what to which

[role_definition]
g = _, _                 # role inheritance: g(alice, admin) means alice inherits admin privileges

[policy_effect]
e = some(where (p.eft == allow))   # allow if ANY matching policy grants access

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

### 6.5 Policy (Generated from YAML Config)

```csv
# policy.csv — auto-generated from workflow YAML permission sections

# Role inheritance
g, scope:dangerous_operation:write, operator
g, scope:sensitive_data:read, analyst
g, operator, analyst
g, admin, operator

# Tool access policies
p, admin, *, *                          # admin: full access
p, operator, payment_gateway_api, write
p, operator, calculate_premium_api, read
p, operator, vector_search_mcp, read
p, analyst, policy_lookup_api, read
p, analyst, claim_history_api, read
p, user, vector_search_mcp, read
p, user, calculate_premium_api, read

# Transition access policies
p, *, collect_property_info, transition
p, *, collect_coverage_needs, transition
p, admin, payment_processing, transition
p, operator, payment_processing, transition
```

### 6.6 Framework Integration

```yaml
# framework.yaml
permission:
  engine: pycasbin           # pycasbin | native (built-in YAML list check)
  model: "config/casbin/model.conf"
  policy_source: workflow_yaml   # workflow_yaml | csv_file | database

# Per-workflow override
workflows:
  home_insurance_quote:
    permission:
      engine: native          # simple allowlist, no casbin needed
  enterprise_payment:
    permission:
      engine: pycasbin        # complex role hierarchy
      model: "config/casbin/payment_model.conf"
```

### 6.7 Enforcement Flow

```
1. Framework loads workflow YAML
2. If permission.engine == "pycasbin":
     a. Load casbin model.conf
     b. Generate policy.csv from YAML permission sections
     c. Create enforcer = casbin.Enforcer(model, adapter)
3. On every tool call or state transition:
     a. Config-level: enforcer.enforce(user_role, tool_name, access_level)
     b. OAuth-level: check user.scopes against required scope
     c. If dangerous_operation_write: require human approval gate (regardless of casbin result)
```

### 6.8 pycasbin vs Built-in YAML Native

| Dimension | pycasbin | Built-in YAML (native) |
|-----------|----------|------------------------|
| Role hierarchy | ✅ built-in | ❌ flat list only |
| Attribute-based rules | ✅ with ABAC model | ❌ |
| Policy hot-reload | ✅ with adapter | ❌ (restart required) |
| External dependency | 1 pip package | 0 |
| Complexity | Medium (model.conf + policy) | Low (YAML list check) |
| Debugging | Casbin explain API | Simple print/assert |
| Best for | Complex multi-role, compliance-heavy | Most production use cases |

---

## 7. Tool Servers (MCP + API + Command)

### 6.1 MCP Server Integration

Our framework nodes can call MCP servers as tools. MCP servers expose capabilities (vector search, knowledge base query, external API) that nodes invoke within their permission allowlist.

```yaml
# framework.yaml — MCP tool discovery
mcp_servers:
  knowledge_base:
    command: "npx @anthropic/mcp-server-knowledge-base"
    args: ["--db-path", "./kb.sqlite"]
    tools: [search_documents, get_document]
  payment_gateway:
    command: "python mcp_servers/payment_server.py"
    env:
      API_KEY: "${PAYMENT_API_KEY}"
    tools: [payment_charge, payment_refund]
  # Framework auto-discovers tools at startup.
  # Available tools: vector_search, payment_charge, payment_refund, ...
```

### 6.2 Tool Registration

Register tools (API, MCP, command) via YAML configuration:

```yaml
# framework.yaml
tools:
  - name: calculate_premium_api
    type: api
    access_level: read
    api:
      method: POST
      url: "/api/v1/premium"
      timeout_ms: 5000
      request_body_schema:
        type: object
        properties:
          coverage_amount: { type: number }
          property_type: { type: string }

  - name: vector_search_mcp
    type: mcp
    access_level: read
    mcp:
      server: knowledge_base
      tool_name: search_documents

  - name: run_risk_model_cmd
    type: command
    access_level: read
    command:
      run: "python /opt/models/risk.py"
      timeout_ms: 30000
      sandbox: true
```

### 6.3 Claude Desktop Integration

When the framework is used with Claude Desktop, MCP tools are auto-exposed:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "deterministic-workflow": {
      "command": "python",
      "args": ["-m", "deterministic_workflow.mcp_server"],
      "env": {
        "WORKFLOW_CONFIG": "workflows/home_insurance_quote.yaml"
      }
    }
  }
}
```

### 6.4 Tool Failure Routing to `errorNode`

When a tool invocation fails (timeout, permission denied, invalid response), the framework routes the execution to a configured `errorNode` instead of crashing the workflow:

```yaml
# framework.yaml
tool_failure_handling:
  default_error_node: errorNode
  timeout_ms: 30000
  max_retries: 2

nodes:
  calculate_premium:
    tools: [calculate_premium_api, run_risk_model_cmd]
    on_tool_failure:
      route_to: errorNode       # overrides default_error_node
      fallback_on_timeout: true     # use cached/default value on timeout
      escalate_after: 3             # retries before escalating

  errorNode:
    strategies: [clarify, escalate, terminate]
    on_clarify: "ask user for missing/corrected input"
    on_escalate: "notify human agent with error context"
    on_terminate: "gracefully end conversation with apology"
```

This ensures deterministic behavior: every tool failure has a defined recovery path, and failures are auditable via LangSmith traces.

---

## 8. State Machine — `transitions`

### 7.1 Role

Python `transitions` library provides the deterministic FSM layer. Our framework generates a `transitions.Machine` from the Domain Model YAML (states + transitions + guards), then wraps it into a LangGraph node.

### 7.2 Graphviz Export

Configure FSM visualization via YAML and export to Graphviz:

```yaml
# framework.yaml
fsm:
  source: "domain-models/home-insurance.yaml"
  visualization:
    format: png
    output: "docs/diagrams/home_insurance_fsm.png"
    engine: dot                    # Graphviz layout engine
    render_on_build: true          # auto-export on graph compilation

  # Generated from domain-model YAML: states, transitions, guards
  # Exported as static FSM diagram for documentation
```

### 7.3 Integration Flow

```
domain-model.yaml
    │
    ▼
FSMGenerator → transitions.Machine (states, transitions, guards)
    │
    ▼
GraphCompiler → LangGraph StateGraph (nodes, conditional edges)
    │
    ▼
Visualization:
  - transitions: graph.draw() → PNG (static)
  - langgraph dev → browser (interactive)
  - LangFlow → drag-and-drop editor
```

---

## 9. PII Detection — Presidio

### 8.1 Role

Microsoft Presidio provides PII detection and anonymization for:
- Response scrubbing (before delivery to user)
- LLM prompt filtering (before sending data to LLM)
- Audit log redaction

### 8.2 Integration

Framework auto-configures Presidio based on domain model PII rules. Configuration is declarative:

```yaml
# framework.yaml
pii:
  engine: presidio
  language: en
  masking_strategy: partial_mask
  # Analyzer and Anonymizer engines are auto-initialized from this config.
  # Used for: response scrubbing, LLM prompt filtering, audit log redaction.

# domain-models/home-insurance.yaml (PII entities to detect)
pii_rules:
  entities:
    - PHONE_NUMBER
    - EMAIL_ADDRESS
    - PERSON
    - CN_ID_NUMBER           # custom: Chinese national ID
    - CREDIT_CARD
  masking_strategy: partial_mask
```

---

## 10. LLM Providers

### 9.1 Supported Providers

| Provider | Package | Use |
|----------|---------|-----|
| **OpenAI** | `langchain-openai` | Extraction, decision, response generation |
| **Anthropic (Claude)** | `langchain-anthropic` | Extraction, response generation, goal setting |
| **Local (Ollama)** | `langchain-ollama` | Offline extraction, PII-safe processing |
| **Azure OpenAI** | `langchain-openai` | Enterprise deployments |

### 9.2 Provider Configuration

```yaml
# framework.yaml
llm:
  default_provider: openai
  providers:
    openai:
      model: gpt-4o
      temperature: 0
      max_tokens: 4096
    anthropic:
      model: claude-sonnet-4-20250514
      temperature: 0
      max_tokens: 4096

  # Per-node override
  nodes:
    extract_property_info:
      provider: anthropic
      temperature: 0
    generate_quote_response:
      provider: openai
      temperature: 0.3
```

---

## 11. Complete Tool Integration Example

Full-stack configuration: from YAML → LangFlow → LangGraph → LangSmith — all declarative:

```yaml
# framework.yaml — complete integration config
engine:
  domain_model: "domain-models/home-insurance.yaml"
  workflow_config: "workflows/home_insurance_quote.yaml"
  rule_engine: durable_rules
  checkpoint_backend: "postgresql://localhost:5432/langgraph"

llm:
  default_provider: openai
  providers:
    openai: { model: gpt-4o, temperature: 0, max_tokens: 4096 }
    anthropic: { model: claude-sonnet-4-20250514, temperature: 0, max_tokens: 4096 }

langsmith:
  api_key: "${LANGSMITH_API_KEY}"
  tracing: true
  project: "home-insurance-quote"

mcp_servers:
  knowledge_base:
    command: "npx @anthropic/mcp-server-knowledge-base"
    args: ["--db-path", "./kb.sqlite"]
  payment_gateway:
    command: "python mcp_servers/payment_server.py"
    env: { API_KEY: "${PAYMENT_API_KEY}" }

tools:
  - name: calculate_premium_api
    type: api
    access_level: read
    api: { method: POST, url: "/api/v1/premium", timeout_ms: 5000 }
  - name: run_risk_model_cmd
    type: command
    access_level: read
    command: { run: "python /opt/models/risk.py", timeout_ms: 30000, sandbox: true }

tool_failure_handling:
  default_error_node: errorNode
  timeout_ms: 30000
  max_retries: 2

fsm:
  source: "domain-models/home-insurance.yaml"
  visualization: { format: png, output: "docs/diagrams/home_insurance_fsm.png" }

pii:
  engine: presidio
  language: en
  masking_strategy: partial_mask

export:
  langflow: "langflow/workflows/home_insurance.json"
  langgraph: "langgraph.json"
```

**Runtime flow:**
1. Framework loads `framework.yaml` → auto-discovers all tools, rule engines, PII config
2. Compiles LangGraph `StateGraph` from domain model + workflow
3. Exports to LangFlow JSON for visual editing and LangGraph JSON for dev server
4. Every conversation is auto-traced in LangSmith Studio
```

---

## 12. Tool Decision Matrix

| Need | Tool | Why |
|------|------|-----|
| Build workflow visually | **LangFlow** | Drag-and-drop, exports to code |
| Local dev + debug | **LangGraph CLI** | Hot reload, graph view, free |
| Production trace + eval | **LangSmith Studio** | Time-travel debug, eval datasets |
| FSM definition | **transitions** | Python-native, Graphviz export |
| Graph runtime | **LangGraph** | State graph, checkpoint, streaming |
| Complex rules | **durable_rules** | When/then inference, Drools-like |
| Simple rules | **business-rules** | Zero-inference YAML rules |
| Expert system rules | **pyknow** | Fact/KnowledgeEngine model |
| Permission enforcement (complex) | **pycasbin** | RBAC + ABAC, role hierarchy, policy hot-reload |
| Permission enforcement (simple) | **Built-in YAML** | No dependency, list check |
| PII detection | **Presidio** | Microsoft-backed, multi-language |
| External tools | **MCP servers** | Any language, standard protocol |
| Claude Desktop | **MCP config** | Auto-expose workflow as tool |
| Mandatory JSON output | **LLM Gateway** | output_schema required for every LLM call |

---

## 13. Open Questions

1. **Should LangFlow components be auto-generated from the domain model YAML, or require manual wiring?** Auto-generation simplifies adoption but risks over-constraining the visual editor experience.

2. **What is the fault-tolerance boundary for MCP tool failures?** When an MCP server (e.g., payment gateway) is unreachable, should the workflow queue the request for retry, fall back to a cached response, or escalate immediately?

3. **How do we version and rollback eval datasets in LangSmith?** Eval results may drift as domain models evolve — do we pin eval datasets to workflow version tags?

4. **Can the framework support non-Python LangGraph runtimes?** LangGraph.js is production-ready for TypeScript users; should the framework spec remain Python-only or define a runtime-agnostic abstraction layer?

5. **How are custom rule engines validated at registration time?** The YAML config specifies a module and class — should the framework enforce a contract check (interface compliance, smoke test) before accepting the engine?

6. **Should pycasbin policies be editable at runtime (hot-reload via database adapter) or only at deploy time (YAML → CSV generation)?** Hot-reload simplifies operations for large orgs but introduces consistency risk across instances.

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — framework architecture, permission model
- [Extraction Layer](./2026-06-17-extraction-layer-design.md) — rule engine integration in Validate node
- [Routing & Execution](./2026-06-17-routing-execution-layer-design.md) — rule engine in Decision nodes, tool system
- [Response Generation](./2026-06-17-response-generation-layer-design.md) — PII scrubbing, widget rendering
- [LangFlow](https://github.com/langflow-ai/langflow) — visual editor (150k stars, MIT)
- [LangGraph CLI](https://pypi.org/project/langgraph-cli/) — dev server + graph visualization
- [LangSmith Studio](https://docs.langchain.com/langsmith/studio) — debug + monitor IDE
- [transitions](https://github.com/pytransitions/transitions) — Python state machine library
- [durable_rules](https://github.com/jruizgit/rules) — Python forward-chaining rule engine
- [Presidio](https://github.com/microsoft/presidio) — Microsoft PII detection
