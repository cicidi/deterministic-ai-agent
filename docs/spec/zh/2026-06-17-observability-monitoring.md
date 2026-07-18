# 可观测性与监控

> 属于 [确定性工作流框架 — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：指标采集、Grafana 仪表板、告警规则、LangSmith 集成、Prometheus 指标、审计日志数据源。

---

## 变更日志

| 日期 | 版本 | 变更内容 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始可观测性规范 |
| 2026-06-17 | 0.2.0 | 将 Grafana JSON 替换为 YAML 模式；新增"实施方案选项" |
| 2026-06-17 | 0.3.0 | 新增 LangFuse 作为方案 B；所有提供商通过 ObservabilityProvider 接口可插拔 |

---

## 1. 角色与职责

可观测性回答：**"框架当前是否正常工作？"**以及**"随时间变化的趋势如何？"** 三大支柱：

```
┌──────────────────────────────────────────────────────────────┐
│                     可观测性技术栈                               │
├──────────────────┬──────────────────┬────────────────────────┤
│   LangSmith      │   Prometheus     │   Grafana              │
│   （链路追踪）      │   （指标）         │   （仪表板/告警）         │
├──────────────────┼──────────────────┼────────────────────────┤
│  - LLM 调用      │  - 计数器         │  - 概览面板              │
│    链路追踪        │  - 仪表盘         │  - LLM 健康面板          │
│  - 逐步           │  - 直方图         │  - 业务指标              │
│    执行追踪        │  - 摘要           │    面板                  │
│  - 提示词迭代      │                  │  - 告警规则              │
└──────────────────┴──────────────────┴────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     审计日志 （PostgreSQL）                      │
│  Grafana 数据源 — 可查询，长期保留                              │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 可观测性覆盖范围

- ✅ **运行时指标** — 对话量、完成率、错误率、延迟
- ✅ **LLM 专属指标** — Token 用量、模式校验失败次数、重试次数
- ✅ **业务指标** — goal_check 422 比率、意图缺口比率、放弃率
- ✅ **仪表板** — 面向运维、工程和业务团队的 Grafana 面板
- ✅ **告警** — 基于错误率、延迟和 422 比率的阈值
- ✅ **链路追踪** — LangSmith 用于逐轮 LLM 调用检查和提示词调试

### 1.2 可观测性不覆盖范围

- ❌ **应用级日志** — 结构化 JSON 日志（由 Python logging → stdout → 日志聚合器处理）
- ❌ **基础设施监控** — CPU、内存、磁盘（由平台处理：Kubernetes、CloudWatch、Datadog）
- ❌ **成本追踪** — LLM Token 成本（未来：可作为 Prometheus 计数器添加）
- ❌ **用户行为分析** — 会话回放、热力图（超出框架范围）

---

## 2. 指标采集

### 2.1 指标分类

| 分类 | 指标 | 类型 | 描述 |
|----------|--------|------|-------------|
| **量级** | `conversations_created_total` | Counter | 已创建的对话总数 |
| **量级** | `conversations_active` | Gauge | 当前活跃对话数 |
| **量级** | `messages_processed_total` | Counter | 已处理的用户消息总数 |
| **完成** | `conversations_completed_total` | Counter | 达到 goal_met 的对话数 |
| **完成** | `conversations_abandoned_total` | Counter | 已放弃的对话数 |
| **完成** | `completion_rate` | Gauge | completed / (completed + abandoned) * 100 |
| **LLM** | `llm_call_latency_seconds` | Histogram | LLM 调用时长（p50、p95、p99） |
| **LLM** | `llm_call_total` | Counter | LLM 总调用次数 |
| **LLM** | `llm_schema_violation_total` | Counter | 模式校验失败次数 |
| **LLM** | `llm_retry_total` | Counter | 重试尝试次数（跨所有调用） |
| **LLM** | `llm_token_usage_total` | Counter | 已消费 Token 总数（按模型） |
| **错误** | `error_rate` | Gauge | errorNode 调用次数 / 总轮次 * 100 |
| **错误** | `errorNode_invocations_total` | Counter | errorNode 转换总数 |
| **错误** | `http_5xx_total` | Counter | 框架返回的 HTTP 5xx 响应数 |
| **业务** | `goal_check_422_rate` | Gauge | goal_check 返回 422 / goal check 总数 * 100 |
| **业务** | `intent_gap_total` | Counter | 意图分类器低于置信度阈值的次数 |
| **业务** | `intent_gap_rate` | Gauge | 意图缺口 / 总分类次数 * 100 |
| **业务** | `dangerous_operation_approvals_total` | Counter | 危险操作的人工审批次数 |

### 2.2 Prometheus 暴露格式

```yaml
# framework.yaml
observability:
  metrics:
    enabled: true
    exposition:
      format: prometheus
      endpoint: /metrics
      port: 9090                     # 与 MCP/REST 使用不同端口

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

### 2.3 指标实施策略

```yaml
# 指标在特定框架钩子处发出
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

## 3. Grafana 仪表板布局

### 3.1 概览面板（第 1 行）

```
┌─────────────────────────────────────────────────────────────────────┐
│  概览                                        [开发] [最近 15 分钟 ▼]   │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  活跃对话      │  已创建        │  已完成        │  完成率                  │
│              │  （今日）       │  （今日）       │                        │
│              │              │              │                        │
│     █ 42     │     █ 287    │     █ 201    │     ████░ 83.4%        │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
├─────────────────────────────────────────────────────────────────────┤
│  对话随时间变化（折线图）                                                │
│  300 ┤                                       ╭────                  │
│  200 ┤            ╭──────╮    ╭───╮         ╯                      │
│  100 ┤    ╭──────╯       ╰────╯   ╰──                               │
│    0 ┤────╯                                                         │
│      09:00  10:00  11:00  12:00  13:00  14:00  15:00  16:00         │
│      ── 已创建  ── 已完成  ── 活跃（右轴）                              │
├─────────────────────────────────────────────────────────────────────┤
│  已处理消息（统计值）                            错误率（仪表盘）          │
│     ██████████████████████ 12,847             █ 1.2%                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 LLM 健康面板（第 2 行）

```
┌─────────────────────────────────────────────────────────────────────┐
│  LLM 健康                                    [开发] [最近 15 分钟 ▼]   │
├─────────────────────────────────────────────────────────────────────┤
│  LLM 调用延迟（热力图 / 直方图）                                       │
│  p50: 1.2s  |  p95: 3.8s  |  p99: 8.2s  |  最大值: 12.4s            │
│                                                                      │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0-1s     │
│  ░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 1-3s     │
│  ░░░░░░░░░░░▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 3-5s     │
│  ░░░░░░░░▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5-10s    │
│  ░░░░░░▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 10s+     │
├─────────────────────────────────────────────────────────────────────┤
│  模式校验违规（统计值）           │  重试次数（统计值）                     │
│     █ 47 (3.2%)              │     █ 23 / 1,452 次调用               │
├─────────────────────────────────────────────────────────────────────┤
│  Token 用量（堆积柱状图，按模型划分）                                     │
│  1.2M ┤ ░░░░░░░░░░░░░░░░░░                                           │
│  800k ┤ ░░░░░░░░░░░░░░░░░░  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓               │
│  400k ┤ ░░░░░░░░░░░░░░░░░░  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ░░░░░░░░    │
│      0 ┤─────────────────────────────────────────────────────────   │
│          gpt-4o              gpt-4o-mini             claude-sonnet   │
│          ░░ 输入              ▓▓ 输出                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 业务指标面板（第 3 行）

```
┌─────────────────────────────────────────────────────────────────────┐
│  业务指标                                    [开发] [最近 15 分钟 ▼]   │
├─────────────────────────────────────────────────────────────────────┤
│  Goal Check 422 比率（仪表盘）         意图缺口比率（仪表盘）            │
│      ██░░░░░░░ 18.3%                      ██░░░░░░░ 22.1%           │
│      ⚠ 阈值：10%                        阈值：15%                     │
├─────────────────────────────────────────────────────────────────────┤
│  Goal Check 422 随时间变化（折线图）       意图缺口随时间变化（折线图）     │
│  30% ┤   ╭╮                                                            │
│  20% ┤  ╭╯╰╮   ╭╮                                                      │
│  10% ┤──╯  ╰───╯╰────                                                  │
│   0% ┤────────────────                                                 │
│      09:00    10:00    11:00    12:00    13:00    14:00    15:00       │
│      ── 422 比率   - - 阈值（10%）                                      │
├─────────────────────────────────────────────────────────────────────┤
│  危险操作审批（统计值）                                                    │
│     已批准：█ 12    │    已拒绝：█ 2    │    待处理：░ 0                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Grafana 仪表板模式（配置推送）

仪表板以声明式方式配置推送。以下 YAML 模式定义结构；实际 Grafana JSON 在部署时从此模式生成。

```yaml
# Grafana 仪表板模式 — 配置推送时生成 JSON
dashboard_schema:
  uid: string                          # 仪表板唯一标识符
  title: string                        # 显示标题
  tags: string[]                       # 组织标签
  refresh_interval: string             # 例如 "30s"、"1m"
  time_range:
    from: string                       # 默认："now-15m"

  rows:
    - name: string                     # 行标签（例如 "概览"、"LLM 健康"）
      panels:
        - title: string                # 面板标题
          type: stat | gauge | graph | heatmap | table
          width: 1..24                 # 网格列数（Grafana 24 列网格）
          height: 1..20                # 网格行数
          x: 0..23
          y: 0..N

          targets:
            - query: string            # PromQL 表达式或 SQL 查询
              legend: string           # 图例标签

          thresholds:                  # 用于 stat/gauge 面板
            - value: number | null
              color: green | yellow | orange | red

          unit: string                 # 例如 "percent"、"seconds"、"short"

          overrides:                   # 逐序列覆盖（可选）
            - alias: string
              color: string
              fill: number             # 0-10

  variables:                           # 仪表板模板变量（可选）
    - name: string                     # 例如 "environment"
      type: custom | query | datasource
      default: string
      options: string[]

  datasources:
    - name: string                     # 例如 "Prometheus"、"PostgreSQL-Audit"
      type: prometheus | postgres | elasticsearch
      uid: string                      # Grafana 配置中的数据源 UID
```

**预置仪表板模板：**

| 仪表板 | 面板 | 数据源 | 刷新频率 |
|-----------|--------|-------------|---------|
| 概览 | 活跃对话（统计值）、已创建/已完成（统计值）、完成率（仪表盘）、对话随时间变化（图表）、已处理消息（统计值）、错误率（仪表盘） | Prometheus | 30s |
| LLM 健康 | 延迟热力图（直方图）、p50/p95/p99（统计值）、模式校验违规（统计值）、重试次数（统计值）、Token 用量堆积柱状图（图表） | Prometheus | 30s |
| 业务指标 | Goal check 422 比率（仪表盘）、意图缺口比率（仪表盘）、422 随时间变化（图表）、意图缺口随时间变化（图表）、危险操作审批（统计值） | Prometheus | 30s |
| 审计追踪 | 状态分布（饼图）、状态转换时间线（表格）、对话详情下钻（表格） | PostgreSQL | 1m |

---

## 4. 告警规则

### 4.1 告警阈值

| 告警 | 条件 | 严重级别 | 通知渠道 | 操作手册 |
|-------|-----------|----------|---------|---------|
| **高错误率** | `error_rate > 5%` 持续 5 分钟 | 严重 | PagerDuty / Slack #alerts | 检查 errorNode 日志，LLM 提供商状态 |
| **LLM 延迟峰值** | `llm_call_latency_seconds:p95 > 5s` 持续 5 分钟 | 警告 | Slack #llm-ops | 检查 LLM 提供商状态页面，考虑故障切换 |
| **高 422 比率** | `goal_check_422_rate > 10%` 持续 5 分钟 | 警告 | Slack #product | 审查意图分类器准确度，检查缺口阈值配置 |
| **模式校验违规激增** | `rate(llm_schema_violation_total[5m]) > 20/min` | 警告 | Slack #llm-ops | 检查提示词模板，LLM 模型行为变化 |
| **无活跃对话** | `conversations_active == 0` 持续 10 分钟 | 信息 | Slack #oncall | 验证部署健康状态，检查 MCP 服务器状态 |
| **完成率下降** | `completion_rate < 50%` 持续 15 分钟 | 警告 | Slack #product | 审查 goal_check 行为，检查破坏性工作流变更 |

### 4.2 告警规则模式

告警规则以声明式方式定义。以下模式描述结构；实际 Prometheus 规则 YAML 或提供商特定配置在部署时生成。

```yaml
# 告警规则模式 — 部署时生成提供商原生格式
alert_rule_schema:
  name: string                          # 唯一告警名称（例如 "HighErrorRate"）
  severity: critical | warning | info
  condition:
    metric: string                      # Prometheus 指标名称或提供商指标
    operator: gt | lt | gte | lte | eq
    threshold: number
    duration: string                    # 例如 "5m"、"10m" — 条件必须持续满足
    rate_window?: string                # 用于基于速率条件的窗口，例如 "5m"
  labels:
    service: string
    environment: string
    team?: string                       # 负责团队
  annotations:
    summary: string                     # 简短描述（例如 "错误率超过 5%"）
    description_template: string        # 含 {{ $value }}、{{ $labels.xxx }} 的模板
    runbook_url?: string                # 故障排查指南链接
  notification:
    channels:                           # 一个或多个投递目标
      - type: pagerduty | slack | email | webhook
        routing_key?: string
        webhook_url?: string
        channel?: string                # Slack 频道（当 type=slack 时）
        repeat_interval?: string        # 例如 "5m"、"15m"、"1h"
```

**告警规则摘要（由上述模式派生）：**

| 告警 | 条件 | 严重级别 | 持续时间 |
|-------|-----------|----------|----------|
| HighErrorRate | `errorNode_invocations / messages_processed > 5%` | 严重 | 5m |
| LLMLatencySpike | `p95 latency > 5s` | 警告 | 5m |
| HighGoalCheck422Rate | `goal_check_422_rate > 10%` | 警告 | 5m |
| SchemaViolationSpike | `schema_violations > 20/min` | 警告 | 5m |
| NoActiveConversations | `conversations_active == 0` | 信息 | 10m |
| CompletionRateDrop | `completion_rate < 50%` | 警告 | 15m |

### 4.3 告警路由

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

## 5. 集成架构

### 5.1 LangSmith — 链路追踪与调试

```
LangSmith 角色：逐轮执行追踪、提示词调试、评估数据集。

框架 → LangSmith：
  - 每次 LLM 调用（通过 LLM 网关）→ LangSmith 追踪
  - 每次用户轮次（第 1 层→第 2 层→第 3 层管道）→ LangSmith 运行
  - 模式校验违规 + 重试 → 包含错误元数据的 LangSmith span
  - 评估运行（来自 CI/CD）→ LangSmith 实验
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
      sample_rate: 1.0            # 1.0 = 在 prod 中追踪所有；低流量环境可调低

    tags:
      - environment: "${ENV}"
      - service: "deterministic-workflow-framework"
      - version: "0.2.0"

    metadata:
      include_user_id: true        # 将 user_id 附加到所有追踪
      include_conversation_id: true
      include_workflow_id: true
      mask_pii: true               # 发送到 LangSmith 前擦除 PII
```

### 5.2 Prometheus — 指标采集

```
Prometheus 角色：数值时间序列指标、告警评估。

框架 → Prometheus：
  - /metrics 端点暴露计数器、仪表盘、直方图
  - Prometheus 每 15 秒（开发）/ 30 秒（生产）抓取
  - 告警规则由 Prometheus 评估 → Alertmanager
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

    # 多实例部署中的每实例配置
    # - targets: ["instance-1:9090", "instance-2:9090"]
    #   labels:
    #     environment: "prod"
```

### 5.3 Grafana — 仪表板与可视化

```
Grafana 角色：仪表板、可视化告警、面向团队的视图。

数据源：
  - Prometheus（指标）
  - PostgreSQL（审计日志）
  - LangSmith API（追踪搜索 — 可选面板）
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

### 5.4 审计日志作为 Grafana 数据源

```yaml
# Grafana 查询用的审计日志表模式
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

  # Grafana 面板查询示例（对话状态分布）
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

## 6. 可观测性配置

### 6.1 完整 YAML 配置

```yaml
# framework.yaml — 完整的可观测性部分
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
    grafana_datasource: true       # 暴露为 Grafana 数据源
```

---

## 7. 实施方案选项

所有可观测性提供商均通过 `ObservabilityProvider` 接口可插拔 — 与规则引擎和 LLM 提供商相同的模式。每个环境选择一项：

```yaml
# framework.yaml
observability:
  provider: grafana_prometheus    # grafana_prometheus | langfuse | datadog | opentelemetry
```

### 7.1 方案 A：Grafana + Prometheus（自托管开源）

自托管开源技术栈。Prometheus 抓取框架的 `/metrics` 端点；Grafana 渲染仪表板并通过 Alertmanager 评估告警规则。

| 方面 | 详情 |
|--------|--------|
| 优势 | 无厂商锁定；零许可费用；丰富的社区仪表板；直接 PromQL 访问；GitOps 友好（仪表板即代码） |
| 劣势 | 运营负担（运行和维护 Prometheus、Grafana、Alertmanager）；存储扩展（Prometheus TSDB）；无内置日志聚合；多集群联邦复杂 |
| 适用场景 | 已有 Kubernetes/Prometheus 基础设施的团队；成本敏感型部署；开源优先的组织 |

### 7.2 方案 B：LangFuse（LLM 专属可观测性）

开源 LLM 可观测性平台，专注于链路追踪、提示词管理和评估。专为 LLM 应用程序设计 — 开箱即用地捕获 LLM 调用、Token 用量、成本和延迟。

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
      enabled: true                      # 版本化和追踪提示词
    evaluation:
      enabled: true                      # 运行 evals-create 技能的评估
    cost_tracking:
      enabled: true                      # 按模型、按对话的 Token 成本
    metrics:
      llm_latency: true                  # 每个模型的 p50/p95/p99
      token_usage: true                  # prompt + completion tokens
      cost: true                         # 预估 USD 成本
      completion_rate: true              # goal_check 通过率
      error_rate: true                   # 模式校验违规、重试率
```

| 方面 | 详情 |
|--------|--------|
| 优势 | 专为 LLM 应用打造；零配置 LLM 追踪（自动插装 OpenAI/Anthropic 调用）；提示词版本化和 A/B 测试；内置评估运行器；开源且提供自托管选项 |
| 劣势 | 非通用可观测性平台（无基础设施指标，无 APM）；仪表板灵活度不如 Grafana；社区规模小于 Datadog/Prometheus |
| 适用场景 | LLM 核心团队；提示词工程工作流；评估驱动开发；成本敏感的部署 |

### 7.3 方案 C：Datadog（SaaS APM）

SaaS 可观测性平台。框架将指标、链路追踪和日志发送到 Datadog agent；仪表板和告警在 Datadog UI 中或通过 Terraform/dd-agent YAML 配置。

```yaml
# framework.yaml — Datadog 集成
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
      auto_provision: true          # Terraform 管理或 API 驱动
    monitors:                       # Datadog 原生告警定义
      - name: "High Error Rate"
        type: metric alert
        query: "avg:error_node.invocations.rate{*} > 5"
        message: "Error rate exceeded 5% — check @llm-ops"
        tags: ["service:deterministic-workflow", "env:${ENV}"]
```

| 方面 | 详情 |
|--------|--------|
| 优势 | 全托管；统一平台中的指标/日志/追踪一体化；丰富的 APM；内置异常检测；无需维护基础设施 |
| 劣势 | 按主机定价，规模较大时成本高昂；厂商锁定；自定义指标需额外费用；受监管行业可能存在数据驻留问题 |
| 适用场景 | 无专门可观测性基础设施的团队；已使用 Datadog 的组织；需要最小运维开销的快速部署 |

### 7.4 方案 D：OpenTelemetry（供应商中立）

框架使用 OpenTelemetry SDK 进行插装（链路追踪、指标、日志）。OTel Collector 接收遥测数据并将其导出到所选后端 — Prometheus、Datadog、Grafana Cloud 或任何兼容 OTLP 的后端。

```yaml
# framework.yaml — OpenTelemetry 集成
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
      prometheus_exporter: true      # 也暴露 /metrics 供本地抓取
    logs:
      enabled: true
      log_level: info
    resource:
      service.name: "deterministic-workflow-framework"
      service.version: "0.2.0"
      deployment.environment: "${ENV}"
```

| 方面 | 详情 |
|--------|--------|
| 优势 | 供应商中立标准（CNCF）；无需代码更改即可切换后端；生态系统不断发展；面向未来的插装投资 |
| 劣势 | OTel 仍在成熟中（指标 SDK 稳定，日志 SDK 实验性质）；需要额外的 collector 组件运行；开箱即用的仪表板少于原生解决方案 |
| 适用场景 | 多云或多供应商策略；计划后端迁移的团队；在 OTel 上标准化的组织 |

### 7.5 方案对比矩阵

| 维度 | 方案 A（Grafana+Prometheus） | 方案 B（LangFuse） | 方案 C（Datadog） | 方案 D（OpenTelemetry） |
|-----------|------------------------------|---------------------|--------------------|--------------------------|
| 专注领域 | 通用基础设施 | LLM 专属 | 通用 APM | 供应商中立标准 |
| LLM 自动插装 | 手动设置 | ✅ 内置 | 需自定义 span | 通过 OTel SDK |
| 提示词管理 | ❌ | ✅ 版本化 + A/B | ❌ | ❌ |
| 评估运行器 | ❌ | ✅ 内置 | ❌ | ❌ |
| 成本追踪 | 手动 | ✅ 按模型/调用 | 通过自定义指标 | 通过 OTel 指标 |
| 厂商锁定 | 无（开源） | 低（开源自托管选项） | 高（专有） | 无（开放标准） |
| 运营负担 | 高（自托管） | 中（云或自托管） | 低（SaaS） | 中（运行 Collector） |
| 仪表板丰富度 | 高 | 中（LLM 聚焦） | 非常高 | 取决于后端 |
| 适用场景 | 基础设施 + LLM 结合 | LLM 核心团队 | 全栈 APM | 多云/供应商策略 |
| 自托管选项 | ✅（所有组件） | ✅ | ❌ | ✅（Collector + 后端） |

---

## 8. 待解决问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | 框架应直接向 Prometheus 发送指标（拉取模式），还是向 Prometheus Pushgateway 推送（用于短生命周期进程）？ | 无服务器部署的架构 |
| 2 | LLM Token 用量应追踪为仪表盘（当月当前成本）还是计数器（生命周期累计）？ | 成本敏感团队的成本可见性 |
| 3 | Grafana 仪表板应包含用户特定数据（按 user_id 的对话状态）还是仅聚合视图？ | 隐私和数据暴露 |
| 4 | 框架应如何处理来自标签的指标基数爆炸（例如将 `user_id` 作为 Prometheus 标签）？ | 大规模 Prometheus 性能 |
| 5 | 框架应暴露 Grafana、Kubernetes 和负载均衡器可消费的健康检查端点（`/healthz`）吗？ | 运维和部署就绪 |
| 6 | LangSmith 追踪 ID 应注入审计日志中吗？以便在链路追踪和生命周期事件之间进行交叉引用？ | 跨工具可调试性 |

---

## 参考资料

- [高层设计](./01-deterministic-workflow-framework-design.md) — §4.3 LLM 输出为 JSON，§4.5 审计追踪
- [LLM 网关](./14-llm-gateway.md) — 校验管道，重试预算，模式校验违规
- [路由与执行](./06-routing-execution-layer-design.md) — errorNode 策略，重试预算
- [响应生成](./08-response-generation-layer-design.md) — goal_check 422 比率，目标设定器/检查器
- [对话生命周期](./07-conversation-lifecycle.md) — 生命周期审计日志，状态转换指标
- [环境配置](./18-environment-config.md) — 按环境的可观测性设置
- [工具生态](./13-tool-ecosystem.md) — LangSmith Studio，LangGraph CLI
- [CI/CD 管线](./19-cicd-jenkins-pipeline.md) — 评估指标集成到可观测性
- [Prometheus 文档](https://prometheus.io/docs/introduction/overview/)
- [Grafana 文档](https://grafana.com/docs/grafana/latest/)
- [LangSmith 文档](https://docs.smith.langchain.com/)
