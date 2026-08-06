# 速率限制

> 属于 [Deterministic Workflow Framework — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：三个维度（用户、租户、工具）的速率限制策略、限制层级、YAML 配置、429 响应格式和 implement-interview 集成。

---

## 变更日志

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始速率限制规范：三维度限制、层级、YAML 配置、429 响应、访谈问题 |

---

## 1. 角色

速率限制保护框架免受滥用和过度使用。每个 API 端点、工具调用和 LLM 调用都必须受可配置的限制约束。这是一个规范层面的关注点——`implement-interview` 技能将在采用过程中询问用户其特定的限制。

```
Incoming Request
    │
    ▼
┌─────────────────────────────┐
│       速率限制器               │
│                               │
│  [用户限制检查]                │  ← 每用户：每个时间窗口的最大请求数
│  [租户限制检查]                │  ← 每租户：组织的聚合限制
│  [工具限制检查]                │  ← 每工具：每个工具有自己的预算
│                               │
│  所有检查通过？                 │
│    ├── 是 → 进入工作流
│    └── 否  → 429 + Retry-After
└─────────────────────────────┘
```

### 1.1 速率限制不涵盖的内容

- **LLM token 限制** → LLM 网关规范（提供商级别的速率限制）
- **认证 / 授权** → 认证令牌验证规范
- **节点级重试预算** → 路由与执行层规范 §6
- **并发限制（最大并行工作流数）** → 框架引擎配置
- **资源配额（CPU、内存）** → 部署 / 基础设施配置

---

## 2. 速率限制的三个维度

### 2.1 维度概述

| 维度 | 键 | 范围 | 目的 |
|-----------|-----|-------|---------|
| **每用户** | `user_id` | 单个已认证用户 | 防止单用户滥用；确保公平使用 |
| **每租户** | `tenant_id` | 组织 / 团队聚合 | 强制执行层级限制；防止噪声邻居 |
| **每工具** | `tool_name` | 单个工具（API、MCP、LLM） | 保护昂贵/慢速资源；成本控制 |

每次请求都会评估所有三个维度。如果任一维度超标，请求将被拒绝并返回 429。

### 2.2 每用户限制

```yaml
# framework.yaml
rate_limiting:
  dimensions:
    user:
      window: sliding              # fixed | sliding | token_bucket
      default:
        requests: 60               # 每分钟 60 个请求（典型聊天交互）
        window_sec: 60
      burst_multiplier: 2          # 允许突发最多为限制的 2 倍
```

每用户限制确保单个用户不能垄断资源。默认值（60 请求/分钟）对聊天交互来说足够宽松——典型对话有 10-30 轮。

### 2.3 每租户限制

```yaml
rate_limiting:
  dimensions:
    tenant:
      window: sliding
      tiers:
        default:
          requests: 600            # 租户内所有用户每分钟 600 个请求
          window_sec: 60
        premium:
          requests: 6000
          window_sec: 60
        enterprise:
          requests: 60000
          window_sec: 60
      # 租户限制在每用户限制之外单独执行。
      # 租户内的单个重度用户不会阻塞其他用户。
```

每租户限制强制执行组织购买的层级。即使单个用户在其每用户限制范围内，聚合租户限制也会限制总吞吐量。

### 2.4 每工具限制

```yaml
rate_limiting:
  dimensions:
    tool:
      window: token_bucket          # 工具首选 token_bucket（允许突发）
      default:
        requests: 100
        window_sec: 60
      tools:
        llm_call:                   # LLM 是最昂贵的资源
          requests: 30
          window_sec: 60
          window: token_bucket
          burst: 5                  # 允许 5 个并发 LLM 调用后进行速率限制
        claims_gateway_api:        # 危险操作获得更严格的限制
          requests: 10
          window_sec: 60
        vector_search_mcp:          # 搜索成本低，限制更高
          requests: 300
          window_sec: 60
        calculate_premium_api:      # 业务计算，适度限制
          requests: 100
          window_sec: 60
```

每工具限制保护昂贵或受速率限制的下游资源。LLM 调用是最昂贵的（无论是成本还是延迟），因此获得最严格的限制。理赔操作因安全和成本原因获得严格的限制。

### 2.5 联合执行

```
请求: user_id=alice, tenant_id=acme_corp, tool=llm_call

检查 1: user_id=alice
  当前: 25/60 → 通过

检查 2: tenant_id=acme_corp (default 层级)
  当前: 580/600 → 通过

检查 3: tool=llm_call
  当前: 28/30 → 通过

全部通过 → 请求继续处理

---

请求: user_id=bob, tenant_id=startup_inc, tool=claims_gateway_api

检查 1: user_id=bob
  当前: 10/60 → 通过

检查 2: tenant_id=startup_inc (default 层级)
  当前: 590/600 → 通过

检查 3: tool=claims_gateway_api
  当前: 10/10 → 失败（已达限制）

→ 429 Too Many Requests
```

---

## 3. 限制层级

### 3.1 层级定义

```yaml
# framework.yaml
rate_limiting:
  tiers:
    default:
      user:
        requests: 60
        window_sec: 60
      tenant:
        requests: 600
        window_sec: 60
      llm_calls_per_min: 30
      max_concurrent_workflows: 10
      tools:
        claims_gateway_api: { requests: 5, window_sec: 60 }
        vector_search_mcp: { requests: 100, window_sec: 60 }

    premium:
      user:
        requests: 120
        window_sec: 60
      tenant:
        requests: 6000
        window_sec: 60
      llm_calls_per_min: 100
      max_concurrent_workflows: 50
      tools:
        claims_gateway_api: { requests: 30, window_sec: 60 }
        vector_search_mcp: { requests: 500, window_sec: 60 }

    enterprise:
      user:
        requests: 300
        window_sec: 60
      tenant:
        requests: 60000
        window_sec: 60
      llm_calls_per_min: 500
      max_concurrent_workflows: 200
      tools:
        claims_gateway_api: { requests: 100, window_sec: 60 }
        vector_search_mcp: { requests: 2000, window_sec: 60 }

      # Enterprise 也可以定义自定义限制
      custom_limits_enabled: true
```

### 3.2 层级分配

层级由 `UserContext.tenant_id`（认证令牌验证规范 §2.3）确定，通过配置映射：

```yaml
# framework.yaml
rate_limiting:
  tenant_tier_mapping:
    source: config                     # config | database | external_api
    mappings:
      - tenant_id: acme_corp
        tier: enterprise
      - tenant_id: startup_inc
        tier: default
      - tenant_id: midmarket_co
        tier: premium
    default_tier: default              # 映射中未列出的租户获得 default 层级
```

### 3.3 层级对比

| 能力 | Default | Premium | Enterprise |
|-----------|---------|---------|------------|
| 用户请求/分钟 | 60 | 120 | 300 |
| 租户请求/分钟 | 600 | 6,000 | 60,000 |
| LLM 调用/分钟 | 30 | 100 | 500 |
| 并发工作流 | 10 | 50 | 200 |
| 理赔操作/分钟 | 5 | 30 | 100 |
| 自定义限制 | ❌ | ❌ | ✅ |

---

## 4. 速率限制算法

### 4.1 算法选择

```yaml
# framework.yaml
rate_limiting:
  algorithm:
    default: sliding_window          # 在准确性和内存之间取得最佳平衡
    options:
      fixed_window:
        description: "在窗口边界重置计数器（例如每 60 秒）"
        pros: ["简单", "低内存"]
        cons: ["边界突发——用户可以在窗口边界两侧达到 2 倍限制"]
      sliding_window:
        description: "以子窗口粒度追踪最近 N 秒内的请求"
        pros: ["平滑", "无边界突发", "良好的准确性"]
        cons: ["内存较高（存储时间戳）"]
        config:
          sub_window_sec: 10          # 在 60 秒窗口中有 6 个子窗口
      token_bucket:
        description: "令牌桶以速率 R 填充，每个请求消耗 1 个令牌。允许突发。"
        pros: ["自然的突发处理", "适合工具", "低内存"]
        cons: ["需要调整突发大小"]
        config:
          burst_size: 10              # 桶中最大令牌数
          refill_rate: 1              # 每秒填充令牌数
```

### 4.2 每维度算法覆盖

```yaml
rate_limiting:
  dimensions:
    user:
      algorithm: sliding_window       # 对用户平滑，无边界突发
    tenant:
      algorithm: sliding_window       # 同样适用于租户公平性
    tool:
      algorithm: token_bucket         # 工具受益于突发容量
```

---

## 5. 429 响应格式

### 5.1 HTTP 响应

当任何速率限制被超出时，框架返回：

```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 30
X-RateLimit-Limit-User: 60
X-RateLimit-Remaining-User: 0
X-RateLimit-Limit-Tenant: 600
X-RateLimit-Remaining-Tenant: 580
X-RateLimit-Limit-Tool: 10
X-RateLimit-Remaining-Tool: 0

{
  "error": "rate_limit_exceeded",
  "message": "请求过多。请在 30 秒后重试。",
  "details": {
    "exceeded_dimension": "tool",
    "exceeded_limit": "claims_gateway_api",
    "user_id": "bob",
    "tenant_id": "startup_inc",
    "current_usage": {
      "user": { "used": 10, "limit": 60, "remaining": 50 },
      "tenant": { "used": 590, "limit": 600, "remaining": 10 },
      "tool": { "used": 10, "limit": 10, "remaining": 0 }
    },
    "retry_after_sec": 30
  }
}
```

### 5.2 响应 Schema

```yaml
# 429 错误响应 schema
RateLimitResponse:
  error: string                          # 始终为 "rate_limit_exceeded"
  message: string                        # 人类可读的消息
  details:
    exceeded_dimension: user | tenant | tool
    exceeded_limit: string               # 触发了哪个具体限制
    user_id: string
    tenant_id: string
    current_usage:
      user:     { used: integer, limit: integer, remaining: integer }
      tenant:   { used: integer, limit: integer, remaining: integer }
      tool:     { used: integer, limit: integer, remaining: integer }
    retry_after_sec: integer
```

### 5.3 Retry-After 头部

`Retry-After` 值按所有超出维度中的最大等待时间计算：

```
Retry-After = max(
  user_window_sec - (now - user_window_start),     // 如果用户限制超出
  tenant_window_sec - (now - tenant_window_start), // 如果租户限制超出
  tool_window_sec - (now - tool_window_start)      // 如果工具限制超出
)
```

### 5.4 客户端指导

429 响应包含对客户端可操作的信息：

```yaml
# 429 响应体中的额外指导
rate_limit_response:
  client_action:
    recommended: "实施指数退避，从 Retry-After 秒开始"
    backoff_strategy:
      initial_delay: "{{retry_after_sec}}"
      multiplier: 2
      max_delay: 300
      jitter: true
```

---

## 6. 所有响应上的速率限制头部

即使在成功的响应中，框架也会发出速率限制头部，以便客户端可以自行节流：

```
# 每个响应中都包含（200、400 等）
X-RateLimit-Limit-User: 60
X-RateLimit-Remaining-User: 35
X-RateLimit-Reset-User: 1623456789

X-RateLimit-Limit-Tenant: 600
X-RateLimit-Remaining-Tenant: 20
X-RateLimit-Reset-Tenant: 1623456789

X-RateLimit-Limit-Tool: 30
X-RateLimit-Remaining-Tool: 2
X-RateLimit-Reset-Tool: 1623456789
```

### 6.1 头部 Schema

```yaml
# 所有响应上的标准速率限制头部
headers:
  X-RateLimit-Limit-{dimension}: integer        # 窗口内允许的最大请求数
  X-RateLimit-Remaining-{dimension}: integer    # 当前窗口内剩余的请求数
  X-RateLimit-Reset-{dimension}: integer        # 窗口重置的 Unix 时间戳
```

---

## 7. 存储后端

### 7.1 后端选项

```yaml
# framework.yaml
rate_limiting:
  storage:
    backend: redis                   # redis | memory | postgresql
    redis:
      host: "${REDIS_HOST}"
      port: 6379
      db: 1
      key_prefix: "ratelimit:"
      # 强烈推荐在生产环境中使用 Redis。
      # 内存后端仅用于开发（重启后丢失）。
    fallback: memory                 # 如果 Redis 不可达，回退到内存限制
```

| 后端 | 使用场景 | 权衡 |
|---------|----------|-----------|
| **Redis** | 生产环境 | 跨实例准确；持久化；支持 Lua 脚本进行原子检查 |
| **Memory** | 开发环境 / 单实例 | 零依赖；重启后丢失 |
| **PostgreSQL** | 无 Redis 可用时 | 准确；延迟高于 Redis |

### 7.2 Redis 键结构

```
# 每个维度的 Redis 键模式
ratelimit:user:{user_id}:{window_start_ts}       → 计数器
ratelimit:tenant:{tenant_id}:{window_start_ts}   → 计数器
ratelimit:tool:{tool_name}:{window_start_ts}     → 计数器
```

---

## 8. Implement-Interview 集成

### 8.1 角色

`implement-interview` 技能是一个引导式访谈，帮助采用者为其特定行业和用例配置框架。速率限制是该技能涵盖的配置域之一。

### 8.2 访谈问题

当 `implement-interview` 技能运行时，它会询问以下关于速率限制的问题：

| # | 问题 | 原因 |
|---|----------|-----|
| 1 | **您的预期月活跃用户数是多少？** | 确定基准租户限制 |
| 2 | **您是否提供分层定价（免费、专业、企业）？** | 映射到限制层级 |
| 3 | **系统中最昂贵的操作是什么？** | 识别哪个工具需要最严格的限制 |
| 4 | **您是否调用了有自身速率限制的第三方 API？** | 确保我们的限制比下游限制更严格 |
| 5 | **您的 LLM 提供商的速率限制是多少（每分钟请求数）？** | 设置 `llm_call` 工具限制 |
| 6 | **您需要每端点限制，还是每用户 + 每租户就足够了？** | 确定是否需要每工具维度 |
| 7 | **您的响应时间 SLA 是多少？** | 影响窗口大小和突发配置 |
| 8 | **您是否在有明确节流要求的受监管行业中运营？** | 可能需要更严格的限制和审计跟踪 |

### 8.3 从访谈答案生成配置

```yaml
# 示例：访谈输出 → 生成的配置
interview_answers:
  mau: 10000
  pricing_tiers: [free, pro, enterprise]
  most_expensive_operation: "LLM call to GPT-4o"
  third_party_limits: "Stripe: 100 req/s; GPT-4o: 500 req/min"
  llm_provider_limit: 500           # 每分钟请求数
  need_per_endpoint: true
  sla_ms: 2000
  regulated: true

# 生成的配置
rate_limiting:
  tiers:
    free:
      user: { requests: 30, window_sec: 60 }       # 足够宽松用于测试
      tenant: { requests: 300, window_sec: 60 }     # 小团队
    pro:
      user: { requests: 60, window_sec: 60 }
      tenant: { requests: 6000, window_sec: 60 }    # 中型组织
    enterprise:
      user: { requests: 300, window_sec: 60 }
      tenant: { requests: 60000, window_sec: 60 }   # 大型组织
  dimensions:
    tool:
      tools:
        llm_call: { requests: 400, window_sec: 60 } # 提供商限制的 80%
        stripe_api: { requests: 80, window_sec: 1 } # Stripe 限制的 80%
```

---

## 9. 绕过和覆盖

### 9.1 管理员绕过

某些角色可以出于运营原因绕过速率限制：

```yaml
# framework.yaml
rate_limiting:
  bypass:
    enabled: true
    roles: [admin, system]                  # 这些角色免于速率限制
    scopes: ["rate_limit:bypass"]           # OAuth scope 替代方案
    audit_bypass: true                      # 记录每次绕过以用于合规
```

### 9.2 每租户覆盖

Enterprise 租户可以协商自定义限制：

```yaml
rate_limiting:
  tenant_overrides:
    - tenant_id: large_enterprise_corp
      tier: enterprise
      overrides:
        user: { requests: 500, window_sec: 60 }
        tenant: { requests: 100000, window_sec: 60 }
        tools:
          llm_call: { requests: 800, window_sec: 60 }
```

### 9.3 紧急解除限制

用于运营紧急情况（事件响应、数据迁移），全局覆盖：

```yaml
rate_limiting:
  emergency_unlimit:
    enabled: false                         # 仅在事件期间设置为 true
    ttl_sec: 3600                          # 1 小时后自动禁用
    audit: true                            # 解除限制期间的每个请求都被审计
```

---

## 10. 待解决问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | 对于 premium/enterprise 层级，速率限制应该是硬执行（拒绝）还是软执行（队列 + 延迟处理）？ | 用户体验 vs 资源保护 |
| 2 | 框架是否应该支持动态速率限制（根据当前系统负载调整限制）？ | 自适应资源管理 |
| 3 | 速率限制应如何通过 A2A 链传播（Agent A → Agent B → Agent C — 哪个 agent 的限制适用）？ | 多 agent 公平性 |
| 4 | 速率限制计数器应该在实例间共享（Redis 集群）还是每实例（内存）+ 协调？ | 水平扩展 |
| 5 | 429 响应是否应该包含每个维度的 `Retry-After`，还是单个聚合值？ | 客户端重试逻辑的简洁性 |
| 6 | 对于 LLM 调用：速率限制应该以请求数还是 token 数来衡量？基于 token 的限制更公平但更难预测。 | LLM 成本控制 |
| 7 | 框架是否应该暴露 `/rate-limits` 端点，以便客户端无需发起请求即可查询其当前使用情况？ | 客户端自我感知 |

---

## 参考文献

- [高层设计](./01-deterministic-workflow-framework-design.md) — 框架架构
- [认证令牌验证](./16-auth-token-verification.md) — UserContext schema (§2.3)、tenant_id
- [LLM 网关](./14-llm-gateway.md) — LLM 调用契约
- [工具生态系统](./13-tool-ecosystem.md) — 工具注册和分类
- [路由与执行层](./06-routing-execution-layer-design.md) — 重试预算 (§6)、权限模型 (§7)
- [A2A 协议](./12-a2a-protocol.md) — 多 agent 速率限制传播（未来关注点）
- [响应生成](./08-response-generation-layer-design.md) — 422 错误格式（可比较的模式）
