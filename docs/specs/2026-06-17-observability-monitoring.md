# Observability & Monitoring

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: Metrics collection, Grafana dashboards, alert rules, LangSmith integration, Prometheus metrics, audit log data source.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial observability spec |
| 2026-06-17 | 0.2.0 | Replace Grafana JSON with YAML schema; add Implementation Options |
| 2026-06-17 | 0.3.0 | Add LangFuse as Option B; all providers pluggable via ObservabilityProvider interface |

---

## 1. Role

Observability answers: **"Is the framework working correctly, right now?"** and **"What is the trend over time?"** Three pillars:

```
┌──────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY STACK                        │
├──────────────────┬──────────────────┬────────────────────────┤
│   LangSmith      │   Prometheus     │   Grafana              │
│   (Traces)       │   (Metrics)      │   (Dashboards/Alerts)  │
├──────────────────┼──────────────────┼────────────────────────┤
│  - LLM call      │  - Counters      │  - Overview panel      │
│    traces        │  - Gauges        │  - LLM Health panel    │
│  - Step-by-step  │  - Histograms    │  - Business Metrics    │
│    execution     │  - Summaries     │    panel               │
│  - Prompt        │                  │  - Alert rules         │
│    iteration     │                  │                        │
└──────────────────┴──────────────────┴────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     AUDIT LOG (PostgreSQL)                     │
│  Data source for Grafana — queryable, long-term retention     │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 What Observability Covers

- ✅ **Runtime metrics** — conversation volume, completion rate, error rates, latency
- ✅ **LLM-specific metrics** — token usage, schema validation failures, retry counts
- ✅ **Business metrics** — goal_check 422 rate, intent gap rate, abandonment rate
- ✅ **Dashboards** — Grafana panels for ops, engineering, and business teams
- ✅ **Alerts** — thresholds on error rates, latency, and 422 rates
- ✅ **Traces** — LangSmith for per-turn LLM call inspection, prompt debugging

### 1.2 What Observability Does NOT Cover

- ❌ **Application-level logging** — structured JSON logs (handled by Python logging → stdout → log aggregator)
- ❌ **Infrastructure monitoring** — CPU, memory, disk (handled by platform: Kubernetes, CloudWatch, Datadog)
- ❌ **Cost tracking** — LLM token costs (future: can be added as Prometheus counter)
- ❌ **User behavior analytics** — session replays, heatmaps (outside framework scope)

---

## 2. Metrics Collection

### 2.1 Metric Taxonomy

| Category | Metric | Type | Description |
|----------|--------|------|-------------|
| **Volume** | `conversations_created_total` | Counter | Total conversations created |
| **Volume** | `conversations_active` | Gauge | Currently active conversations |
| **Volume** | `messages_processed_total` | Counter | Total user messages processed |
| **Completion** | `conversations_completed_total` | Counter | Conversations reaching goal_met |
| **Completion** | `conversations_abandoned_total` | Counter | Conversations abandoned |
| **Completion** | `completion_rate` | Gauge | completed / (completed + abandoned) * 100 |
| **LLM** | `llm_call_latency_seconds` | Histogram | LLM call duration (p50, p95, p99) |
| **LLM** | `llm_call_total` | Counter | Total LLM calls |
| **LLM** | `llm_schema_violation_total` | Counter | Schema validation failures |
| **LLM** | `llm_retry_total` | Counter | Retry attempts (across all calls) |
| **LLM** | `llm_token_usage_total` | Counter | Total tokens consumed (by model) |
| **LLM** | `llm_escalation_total` | Counter | Escalation steps per from_tier→to_tier |
| **LLM** | `llm_retry_total` | Counter | Retries before escalation or success (by node_id, error_type) |
| **LLM** | `llm_tier_usage_ratio` | Gauge | Ratio: calls_on_this_tier / total_calls |
| **Error** | `error_rate` | Gauge | errorNode invocations / total turns * 100 |
| **Error** | `errorNode_invocations_total` | Counter | Total errorNode transitions |
| **Error** | `http_5xx_total` | Counter | HTTP 5xx responses from framework |
| **Business** | `goal_check_422_rate` | Gauge | goal_check returning 422 / total goal checks * 100 |
| **Business** | `intent_gap_total` | Counter | Intent classifier below confidence threshold |
| **Business** | `intent_gap_rate` | Gauge | intent gaps / total classifications * 100 |
| **Business** | `dangerous_operation_approvals_total` | Counter | Human approvals for dangerous ops |

### 2.2 Prometheus Exposition Format

```yaml
# framework.yaml
observability:
  metrics:
    enabled: true
    exposition:
      format: prometheus
      endpoint: /metrics
      port: 9090                     # separate port from MCP/REST
    
    collectors:
      conversations:
        - conversations_created_total
        - conversations_active
        - conversations_completed_total
        - conversations_abandoned_total
        - completion_rate
      
      llm:
        - llm_call_latency_seconds
        - llm_call_total
        - llm_schema_violation_total
        - llm_retry_total
        - llm_token_usage_total
        - llm_escalation_total
        - llm_tier_usage_ratio
      
      errors:
        - errorNode_invocations_total
        - http_5xx_total
        - error_rate
      
      business:
        - goal_check_422_rate
        - intent_gap_total
        - intent_gap_rate
        - dangerous_operation_approvals_total
    
    labels:
      global:
        - environment: "${ENV}"
        - service: "deterministic-workflow-framework"
        - version: "0.2.0"
      per_metric:
        llm_call_latency_seconds:
          - model
          - provider
        llm_token_usage_total:
          - model
          - direction           # input | output
        conversations_created_total:
          - workflow_id
```

### 2.3 Metric Implementation Strategy

```yaml
# Metrics are emitted at specific framework hooks
observability:
  hooks:
    on_conversation_create:
      - increment: conversations_created_total
        labels: { workflow_id: "{workflow_id}" }
      - set_gauge: conversations_active
        action: increment
    
    on_conversation_complete:
      - increment: conversations_completed_total
      - set_gauge: conversations_active
        action: decrement
    
    on_llm_call:
      - observe_histogram: llm_call_latency_seconds
        labels: { model: "{model}", provider: "{provider}" }
      - increment: llm_call_total
        labels: { model: "{model}" }
    
    on_schema_violation:
      - increment: llm_schema_violation_total
        labels: { model: "{model}", violation_type: "{type}" }
    
    on_retry:
      - increment: llm_retry_total
        labels: { node: "{node_name}", attempt: "{attempt_number}" }
    
    on_errorNode:
      - increment: errorNode_invocations_total
        labels: { strategy: "{strategy}", node: "{source_node}" }
    
    on_goal_check_422:
      - set_gauge: goal_check_422_rate
      - increment: goal_check_422_total
    
    on_intent_gap:
      - increment: intent_gap_total
        labels: { workflow_id: "{workflow_id}" }
```

---

## 3. Grafana Dashboard Layout

### 3.1 Overview Panel (Row 1)

```
┌─────────────────────────────────────────────────────────────────────┐
│  OVERVIEW                                     [dev] [Last 15 min ▼]  │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  Active      │  Created     │  Completed   │  Completion Rate       │
│  Convos      │  (today)     │  (today)     │                        │
│              │              │              │                        │
│     █ 42     │     █ 287    │     █ 201    │     ████░ 83.4%        │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
├─────────────────────────────────────────────────────────────────────┤
│  Conversations Over Time (line chart)                                │
│  300 ┤                                       ╭────                  │
│  200 ┤            ╭──────╮    ╭───╮         ╯                      │
│  100 ┤    ╭──────╯       ╰────╯   ╰──                               │
│    0 ┤────╯                                                         │
│      09:00  10:00  11:00  12:00  13:00  14:00  15:00  16:00         │
│      ── Created  ── Completed  ── Active (right axis)               │
├─────────────────────────────────────────────────────────────────────┤
│  Messages Processed (stat)                    Error Rate (gauge)     │
│     ██████████████████████ 12,847             █ 1.2%                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 LLM Health Panel (Row 2)

```
┌─────────────────────────────────────────────────────────────────────┐
│  LLM HEALTH                                   [dev] [Last 15 min ▼]  │
├─────────────────────────────────────────────────────────────────────┤
│  LLM Call Latency (heatmap / histogram)                              │
│  p50: 1.2s  |  p95: 3.8s  |  p99: 8.2s  |  Max: 12.4s              │
│                                                                      │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0-1s     │
│  ░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 1-3s     │
│  ░░░░░░░░░░░▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 3-5s     │
│  ░░░░░░░░▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5-10s    │
│  ░░░░░░▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 10s+     │
├─────────────────────────────────────────────────────────────────────┤
│  Schema Violations (stat)    │  Retries (stat)                       │
│     █ 47 (3.2%)              │     █ 23 / 1,452 calls                │
├─────────────────────────────────────────────────────────────────────┤
│  Token Usage (stacked bar, by model)                                 │
│  1.2M ┤ ░░░░░░░░░░░░░░░░░░                                           │
│  800k ┤ ░░░░░░░░░░░░░░░░░░  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓               │
│  400k ┤ ░░░░░░░░░░░░░░░░░░  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ░░░░░░░░    │
│      0 ┤─────────────────────────────────────────────────────────   │
│          gpt-4o              gpt-4o-mini             claude-sonnet   │
│          ░░ Input            ▓▓ Output                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Business Metrics Panel (Row 3)

```
┌─────────────────────────────────────────────────────────────────────┐
│  BUSINESS METRICS                             [dev] [Last 15 min ▼]  │
├─────────────────────────────────────────────────────────────────────┤
│  Goal Check 422 Rate (gauge)          Intent Gap Rate (gauge)        │
│      ██░░░░░░░ 18.3%                      ██░░░░░░░ 22.1%           │
│      ⚠ Threshold: 10%                    Threshold: 15%              │
├─────────────────────────────────────────────────────────────────────┤
│  Goal Check 422 Over Time (line)       Intent Gaps Over Time (line)  │
│  30% ┤   ╭╮                                                            │
│  20% ┤  ╭╯╰╮   ╭╮                                                      │
│  10% ┤──╯  ╰───╯╰────                                                  │
│   0% ┤────────────────                                                 │
│      09:00    10:00    11:00    12:00    13:00    14:00    15:00       │
│      ── 422 Rate   - - Threshold (10%)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Dangerous Operation Approvals (stat)                                 │
│     Approved: █ 12    │    Denied: █ 2    │    Pending: ░ 0       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Grafana Dashboard Schema (Provisioning)

Dashboards are provisioned declaratively. The YAML schema below defines the structure; actual Grafana JSON is generated from this schema at deploy time.

```yaml
# Grafana dashboard schema — generated into JSON at provision time
dashboard_schema:
  uid: string                          # unique dashboard identifier
  title: string                        # display title
  tags: string[]                       # organization tags
  refresh_interval: string             # e.g. "30s", "1m"
  time_range:
    from: string                       # default: "now-15m"
  
  rows:
    - name: string                     # row label (e.g. "Overview", "LLM Health")
      panels:
        - title: string                # panel title
          type: stat | gauge | graph | heatmap | table
          width: 1..24                 # grid columns (Grafana 24-col grid)
          height: 1..20                # grid rows
          x: 0..23
          y: 0..N
          
          targets:
            - query: string            # PromQL expression or SQL query
              legend: string           # legend label
          
          thresholds:                  # for stat/gauge panels
            - value: number | null
              color: green | yellow | orange | red
          
          unit: string                 # e.g. "percent", "seconds", "short"
          
          overrides:                   # per-series overrides (optional)
            - alias: string
              color: string
              fill: number             # 0-10

  variables:                           # dashboard template variables (optional)
    - name: string                     # e.g. "environment"
      type: custom | query | datasource
      default: string
      options: string[]

  datasources:
    - name: string                     # e.g. "Prometheus", "PostgreSQL-Audit"
      type: prometheus | postgres | elasticsearch
      uid: string                      # datasource UID in Grafana config
```

**Pre-built dashboard templates:**

| Dashboard | Panels | Data Source | Refresh |
|-----------|--------|-------------|---------|
| Overview | Active convos (stat), created/completed (stat), completion rate (gauge), convos over time (graph), messages processed (stat), error rate (gauge) | Prometheus | 30s |
| LLM Health | Latency heatmap (histogram), p50/p95/p99 (stat), schema violations (stat), retries (stat), token usage stacked bar (graph) | Prometheus | 30s |
| Business Metrics | Goal check 422 rate (gauge), intent gap rate (gauge), 422 over time (graph), intent gaps over time (graph), dangerous op approvals (stat) | Prometheus | 30s |
| Audit Trail | State distribution (pie), state transition timeline (table), conversation detail drill-down (table) | PostgreSQL | 1m |

---

## 4. Alert Rules

### 4.1 Alert Thresholds

| Alert | Condition | Severity | Channel | Runbook |
|-------|-----------|----------|---------|---------|
| **High Error Rate** | `error_rate > 5%` for 5 min | Critical | PagerDuty / Slack #alerts | Check errorNode logs, LLM provider status |
| **LLM Latency Spike** | `llm_call_latency_seconds:p95 > 5s` for 5 min | Warning | Slack #llm-ops | Check LLM provider status page, consider failover |
| **High 422 Rate** | `goal_check_422_rate > 10%` for 5 min | Warning | Slack #product | Review intent classifier accuracy, check gap threshold config |
| **Schema Violation Spike** | `rate(llm_schema_violation_total[5m]) > 20/min` | Warning | Slack #llm-ops | Check prompt templates, LLM model behavior change |
| **No Active Conversations** | `conversations_active == 0` for 10 min | Info | Slack #oncall | Verify deployment health, check MCP server status |
| **Completion Rate Drop** | `completion_rate < 50%` for 15 min | Warning | Slack #product | Review goal_check behavior, check for breaking workflow changes |
| **High Escalation Rate** | `rate(llm_escalation_total[5m]) > 2` | Warning | Slack #llm-ops | LLM frequently falling back to larger models — check small model health |
| **Retry Storm** | `rate(llm_retry_total[5m]) > 10` | Critical | PagerDuty / Slack #llm-ops | Excessive LLM retries — possible provider outage or model misconfiguration |

### 4.2 Alert Rule Schema

Alert rules are defined declaratively. The schema below describes the structure; actual Prometheus rule YAML or provider-specific configuration is generated at deploy time.

```yaml
# Alert rule schema — generated into provider-native format at deploy time
alert_rule_schema:
  name: string                          # unique alert name (e.g. "HighErrorRate")
  severity: critical | warning | info
  condition:
    metric: string                      # Prometheus metric name or provider metric
    operator: gt | lt | gte | lte | eq
    threshold: number
    duration: string                    # e.g. "5m", "10m" — condition must persist
    rate_window?: string                # for rate-based conditions, e.g. "5m"
  labels:
    service: string
    environment: string
    team?: string                       # owning team for routing
  annotations:
    summary: string                     # short description (e.g. "Error rate exceeds 5%")
    description_template: string        # template with {{ $value }}, {{ $labels.xxx }}
    runbook_url?: string                # link to troubleshooting guide
  notification:
    channels:                           # one or more delivery targets
      - type: pagerduty | slack | email | webhook
        routing_key?: string
        webhook_url?: string
        channel?: string                # Slack channel, if type=slack
        repeat_interval?: string        # e.g. "5m", "15m", "1h"
```

**Alert rules summary (derived from above schema):**

| Alert | Condition | Severity | Duration |
|-------|-----------|----------|----------|
| HighErrorRate | `errorNode_invocations / messages_processed > 5%` | critical | 5m |
| LLMLatencySpike | `p95 latency > 5s` | warning | 5m |
| HighGoalCheck422Rate | `goal_check_422_rate > 10%` | warning | 5m |
| SchemaViolationSpike | `schema_violations > 20/min` | warning | 5m |
| NoActiveConversations | `conversations_active == 0` | info | 10m |
| CompletionRateDrop | `completion_rate < 50%` | warning | 15m |
| HighEscalationRate | `rate(llm_escalation_total[5m]) > 2` | warning | 5m |
| RetryStorm | `rate(llm_retry_total[5m]) > 10` | critical | 5m |

### 4.3 Alert Routing

```yaml
# alertmanager/config.yaml
route:
  receiver: default
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      repeat_interval: 5m
    
    - match:
        severity: warning
      receiver: slack_llm_ops
      repeat_interval: 15m
    
    - match:
        severity: info
      receiver: slack_oncall
      repeat_interval: 1h

receivers:
  - name: pagerduty
    pagerduty_configs:
      - routing_key: "${PAGERDUTY_ROUTING_KEY}"
        severity: critical
        description: "{{ .CommonAnnotations.description }}"

  - name: slack_llm_ops
    slack_configs:
      - api_url: "${SLACK_LLM_OPS_WEBHOOK}"
        channel: "#llm-ops"
        title: "{{ .CommonLabels.alertname }}"
        text: "{{ .CommonAnnotations.description }}"

  - name: slack_oncall
    slack_configs:
      - api_url: "${SLACK_ONCALL_WEBHOOK}"
        channel: "#oncall"
```

---

## 5. Integration Architecture

### 5.1 LangSmith — Traces & Debugging

```
LangSmith Role: Per-turn execution traces, prompt debugging, eval datasets.

Framework → LangSmith:
  - Every LLM call (via LLM Gateway) → LangSmith trace
  - Every user turn (Layer 1→2→3 pipeline) → LangSmith run
  - Schema violations + retries → LangSmith span with error metadata
  - eval runs (from CI/CD) → LangSmith experiment
```

```yaml
observability:
  langsmith:
    enabled: true
    api_key: "${LANGSMITH_API_KEY}"
    project: "deterministic-workflow-${ENV}"
    
    tracing:
      auto_trace: true
      trace_all_llm_calls: true
      trace_workflow_runs: true
      sample_rate: 1.0            # 1.0 = trace all in prod; lower for high-volume
    
    tags:
      - environment: "${ENV}"
      - service: "deterministic-workflow-framework"
      - version: "0.2.0"
    
    metadata:
      include_user_id: true        # append user_id to all traces
      include_conversation_id: true
      include_workflow_id: true
      mask_pii: true               # scrub PII before sending to LangSmith
```

### 5.2 Prometheus — Metrics Collection

```
Prometheus Role: Numeric time-series metrics, alert evaluation.

Framework → Prometheus:
  - /metrics endpoint exposes counters, gauges, histograms
  - Prometheus scrapes every 15s (dev) / 30s (prod)
  - Alert rules evaluated by Prometheus → Alertmanager
```

```yaml
# prometheus/prometheus.yaml
scrape_configs:
  - job_name: "deterministic-workflow"
    scrape_interval: 15s
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          environment: "${ENV}"
          service: "deterministic-workflow-framework"
    
    # Per-instance in multi-instance deployments
    # - targets: ["instance-1:9090", "instance-2:9090"]
    #   labels:
    #     environment: "prod"
```

### 5.3 Grafana — Dashboards & Visualization

```
Grafana Role: Dashboards, visual alerting, team-facing views.

Data sources:
  - Prometheus (metrics)
  - PostgreSQL (audit logs)
  - LangSmith API (trace search — optional panel)
```

```yaml
# grafana/datasources.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: PostgreSQL-Audit
    type: postgres
    access: proxy
    url: "${AUDIT_DB_HOST}:5432"
    database: audit_logs
    user: grafana_reader
    secureJsonData:
      password: "${GRAFANA_DB_PASSWORD}"
    jsonData:
      sslmode: "require"
```

### 5.4 Audit Log as Grafana Data Source

```yaml
# Audit log table schema for Grafana queries
audit_log_grafana_view:
  table: lifecycle_audit_log
  columns:
    - timestamp: timestamptz
    - conversation_id: text
    - user_id: text
    - previous_state: text
    - new_state: text
    - trigger: text
    - turn_number: integer
  
  # Example Grafana panel query for conversation state distribution
  queries:
    state_distribution: >
      SELECT new_state, COUNT(*) as count
      FROM lifecycle_audit_log
      WHERE timestamp > NOW() - INTERVAL '24 hours'
      GROUP BY new_state
    
    state_transition_timeline: >
      SELECT timestamp, new_state
      FROM lifecycle_audit_log
      WHERE conversation_id = '${conversation_id}'
      ORDER BY timestamp ASC
```

---

## 6. Observability Configuration

### 6.1 Full YAML Configuration

```yaml
# framework.yaml — complete observability section
observability:
  enabled: true
  
  metrics:
    enabled: true
    endpoint: /metrics
    port: 9090
    
    collectors:
      conversations: true
      llm: true
      errors: true
      business: true
    
    prometheus:
      scrape_interval_seconds: 15
    
    labels:
      global:
        service: "deterministic-workflow-framework"
        version: "0.2.0"
  
  langsmith:
    enabled: true
    api_key: "${LANGSMITH_API_KEY}"
    project: "deterministic-workflow-${ENV}"
    trace_all_llm_calls: true
    trace_workflow_runs: true
    mask_pii: true
  
  grafana:
    dashboards:
      auto_provision: true
      config_path: /etc/grafana/provisioning/dashboards/
      dashboards:
        - overview
        - llm_health
        - business_metrics
    datasources:
      - prometheus
      - postgresql_audit
  
  alerts:
    enabled: true
    rules_file: alerts.yaml
    prometheus_alertmanager_url: "${ALERTMANAGER_URL}"
  
  audit_log:
    enabled: true
    backend: postgresql
    dsn: "${AUDIT_LOG_DSN}"
    retention_days: 365
    grafana_datasource: true       # expose as Grafana data source
```

---

## 7. Implementation Options

All observability providers are pluggable via the `ObservabilityProvider` interface — same pattern as rule engines and LLM providers. Choose one per environment:

```yaml
# framework.yaml
observability:
  provider: grafana_prometheus    # grafana_prometheus | langfuse | datadog | opentelemetry
```

### 7.1 Option A: Grafana + Prometheus (Self-Hosted OSS)

Self-hosted open-source stack. Prometheus scrapes the framework's `/metrics` endpoint; Grafana renders dashboards and evaluates alert rules via Alertmanager.

| Aspect | Detail |
|--------|--------|
| Strengths | No vendor lock-in; zero licensing cost; rich community dashboards; direct PromQL access; GitOps-friendly (dashboards as code) |
| Weaknesses | Operational burden (run and maintain Prometheus, Grafana, Alertmanager); storage scaling (Prometheus TSDB); no built-in log aggregation; multi-cluster federation is complex |
| Best for | Teams with existing Kubernetes/Prometheus infrastructure; cost-sensitive deployments; open-source-first organizations |

### 7.2 Option B: LangFuse (LLM-Specific Observability)

Open-source LLM observability platform focused on tracing, prompt management, and evaluation. Designed specifically for LLM applications — captures LLM calls, token usage, cost, and latency out of the box.

```yaml
# framework.yaml
observability:
  provider: langfuse
  langfuse:
    public_key: "${LANGFUSE_PUBLIC_KEY}"
    secret_key: "${LANGFUSE_SECRET_KEY}"
    host: "https://cloud.langfuse.com"   # cloud | self-hosted
    tracing:
      enabled: true
      sample_rate: 1.0
    prompt_management:
      enabled: true                      # version and track prompts
    evaluation:
      enabled: true                      # run evals from evals-create skill
    cost_tracking:
      enabled: true                      # per-model, per-conversation token cost
    metrics:
      llm_latency: true                  # p50/p95/p99 per model
      token_usage: true                  # prompt + completion tokens
      cost: true                         # estimated USD cost
      completion_rate: true              # goal_check pass rate
      error_rate: true                   # schema violations, retry rate
```

| Aspect | Detail |
|--------|--------|
| Strengths | Purpose-built for LLM apps; zero-config LLM tracing (auto-instruments OpenAI/Anthropic calls); prompt versioning and A/B testing; built-in eval runner; open-source with self-host option |
| Weaknesses | Not a general observability platform (no infra metrics, no APM); dashboarding less flexible than Grafana; smaller community than Datadog/Prometheus |
| Best for | LLM-centric teams; prompt engineering workflows; eval-driven development; cost-conscious deployments |

### 7.3 Option C: Datadog (SaaS APM)

SaaS observability platform. The framework emits metrics, traces, and logs to the Datadog agent; dashboards and alerts are configured in the Datadog UI or via Terraform/dd-agent YAML.

```yaml
# framework.yaml — Datadog integration
observability:
  provider: datadog
  datadog:
    api_key: "${DD_API_KEY}"
    site: "${DD_SITE:-datadoghq.com}"
    metrics:
      enabled: true
      statsd_port: 8125
      dogstatsd: true
    tracing:
      enabled: true
      agent_host: "${DD_AGENT_HOST}"
    logs:
      enabled: true
      intake_url: "https://http-intake.logs.${DD_SITE}"
    dashboards:
      auto_provision: true          # Terraform-managed or API-driven
    monitors:                       # Datadog-native alert definitions
      - name: "High Error Rate"
        type: metric alert
        query: "avg:error_node.invocations.rate{*} > 5"
        message: "Error rate exceeded 5% — check @llm-ops"
        tags: ["service:deterministic-workflow", "env:${ENV}"]
```

| Aspect | Detail |
|--------|--------|
| Strengths | Fully managed; unified metrics/logs/traces in one platform; rich APM; built-in anomaly detection; no infrastructure to maintain |
| Weaknesses | Per-host pricing can be expensive at scale; vendor lock-in; custom metrics cost extra; data residency concerns for regulated industries |
| Best for | Teams without dedicated observability infra; organizations already on Datadog; rapid setup with minimal ops |

### 7.4 Option D: OpenTelemetry (Vendor-Neutral)

The framework instruments with the OpenTelemetry SDK (traces, metrics, logs). An OTel Collector receives and exports telemetry to the backend(s) of choice — Prometheus, Datadog, Grafana Cloud, or any OTLP-compatible backend.

```yaml
# framework.yaml — OpenTelemetry integration
observability:
  provider: opentelemetry
  otel:
    exporter:
      protocol: otlp | grpc | http
      endpoint: "${OTEL_EXPORTER_OTLP_ENDPOINT}"
    traces:
      enabled: true
      sampler: parentbased_traceidratio
      sample_rate: 1.0
    metrics:
      enabled: true
      export_interval_ms: 15000
      prometheus_exporter: true      # also expose /metrics for local scraping
    logs:
      enabled: true
      log_level: info
    resource:
      service.name: "deterministic-workflow-framework"
      service.version: "0.2.0"
      deployment.environment: "${ENV}"
```

| Aspect | Detail |
|--------|--------|
| Strengths | Vendor-neutral standard (CNCF); swap backends without code changes; growing ecosystem; future-proof instrumentation investment |
| Weaknesses | OTel is still maturing (metrics SDK stable, logs SDK experimental); added collector component to run; fewer turnkey dashboards than native solutions |
| Best for | Multi-cloud or multi-vendor strategy; teams planning backend migrations; organizations standardizing on OTel |

### 7.5 Comparison Matrix

| Dimension | Option A (Grafana+Prometheus) | Option B (LangFuse) | Option C (Datadog) | Option D (OpenTelemetry) |
|-----------|------------------------------|---------------------|--------------------|--------------------------|
| Focus | General infrastructure | LLM-specific | General APM | Vendor-neutral standard |
| LLM auto-instrumentation | Manual setup | ✅ Built-in | Requires custom spans | Via OTel SDK |
| Prompt management | ❌ | ✅ Versioning + A/B | ❌ | ❌ |
| Eval runner | ❌ | ✅ Built-in | ❌ | ❌ |
| Cost tracking | Manual | ✅ Per-model/call | Via custom metrics | Via OTel metrics |
| Vendor lock-in | None (OSS) | Low (OSS self-host option) | High (proprietary) | None (open standard) |
| Operational burden | High (self-hosted) | Medium (cloud or self-host) | Low (SaaS) | Medium (run Collector) |
| Dashboard richness | High | Medium (LLM-focused) | Very high | Dependent on backend |
| Best for | Infra + LLM combined | LLM-centric teams | Full-stack APM | Multi-cloud/vendor strategy |
| Self-host option | ✅ (all components) | ✅ | ❌ | ✅ (Collector + backend) |

---

## 8. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should the framework emit metrics directly to Prometheus (pull model) or push to a Prometheus Pushgateway for short-lived processes? | Architecture for serverless deployments |
| 2 | Should LLM token usage be tracked as a gauge (current cost this month) in addition to a counter (lifetime total)? | Cost visibility for budget-conscious teams |
| 3 | Should Grafana dashboards include user-specific data (per-user_id conversation state) or only aggregate views? | Privacy and data exposure |
| 4 | How should the framework handle metric cardinality explosion from labels (e.g., `user_id` as a Prometheus label)? | Prometheus performance at scale |
| 5 | Should the framework expose a health check endpoint (`/healthz`) that Grafana, Kubernetes, and load balancers can consume? | Operations and deployment readiness |
| 6 | Should LangSmith trace IDs be injected into the audit log for cross-reference between traces and lifecycle events? | Debugability across tools |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — §4.3 LLM Output is JSON, §4.5 Audit Trail
- [LLM Gateway](./2026-06-17-llm-gateway.md) — Validation pipeline, retry budget, schema violations
- [Routing & Execution](./2026-06-17-routing-execution-layer-design.md) — errorNode strategy, retry budgets
- [Response Generation](./2026-06-17-response-generation-layer-design.md) — goal_check 422 rate, goal setter/checker
- [Conversation Lifecycle](./2026-06-17-conversation-lifecycle.md) — Lifecycle audit log, state transition metrics
- [Environment Config](./2026-06-17-environment-config.md) — Per-environment observability settings
- [Tool Ecosystem](./2026-06-17-tool-ecosystem.md) — LangSmith Studio, LangGraph CLI
- [CI/CD Pipeline](./2026-06-17-cicd-jenkins-pipeline.md) — Eval metrics tie into observability
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
