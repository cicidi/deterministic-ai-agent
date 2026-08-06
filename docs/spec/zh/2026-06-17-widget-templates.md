# 组件模板

> 属于[确定性工作流框架 — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖：响应生成的两种组件模板策略 — A2A 聊天机器人模板（开源）和 Claude 生成组件（LLM 生成） — 组件类型、消息格式、主题配置、嵌入方式、组件模式以及 frontmatter 协议映射。

---

## Changelog

| 日期 | 版本 | 变更内容 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始组件模板规范：模板 A（开源聊天机器人 UI）、模板 B（Claude 生成组件）、frontmatter 集成 |

---

## 1. 角色定位

框架提供预构建的聊天机器人 UI，使开发者无需从零构建聊天界面。两种模板策略服务于不同的需求：

- **模板 A（A2A 聊天机器人模板）：** 预配置的开源聊天机器人 UI 外壳，开箱即用地渲染框架的 ResponseMessage 格式。这将成为 `home_insurance` 的聊天界面。
- **模板 B（Claude 生成组件）：** 由 Claude 根据模式描述生成的领域特定组件（保费计算器、保障对比表、保障细分图），并自动嵌入响应组件中。

```
响应生成（第三层）
    │
    ├── 纯文本消息模式 → 模板 A 渲染 markdown 文本
    │
    └── 组件模式 → 组件映射
                         │
                         ├── 内置组件 → 模板 A 渲染（保费卡片、风险仪表）
                         │
                         └── Claude 生成组件 → 模板 B：领域特定组件
                               （保费计算器、      （通过 frontmatter 协议嵌入）
                               保障对比表）
```

### 1.1 组件模板不涵盖的内容

- **响应生成逻辑** → 响应生成规范 §3
- **Frontmatter 组件协议细节** → 响应生成规范 §7
- **LLM 提示词构建** → LLM 网关规范
- **前端实现** → 本文档规范框架提供的内容，而非前端的构建方式
- **CSS/样式框架** → 推迟至实现阶段

---

## 2. 模板 A：A2A 聊天机器人模板

### 2.1 概念

模板 A 是一个预构建的开源聊天机器人 UI 外壳。它被配置为框架的默认 UI。开发者可以立即获得一个可用的聊天界面 — 他们只需配置主题和品牌，无需从零构建聊天。

**开源模板的选择标准：**

| 标准 | 要求 |
|-----------|-------------|
| 许可证 | MIT 或 Apache 2.0 |
| Star / 社区 | GitHub Star > 5k（维护活跃） |
| 框架 | React / Next.js（匹配常用前端技术栈） |
| 消息格式 | 兼容我们的 ResponseMessage 模式（响应生成规范 §3.2） |
| 组件渲染 | 支持嵌入 UI 组件（卡片、表格、按钮） |
| 主题化 | CSS 变量或主题提供器，支持白标 |
| 流式传输 | 支持流式文本（SSE 或 WebSocket） |
| 无障碍 | 最低 WCAG 2.1 AA |
| 包体积 | < 100KB gzipped |

### 2.2 架构

```
┌──────────────────────────────────────────────┐
│              聊天机器人模板                      │
│                                                │
│  ┌──────────────────────────────────┐         │
│  │         消息列表                    │         │
│  │  ┌────────────────────────────┐  │         │
│  │  │ 用户："我想要一份报价"         │  │         │
│  │  └────────────────────────────┘  │         │
│  │  ┌────────────────────────────┐  │         │
│  │  │ 代理：文本消息                │  │         │
│  │  │ ┌──────────────────────┐   │  │         │
│  │  │ │ [保费卡片组件]          │   │  │  ← 嵌入式组件
│  │  │ │  年付：$1,200         │   │  │
│  │  │ │  月付：$100           │   │  │
│  │  │ └──────────────────────┘   │  │         │
│  │  └────────────────────────────┘  │         │
│  └──────────────────────────────────┘         │
│                                                │
│  ┌──────────────────────────────────┐         │
│  │         输入区域                    │         │
│  │  [输入您的消息...] [发送]          │         │
│  └──────────────────────────────────┘         │
└──────────────────────────────────────────────┘
```

### 2.3 组件类型

模板必须支持以下内置组件类型。每种类型映射到 frontmatter 组件协议类型（响应生成规范 §7.1）：

| 组件类型 | 渲染形式 | Frontmatter `type` |
|---------------|-----------|-------------------|
| **文本消息** | Markdown 渲染文本，含链接、加粗、列表 | （仅使用 `text` 字段） |
| **卡片** | 带边框的卡片，包含标题、正文、可选页脚 | `premium_breakdown_card`, `coverage_comparison_table` |
| **表格** | 带表头的可排序数据表 | `coverage_comparison_table` |
| **仪表 / 计量器** | 带标签的可视化指示器（0-100） | `risk_score_gauge` |
| **按钮组** | 操作按钮行（确认、拒绝、修改） | `approval_buttons` |
| **进度追踪器** | 展示工作流进度的横向步进器 | `claim_status_tracker` |
| **文件上传** | 带类型约束的拖放区或文件选择器 | `document_upload_prompt` |
| **理赔收据** | 含理赔 ID 的收据卡片 | `claim_receipt` |
| **快捷回复** | 建议回复的横向芯片按钮 | ResponseMessage 中的 `actions` 字段 |

### 2.4 消息格式

模板直接消费框架的 `ResponseMessage` 格式。无需转换：

```yaml
# ResponseMessage — 由模板 A 直接消费
ResponseMessage:
  text: string                           # 主要文本（markdown），始终存在
  components: UIComponent[]              # 结构化组件（可选）
  actions: SuggestedAction[]             # 快捷回复 / 后续建议（可选）
  metadata:
    message_id: string
    timestamp: datetime
    workflow_id: string
    sensitive_data_scrubbed: boolean

# UIComponent — components 数组中的每个组件
UIComponent:
  type: string                           # 组件类型，来自 §2.3
  id: string                             # 唯一组件 ID，用于事件追踪
  data: object                           # 组件的结构化数据
  metadata:
    title: string                        # 显示标题
    description: string                  # 可选描述 / 提示文字
    collapsed: boolean                   # 初始折叠状态（用于次要信息）

# SuggestedAction — 快捷回复按钮
SuggestedAction:
  label: string                          # 按钮文本
  value: string                          # 点击后返回的值
  style: primary | secondary | danger
```

### 2.5 主题配置

模板支持白标化。主题配置为声明式：

```yaml
# framework.yaml — 聊天机器人 UI 主题配置
chatbot_ui:
  template: a2a_chatbot                    # 模板 A
  theme:
    # 颜色
    primary_color: "#1a73e8"               # 品牌主色（按钮、链接、强调色）
    secondary_color: "#5f6368"             # 次要文本、边框
    background_color: "#ffffff"            # 聊天背景
    surface_color: "#f8f9fa"              # 消息气泡背景
    error_color: "#d93025"                 # 错误消息、破坏性操作
    success_color: "#0f9d58"              # 成功确认

    # 排版
    font_family: "Inter, system-ui, sans-serif"
    font_size_base: "14px"
    font_size_heading: "18px"

    # 间距
    border_radius: "8px"
    message_spacing: "12px"

    # Logo
    logo_url: "https://cdn.example.com/logo.svg"
    favicon_url: "https://cdn.example.com/favicon.ico"

    # 字符串
    branding:
      app_name: "HomeInsurance"
      welcome_message: "您好！我可以帮您找到最佳的家庭保险方案。您需要什么？"
      placeholder_text: "输入您的消息..."
      send_button_label: "发送"
      error_generic: "出了点问题。请重试。"
      typing_indicator: "代理正在输入..."

  # 组件特定主题
  components:
    premium_card:
      highlight_color: "#e8f0fe"
      border_style: "solid"
    risk_gauge:
      low_color: "#0f9d58"
      medium_color: "#f9ab00"
      high_color: "#d93025"
    approval_buttons:
      confirm_style: primary
      decline_style: secondary
      modify_style: secondary
```

### 2.6 嵌入选项

```yaml
# framework.yaml — 聊天机器人 UI 的嵌入方式
chatbot_ui:
  embedding:
    mode: widget | standalone | iframe
    widget:
      mount_selector: "#home_insurance-chat"  # 挂载点的 CSS 选择器
      launcher:
        type: floating_button              # floating_button | inline
        position: bottom-right             # bottom-right | bottom-left
        icon: chat_bubble
        label: "需要帮助？"
    standalone:
      url: "/chat"                         # 独立页面
    iframe:
      width: "400px"
      height: "600px"
      origin_whitelist:
        - "https://partner-site.com"
```

| 模式 | 使用场景 |
|------|----------|
| **Widget** | 嵌入现有产品页面（角落气泡） |
| **Standalone** | `/chat` 独立聊天页面 |
| **Iframe** | 合作方站点的跨源嵌入 |

### 2.7 流式传输支持

```yaml
chatbot_ui:
  streaming:
    enabled: true
    protocol: sse                        # sse（服务器推送事件） | websocket
    sse:
      endpoint: "/api/chat/stream"
      event_types:
        - message_chunk                  # 流式文本 token
        - component_update               # 组件数据更新（如实时计算）
        - status_update                  # 工作流阶段变更
        - error                          # 流级错误
    render_strategy:
      text: typewriter                   # typewriter（打字机效果） | instant（即时展示）
      components: instant                # 组件到达后立即渲染
```

---

## 3. 模板 B：Claude 生成组件

### 3.1 概念

模板 B 是一种策略，而非固定代码库。对于领域特定需求（保费计算器、保障对比表、保障细分图），开发者描述组件模式，Claude 生成组件代码。生成的组件注册为框架组件，并自动嵌入响应中。

这是专门为 `home_insurance` — 家庭保险产品 — 设计的，标准保险组件（保费卡片、风险仪表）不适用。我们需要：
- 保费计算器（保障金额、房产价值、免赔额 → 月付保费）
- 保障对比表（提供商、保障类型、保费、免赔额、限额）
- 保障细分图
- 免赔额预估器
- 报价到期倒计时器

### 3.2 组件生成提示

开发者提供组件规范。Claude 生成组件代码：

```yaml
# 组件规范 — 开发者编写的内容
widget_spec:
  name: premium_calculator
  display_name: "保费计算器"
  description: "交互式计算器：保障金额、房产价值、免赔额 → 月付保费 + 年付保费"
  category: home_insurance

  inputs:
    - name: coverage_amount
      type: number
      label: "保障金额"
      min: 50000
      max: 5000000
      step: 10000
      default: 300000
    - name: property_value
      type: number
      label: "房产价值"
      min: 50000
      max: 10000000
      step: 10000
      default: 350000
    - name: deductible
      type: select
      label: "免赔额"
      options: [500, 1000, 2500, 5000]
      default: 1000

  outputs:
    - name: monthly_premium
      type: number
      label: "月付保费"
      format: currency
    - name: annual_premium
      type: number
      label: "年付保费"
      format: currency
    - name: total_coverage
      type: number
      label: "总保障金额"
      format: currency
    - name: policy_end_date
      type: date
      label: "保单到期日期"

  calculation:
    formula: "standard_premium_calc"
    # monthly_premium = (coverage_amount * base_rate) / 12
    # 其中 base_rate 取决于 property_value、deductible 和地区风险因素

  interaction:
    mode: live | submit             # live = 每次变更时重新计算；submit = 点击按钮后计算
    validation:
      - field: coverage_amount
        rule: "value >= 50000 AND value <= 5000000"
        message: "保障金额必须在 $50,000 到 $5,000,000 之间"
      - field: deductible
        rule: "value IN [500, 1000, 2500, 5000]"
        message: "免赔额必须是：$500、$1,000、$2,500、$5,000 之一"

  # --- Claude 提示上下文（不发送给用户）---
  # Claude 接收：widget_spec + framework component schema (§3.5) +
  #   "生成一个实现此组件规范的 React 组件。
  #    使用框架的 UIComponent 模式进行数据绑定。
  #    组件接收的 `data: object` 应与规范的 outputs 匹配。
  #    包含所有 `inputs` 的输入字段、实时计算逻辑和验证消息。
  #    输出单个 .tsx 文件。"
```

### 3.3 家庭保险组件目录

`home_insurance` 的所有组件，通过模板 B 生成：

| 组件 | 描述 | 输入 | 输出 |
|--------|-------------|--------|---------|
| `premium_calculator` | 交互式保费计算器 | coverage_amount, property_value, deductible | monthly_premium, annual_premium, total_coverage |
| `coverage_comparison_table` | 提供商横向对比 | coverage_amount, property_value, location | provider/premium/deductible/limits/monthly 表格 |
| `coverage_breakdown` | 保障细分图 | coverage_amount, property_value, deductible | 保障类别明细表 + 图表 |
| `deductible_estimator` | 预估免赔额影响 | coverage_amount, property_value, deductible | 免赔额选项 + 保费影响 |
| `quote_expiry_timer` | 报价到期倒计时 | quote_expiry_date | 倒计时、剩余天数、操作按钮 |
| `provider_recommendation_card` | 最优提供商推荐 | user_preferences, comparison_results | 推荐提供商、保费、理由、申请按钮 |

### 3.4 组件注册

生成的组件注册到框架的组件系统中：

```yaml
# framework.yaml — 注册 Claude 生成的组件
components:
  # 内置组件（来自响应生成规范 §7.1）
  premium_breakdown_card:
    type: widget
    built_in: true

  # 模板 B：Claude 生成组件
  premium_calculator:
    type: widget
    generated: true
    source: "widgets/premium_calculator.tsx"      # 由 Claude 生成
    spec: "specs/widgets/premium_calculator.yaml"  # 生成它的 widget_spec
    version: "1.0.0"
    generated_by: claude
    generated_date: "2026-06-17"

  coverage_comparison_table:
    type: widget
    generated: true
    source: "widgets/coverage_comparison_table.tsx"
    spec: "specs/widgets/coverage_comparison_table.yaml"
    version: "1.0.0"

  coverage_breakdown:
    type: widget
    generated: true
    source: "widgets/coverage_breakdown.tsx"
    spec: "specs/widgets/coverage_breakdown.yaml"
    version: "1.0.0"
```

### 3.5 用于 Claude 生成的组件模式

Claude 在生成组件时接收此模式契约：

```yaml
# Framework component contract — 作为生成上下文提供给 Claude
WidgetComponent:
  props:
    data: object                     # 与 widget_spec.outputs 匹配的结构化数据
    inputs: object                   # 当前输入值（用于 live/interactive 模式）
    onInputChange: function          # (field_name, value) → void
    onSubmit: function               # () → void（用于 submit 模式组件）
    theme: ThemeConfig               # 来自 §2.5 的 CSS 变量映射
    disabled: boolean                # 工作流终止时为 true

  # 必需的导出
  exports:
    default: React.FC<WidgetComponent.props>

  # 必需的样式
  styling:
    use_variables: true              # 使用主题 CSS 变量，而非硬编码颜色
    responsive: true                 # 移动端 + 桌面端
    accessible: true                 # WCAG 2.1 AA

  # 生命周期
  lifecycle:
    on_mount: "从 props.data 初始化（预填充值）"
    on_data_change: "使用新数据重新渲染（流式更新）"
    on_input_change: "调用 onInputChange 或更新本地状态（实时模式）"
    on_unmount: "清理定时器、订阅"
```

### 3.6 响应中自动嵌入

生成的组件通过组件映射系统（响应生成规范 §3.3 选项 B）自动嵌入响应中：

```yaml
# home_insurance 的每个工作流组件映射
widget_mapping:
  premium_calculation:
    outcome_key: "premium_calculation"
    condition: "outcomes.premium_calculation 存在时"
    component: premium_calculator
    required_fields: [monthly_premium, total_coverage]

  coverage_comparison:
    outcome_key: "coverage_comparison"
    condition: "outcomes.coverage_comparison 存在时"
    component: coverage_comparison_table
    required_fields: [providers]

  coverage_breakdown:
    outcome_key: "coverage_breakdown"
    condition: "outcomes.coverage_breakdown 存在时"
    component: coverage_breakdown

  deductible_estimate:
    outcome_key: "deductible_estimate"
    condition: "outcomes.deductible_estimate 存在时"
    component: deductible_estimator

  quote_expiry:
    outcome_key: "quote_expiry"
    condition: "outcomes.quote_expiry 存在时"
    component: quote_expiry_timer

  default_next_step:
    component: next_step_actions
    always: true
```

---

## 4. 组件如何映射到 Frontmatter 组件协议

### 4.1 映射关系

响应生成规范 §7 定义了 frontmatter 组件协议。本规范定义了模板 A 如何渲染它，以及模板 B 如何为它生成新的组件类型。

```
ResponseMessage（第三层输出）
    │
    ├── text: "这是您的家庭保险报价..."
    │     └── 模板 A：渲染为 markdown 消息气泡
    │
    └── components: [
          {
            type: "coverage_comparison_table",    ← 模板 B 生成了此组件
            metadata: { title: "您的保障方案" },
            data: { providers: [...] }           ← 来自第二层 outcomes
          }
        ]
          └── 模板 A：解析 type → 渲染 CoverageComparisonTable 组件
              模板 B：从 widget_spec 生成 CoverageComparisonTable.tsx
```

### 4.2 组件解析流程

```
1. ResponseMessage.components 到达模板 A
2. 模板 A 遍历 components[]
3. 对每个 component：
   a. 在已注册组件中查找 component.type
      - 内置组件（premium_breakdown_card, risk_score_gauge, ...）
      - 生成组件（premium_calculator, coverage_comparison_table, ...）
   b. 如果找到 → 使用 component.data + theme 渲染组件
   c. 如果未找到 → 回退：渲染为带原始数据表格的通用卡片
4. 将 component.metadata.title 渲染为卡片标题
5. 对次要信息应用 component.metadata.collapsed
```

### 4.3 模板 A + 模板 B 协同工作

```
┌──────────────────────────────────────────────────────┐
│                 家庭保险聊天                            │
│                                                        │
│  代理："这是您的保障方案："                              │
│  ┌──────────────────────────────────────────┐         │
│  │  您的保障方案                   （模板      │         │
│  │  ┌──────────┬────────┬──────────┬──────┐ │   A：    │
│  │  │ 提供商   │ 保费   │ 免赔额   │保额  │ │  卡片    │
│  │  ├──────────┼────────┼──────────┼──────┤ │  布局    │
│  │  │ABC 保险  │ $1,845 │ $1,000   │$350K │ │         │
│  │  │XYZ 保险  │ $1,812 │ $500     │$350K │ │         │
│  │  │ （模板 B：生成的组件）              │ │         │
│  │  └──────────┴────────┴──────────┴──────┘ │         │
│  │  [申请 XYZ 保险]  [查看详细信息]          │         │
│  └──────────────────────────────────────────┘         │
│                                                        │
│  ┌──────────────────────────────────────────┐         │
│  │  保费计算器                   （模板       │         │
│  │  保障金额：[$300,000]  房产价值：[$350K]   │  B：    │
│  │  免赔额：[$1,000 ▼]                        │ 组件    │
│  │  月付：$150  年付：$1,800                  │         │
│  └──────────────────────────────────────────┘         │
│                                                        │
│  [输入您的消息...]                              [发送] │
└──────────────────────────────────────────────────────┘
```

---

## 5. 组件生命周期

### 5.1 状态转换

```
组件生命周期：
  [已注册] → [已渲染] → [交互中] → [已完成]
       │            │            │            │
       │            │            │            └── 结果被工作流捕获
       │            │            └── 用户交互（输入、点击）
       │            └── 使用初始数据首次渲染
       └── 组件代码加载并验证通过
```

### 5.2 交互式组件事件

组件将事件发送回框架：

```yaml
# 组件事件契约
WidgetEvent:
  type: input_change | submit | action_click | close
  widget_id: string                        # 匹配 UIComponent.id
  payload: object                          # 事件特定数据
  timestamp: datetime

# 示例：用户提交保费计算器
widget_event:
  type: submit
  widget_id: "premium_calc_1"
  payload:
    coverage_amount: 350000
    property_value: 420000
    deductible: 1000
  timestamp: "2026-06-17T10:30:00Z"
```

框架将组件事件作为用户输入路由到工作流，与文本消息处理方式相同。工作流可以：
- 基于新输入重新计算
- 导航到新阶段
- 使用新数据更新组件

### 5.3 组件流式更新

对于长时间运行的计算，组件接收流式更新：

```yaml
# 组件更新的 SSE 事件流
events:
  - type: widget_update
    widget_id: "premium_calc_1"
    status: calculating
    progress: 0.5
  - type: widget_update
    widget_id: "premium_calc_1"
    status: completed
    data:
      monthly_premium: 145.83
      annual_premium: 1750.00
      total_coverage: 350000.00
```

---

## 6. 组件中的安全与 PII

### 6.1 数据流

```
第二层 outcome  →  PII 脱敏  →  组件数据  →  模板 A 渲染  →  用户屏幕
                       │
                 （响应生成 §8）
```

PII 脱敏（响应生成规范 §8）在数据到达组件之前对组件数据执行。组件永远不会接收原始 PII。

### 6.2 组件沙箱

Claude 生成的组件在沙箱环境中运行：

```yaml
# framework.yaml
widgets:
  sandbox:
    enabled: true
    restrictions:
      no_network: true                      # 组件不能发起 fetch/axios 调用
      no_dom_manipulation_outside_mount: true
      no_local_storage: true
      no_cookies: true
      no_eval: true
      max_render_time_ms: 5000              # 渲染超过 5 秒则终止组件
    csp:
      script_src: "'self'"                 # 禁止内联脚本
      style_src: "'self' 'unsafe-inline'"  # 允许 CSS 变量
```

---

## 7. 模板对比

| 维度 | 模板 A（聊天机器人 UI） | 模板 B（Claude 组件） |
|-----------|------------------------|---------------------------|
| **来源** | 开源项目（GitHub） | Claude 根据规范生成 |
| **提供内容** | 完整聊天 UI 外壳（消息列表、输入框、主题化） | 领域特定组件（计算器、表格、图表） |
| **使用时机** | 始终 — 这是默认 UI | 按领域使用：home_insurance 需要家庭保险组件 |
| **定制方式** | 主题配置（YAML）、品牌字符串 | 组件规范（YAML） → Claude 生成代码 |
| **维护方式** | 上游开源项目 | 框架升级时从规范重新生成 |
| **版本管理** | 固定到上游发布标签 | 在组件注册表中按组件版本化 |
| **测试方式** | 上游测试 + 框架集成测试 | 框架在注册时根据模式验证组件 |
| **回退方案** | 不适用（始终存在） | 对未知组件类型的通用卡片渲染器 |

---

## 8. 待定问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | 模板 A 应该是单一选定的开源项目，还是框架应支持多个聊天机器人 UI 的插件系统？ | 维护负担 |
| 2 | 模板 B：Claude 生成的组件应提交到仓库（静态）还是在构建时生成（动态）？ | 可复现性 vs 时效性 |
| 3 | 框架升级时如何管理组件版本？重新生成所有组件？人工审查？ | 升级安全性 |
| 4 | 交互式组件是否应支持撤销/重做（组件内的状态历史）？ | UX 复杂度 |
| 5 | 模板 A 是否应支持 WebSocket 进行双向流式传输（用户输入状态指示、实时组件更新）？ | 实时 UX |
| 6 | 模板 B：是否应支持非 React 组件（Vue、Svelte、Web Components）？ | 前端生态系统 |
| 7 | 如何向用户展示组件错误 — 在组件内联显示、回退到文本、还是错误提示？ | 错误 UX |
| 8 | 组件是否应支持 A/B 测试（同一数据的多个组件变体）？ | 产品实验 |

---

## References

- [高层设计](./01-deterministic-workflow-framework-design.md) — 框架架构、JSON 防护
- [响应生成层](./08-response-generation-layer-design.md) — ResponseMessage 模式（§3.2）、组件映射（§3.3 选项 B）、frontmatter 协议（§7）、PII 脱敏（§8）
- [LLM 网关](./14-llm-gateway.md) — LLM 调用契约（用于 Claude 生成）
- [工具生态系统](./13-tool-ecosystem.md) — 组件注册、LangFlow 集成
- [A2A 协议](./12-a2a-protocol.md) — A2A 聊天机器人模板命名参考
