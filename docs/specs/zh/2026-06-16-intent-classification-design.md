# 第1层：意图分类

> 属于 [确定性工作流框架 — 高层设计](./2026-06-16-deterministic-workflow-framework-design.md)
> 重点关注：UNDERSTAND 层中的意图分类。
> 所有具体的意图示例已提取到 [examples/home-insurance/](../../examples/home-insurance/)。

---

## 变更日志

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-16 | 0.1.0 | 初始意图分类规范 |
| 2026-06-16 | 0.2.0 | 将自定义意图示例提取到 examples/；修正章节编号 |
| 2026-06-17 | 0.3.0 | 添加实现方案对比、YAML schema、待解决问题、errorNode 交叉引用、agentState.phase 提及 |
| 2026-06-18 | 0.4.0 | IntentDef 新增 `complex` 字段；实现多意图检测（单条用户消息 → 多个意图）；意图组合验证规则；意图→payload 映射表 |
| 2026-06-18 | 0.5.1 | 简化 §2.4：移除方案A/B/C 对比表；仅保留 LLM + 关键词回退作为唯一策略 |
| 2026-06-18 | 0.5.0 | 系统意图从 8 个扩展至 17 个：移除 `resume_conversation`（降级为系统状态，非用户意图）；新增 `help`、`correction`、`chitchat`、`out_of_scope`、`repeat`、`escalate`、`restart`、`complaint`、`pause`、`ambiguous_request`；为所有系统意图添加关键词+示例 YAML 定义；扩展 §5.2 payload 映射至全部 17 个系统意图 |

---

## 1. 角色

意图分类回答的问题是：*"用户想要做什么？"*

它将自由形式的用户话语映射到预定义的意图标签，可选地附带置信度分数。输出结果由状态机（第2层）消费，用于确定有效的状态转换。

## 2. 意图模型

### 2.1 系统意图（内置）

以下 17 个系统意图对所有工作流可用。它们涵盖对话生命周期、错误恢复、任务消歧和社交互动——独立于任何产品领域。

| 分类 | Intent | 描述 | Complex |
|----------|--------|-------------|---------|
| **对话生命周期** | `start_conversation` | 用户发起新对话 | false |
| | `finish_conversation` | 用户希望结束对话 | false |
| | `pause` | 用户要求暂停或等待（"等一下"、"稍等"） | false |
| | `restart` | 用户希望从头开始当前工作流 | false |
| **信息交换** | `ask_question` | 用户询问信息或解释 | false |
| | `provide_information` | 用户响应提示提供数据 | false |
| | `repeat` | 用户要求机器人重复上一次回复 | false |
| **确认** | `confirm` | 用户同意或确认 | false |
| | `decline` | 用户不同意、取消或拒绝 | false |
| **错误与恢复** | `unrecognized_intent` | 无法确定意图（低置信度回退） | false |
| | `correction` | 用户纠正之前的陈述——自己的或机器人的 | false |
| | `ambiguous_request` | 话语可映射到多个可能的意图；需要消歧 | false |
| | `out_of_scope` | 识别到请求但系统明确不支持 | false |
| **社交与元操作** | `help` | 用户询问系统能力或如何使用机器人 | false |
| | `chitchat` | 与任何任务无关的随意社交对话 | false |
| | `complaint` | 用户表达不满或提出投诉 | false |
| | `escalate` | 用户要求转接人工客服 | false |

> **所有系统意图均为 `complex: false`**——它们可以在单轮分类中相互自由组合，也可以与自定义意图组合（见 §4.3）。

#### 系统意图关键词与示例

框架的关键词回退机制（见 §3.4）依赖这些定义。每个系统意图包含用于确定性匹配的 `keywords` 列表和用于 LLM few-shot 提示的 `examples`。

```yaml
# 系统意图 — 内置于框架中
# 全部 complex: false；全部可与简单意图组合

system_intents:
  # ── 对话生命周期 ──
  - name: start_conversation
    description: 用户发起新对话
    keywords: [hello, hi, hey, good morning, good afternoon, greetings, what's up, 你好, 您好, 早上好]
    examples:
      - "Hello, I need help"
      - "Hi there"
      - "你好，我需要帮助"

  - name: finish_conversation
    description: 用户希望结束对话
    keywords: [bye, goodbye, that's all, done, no more questions, I'm finished, see you, thanks bye, 再见, 拜拜, 没了]
    examples:
      - "That's all I needed, thanks"
      - "Goodbye"
      - "没有了，谢谢"

  - name: pause
    description: 用户要求暂停或等待
    keywords: [wait, hold on, one moment, give me a second, pause, hang on, let me think, not ready, 等一下, 稍等, 等等]
    examples:
      - "Wait, let me check something"
      - "Hold on a moment"
      - "等一下，我查一下"

  - name: restart
    description: 用户希望从头开始当前工作流
    keywords: [start over, begin again, restart, from the beginning, reset, clear everything, new session, let's redo, 重新开始, 重来, 重置]
    examples:
      - "Let's start over"
      - "Can we begin again?"
      - "重新开始吧"

  # ── 信息交换 ──
  - name: ask_question
    description: 用户询问信息或解释
    keywords: [what is, how does, tell me about, explain, why, when did, where is, who is, can you tell, 什么是, 怎么, 解释, 为什么]
    examples:
      - "What is my deductible?"
      - "How does the claims process work?"
      - "我的免赔额是多少？"

  - name: provide_information
    description: 用户响应提示提供数据
    keywords: [my name is, my phone is, my address is, the number is, it's, here is, this is, 我叫, 我的电话是, 地址是]
    examples:
      - "My name is John"
      - "The address is 123 Main St"
      - "我叫张三"

  - name: repeat
    description: 用户要求机器人重复上一次回复
    keywords: [repeat, say that again, what did you say, come again, pardon, sorry what, can you repeat, once more, 再说一遍, 重复, 没听清]
    examples:
      - "Can you repeat that?"
      - "What did you say?"
      - "再说一遍"

  # ── 确认 ──
  - name: confirm
    description: 用户同意或确认
    keywords: [yes, yeah, correct, that's right, exactly, sounds good, okay, sure, go ahead, proceed, 是的, 对, 好的, 没错, 可以]
    examples:
      - "Yes, that's correct"
      - "Sounds good, proceed"
      - "是的，没错"

  - name: decline
    description: 用户不同意、取消或拒绝
    keywords: [no, nope, not, that's wrong, incorrect, cancel, stop, never mind, I don't want, reject, 不, 不对, 取消, 算了]
    examples:
      - "No, that's not what I want"
      - "Cancel that"
      - "不，不是我想要的"

  # ── 错误与恢复 ──
  - name: unrecognized_intent
    description: 无法确定意图（低置信度回退）
    keywords: []  # 无关键词 — 由分类器在 confidence < threshold 时产生
    examples: []  # 无示例 — 这是回退输出，非用户表达的意图
    note: "框架内部回退。不通过关键词匹配；在所有分类失败时产生。"

  - name: correction
    description: 用户纠正之前的陈述——自己的或机器人的
    keywords: [no, wrong, that's not right, I meant, actually, not that, I said, change that to, correct that, not X, 不是, 不对, 我指的是, 应该是, 改一下]
    examples:
      - "No, I meant 456 Oak Street, not 123 Main"
      - "That's wrong, my phone is 555-9999"
      - "不对，我指的是上海路456号"

  - name: ambiguous_request
    description: 话语可映射到多个可能的意图；需要消歧
    keywords: []  # 无关键词 — 由分类器在置信度分散时产生
    examples: []  # 无示例 — 这是分类器的元输出
    note: "框架内部元意图。当分类器检测到多个同等可能的意图，需要用户消歧时产生。"

  - name: out_of_scope
    description: 识别到请求但系统明确不支持
    keywords: []  # 无关键词 — 由系统能力注册表决定，非用户措辞
    examples: []  # 无示例 — 用户措辞多样化；分类器与能力注册表交叉引用
    note: "框架内部元意图。当分类器识别出有效的请求模式，但系统能力注册表标记为不支持时产生。"

  # ── 社交与元操作 ──
  - name: help
    description: 用户询问系统能力或如何使用机器人
    keywords: [help, what can you do, how do I use, guide me, assist, support, what are you capable of, commands, options, 帮助, 你能做什么, 怎么用, 功能]
    examples:
      - "What can you help me with?"
      - "How do I use this?"
      - "你能帮我做什么？"

  - name: chitchat
    description: 与任何任务无关的随意社交对话
    keywords: [how are you, how's it going, thank you, thanks, appreciate it, tell me a joke, nice weather, lol, haha, 你好吗, 谢谢, 讲个笑话, 天气不错]
    examples:
      - "How are you today?"
      - "Thank you for helping!"
      - "谢谢你的帮助！"

  - name: complaint
    description: 用户表达不满或提出投诉
    keywords: [complaint, unhappy, dissatisfied, frustrated, terrible, awful, bad service, not satisfied, want to complain, this is unacceptable, 投诉, 不满意, 太差了, 我要投诉]
    examples:
      - "I'm very unhappy with this process"
      - "This is terrible service"
      - "我对这个流程非常不满意"

  - name: escalate
    description: 用户要求转接人工客服
    keywords: [human, speak to someone, real person, talk to a person, representative, agent, customer service, operator, transfer me, connect me to, 人工, 转人工, 客服, 真人]
    examples:
      - "I want to speak to a human"
      - "Can you transfer me to an agent?"
      - "我要转人工客服"
```

> **无关键词的元意图**（`unrecognized_intent`、`ambiguous_request`、`out_of_scope`）由分类器产生，不通过关键词匹配。它们完全依赖 LLM 分类和能力注册表查找。详见 §3 分类流程。

### 2.2 自定义意图（按工作流）

每个工作流可以定义额外的领域特定意图。关于家庭保险意图及其关键词和示例的完整目录，请参见 [intent-definitions.md](../../examples/home-insurance/intent-definitions.md)。框架对系统意图和自定义意图使用相同的 `IntentDef` schema。

### 2.3 意图定义 Schema

```yaml
# Schema: IntentDef
#   name:        string      # 唯一标识符
#   description: string      # 指导 LLM 分类
#   complex:     boolean     # true = 多轮任务；不能与其他 complex 意图组合
#   keywords:    string[]    # 确定性回退模式
#   examples:    string[]    # LLM 提示的 few-shot 示例

intents:
  - name: "ask_question"
    description: "用户询问信息或解释"
    complex: false
    keywords:
      - "what is"
      - "how does"
      - "tell me about"
      - "explain"
    examples:
      - "What is my deductible?"
      - "How does the claims process work?"
      - "Tell me about coverage options"

  - name: "get_quote"
    description: "用户请求新的保险报价"
    complex: true
    keywords:
      - "quote"
      - "get a price"
      - "how much"
      - "estimate"
    examples:
      - "I want a quote for home insurance"
      - "How much would it cost to insure my house?"
      - "Give me a price estimate"
```

### 2.4 分类策略

框架采用 **LLM 优先 + 关键词回退** 作为确定性安全网。这是唯一支持的策略——没有回退到更简单机制的选项。

| 维度 | 行为 |
|-----------|----------|
| **主策略** | LLM 结合对话上下文和意图定义对用户话语进行分类 |
| **回退** | 基于意图 `keywords` 列表的关键词匹配（不区分大小写，confidence=1.0） |
| **合并** | LLM 结果在 confidence ≥ threshold 时胜出；否则关键词结果胜出 |
| **均无结果** | 返回 `unrecognized_intent` → 路由到澄清节点 |
| **置信度阈值** | 可配置，默认 `0.7` |
| **温度** | 0（确定性输出） |

完整的分词流程详见 §3。

## 3. 分类策略：LLM优先 + 关键词回退

> **所有 LLM 输出均为 JSON。** 框架通过输出守卫（见 HLD 第4.3节）对每个分类结果强制执行 schema 验证、字段存在性检查和类型强制转换。如果 JSON 格式错误，守卫会在重试预算内自动重试。

### 3.1 对话上下文

意图分类不是单条消息的操作。LLM 提示必须包含对话历史以消歧模糊话语。例如，如果 agent 刚刚问"我应该继续吗？"，"yes" 意味着 `confirm`；但如果 agent 问"你的电话号码是 555-0123 吗？"（确认提取的数据），"yes" 则意味着 `provide_information`。脱离了上下文，像回应"你叫什么名字？"时说 "yes" 这样毫无语义关联的单字回复，就是 `unrecognized_intent`。

框架在每次分类调用中包含 **最近3条用户消息 + 最近3条 agent 消息** 作为上下文。这提供了足够的对话历史来消歧短回复，同时不会使提示词膨胀。

> **注意：** 意图分类的输入还包含 `agentState.phase`（例如 `quoting`、`claims`、`onboarding`）。当前工作流阶段提供状态感知的上下文，帮助分类器消歧意图 —— 例如，在 `quoting` 阶段说"我想改一下"很可能是指修改报价，而在 `claims` 阶段则很可能是指更新理赔。

### 3.2 边界情况覆盖

意图分类是系统应对意外用户行为的安全网。它必须处理的边界情况：

- 工作流中突然切换话题（"算了，我想给别人付款"）
- 模糊的单字回复（"ok"、"sure"、"no"）
- 工作流中的离题问题
- 部分或不完整的话语
- 代码切换或混合语言输入

当分类器无法自信地解决边界情况时，返回 `unrecognized_intent`，触发澄清回复。

### 3.3 LLM 提示词构建

框架根据用户的意图定义和对话上下文构建系统提示词。提示词包括：

1. 最近3条用户消息 + 最近3条 agent 消息（上下文窗口）
2. 所有意图及其描述的列表
3. 每个意图的 few-shot 示例
4. 结构化输出指令：`{ intent: string, confidence: number, reasoning: string }`

Temperature 设置为 0 以实现确定性分类。

### 3.4 回退：关键词匹配

如果 LLM 调用失败或返回 `confidence < threshold`，框架对用户输入执行关键词匹配：

```
For each intent:
  if any keyword matches user_input (case-insensitive):
    return that intent with confidence=1.0
```

系统意图具有内置关键词模式。自定义意图使用用户提供的 `keywords`。

### 3.5 置信度阈值

可配置的阈值（默认 `0.7`）。当 LLM 返回 `confidence < threshold` 时，结果被视为 `unrecognized_intent`，触发第3层的澄清回复。

### 3.6 合并策略

```
1. 尝试 LLM 分类
2. 如果 LLM 失败 → 回退到关键词匹配
3. 如果 LLM 成功但 confidence < threshold → 使用回退结果（如有）
4. 如果两者都未产生结果 → unrecognized_intent
```

LLM 结果 + 回退结果可能不一致。当两者不一致且 LLM 置信度高于阈值时，LLM 胜出。当两者都低于阈值时，关键词回退胜出（它是确定性的）。

> **注意：** 如果 LLM 和关键词都未产生结果（`unrecognized_intent`），框架路由到 `errorNode` 进行统一错误处理（见路由与执行规范第6节）。

## 4. 输出契约

### 4.1 分类结果（每个意图）

```
ClassifiedIntent {
  intent:     string      // 解析后的意图标签
  confidence: number      // 0.0 - 1.0
  source:     "llm" | "keyword" | "unrecognized"
  reasoning?: string      // LLM 的推理（用于审计追踪）
}
```

`source` 字段指示哪个分类器产生了结果，使下游节点能够调整行为（例如，"关键词匹配 → 立即继续；LLM 匹配 → 考虑再次确认"）。

### 4.2 多意图输出

单条用户话语可能携带多个意图（"我要报理赔，我的电话是 123-456-7890"）。分类器返回 `ClassifiedIntent` 对象列表：

```
ClassificationResult {
  intents: ClassifiedIntent[]  // 一个或多个解析后的意图
}
```

**示例：**

```json
{
  "intents": [
    {
      "intent": "file_claim",
      "confidence": 0.95,
      "source": "llm"
    },
    {
      "intent": "provide_information",
      "confidence": 0.88,
      "source": "llm",
      "reasoning": "用户随理赔意图一起提供了电话号码"
    }
  ]
}
```

### 4.3 意图组合规则

每个意图携带 `complex` 标志。组合规则防止单轮处理中出现不兼容的组合：

| 场景 | 允许 | 行为 |
|----------|---------|----------|
| 多个简单意图 | 是 | 一起处理 |
| 1 个 complex + N 个简单意图 | 是 | 一起处理（简单意图依附于 complex 工作流） |
| 多个 complex 意图 | 否（默认） | 见下方冲突解决 |

**多 complex 意图的冲突解决** 在 Response 节点中通过 `on_multi_intent_conflict` 配置：

| 模式 | 行为 |
|------|----------|
| `error`（默认） | 抛出 `MultiIntentConflictError`；响应层询问用户首先处理哪个任务 |
| `sequential` | 先处理置信度最高的 complex 意图；将其余排队到下一轮 |

**验证伪代码：**

```
def validate_intent_combination(intents: ClassifiedIntent[], intent_defs: IntentDef[], mode: string):
    complex = [i for i in intents if intent_defs[i.intent].complex]
    if len(complex) > 1:
        if mode == "error":
            raise MultiIntentConflictError(
                conflict_intents=[i.intent for i in complex],
                message="检测到多个任务。请选择先处理哪一个。"
            )
        # sequential: 保留最高置信度，将其余排队
```

---

## 5. 待解决问题

### 5.1 多意图检测

多意图检测已实现。分类器对每条用户消息返回 `ClassifiedIntent` 对象列表（见第 4.2 节）。意图组合验证（第 4.3 节）防止不兼容的 complex 意图被同时处理。

### 5.2 意图 → 提取 Payload 映射

每个意图映射到一个由 Extract 节点消费的类型化提取 payload（参见 [提取层规范](./2026-06-17-extraction-layer-design.md)）：

#### 系统意图

| Intent | Payload 类 | 提取 / 路由 |
|--------|--------------|---------------------|
| `start_conversation` | *(跳过提取)* | 路由到对话初始化节点 |
| `finish_conversation` | *(跳过提取)* | 路由到对话结束节点 |
| `pause` | *(跳过提取)* | 暂停处理，等待用户信号 |
| `restart` | *(跳过提取)* | 重置 agentState，返回入口 |
| `ask_question` | *(跳过提取)* | 直接路由到 Q&A 节点 |
| `provide_information` | `ProvideInformationIntentPayload` | `field_values: dict[str, Any]` |
| `repeat` | *(跳过提取)* | 重放上一条 assistant 消息 |
| `confirm` | `ConfirmIntentPayload` | `fields: dict[str, bool]` |
| `decline` | `DeclineIntentPayload` | `fields: dict[str, bool]` |
| `unrecognized_intent` | *(跳过提取)* | 路由到澄清节点 |
| `correction` | `CorrectionIntentPayload` | `corrected_fields: dict[str, Any]` |
| `ambiguous_request` | `AmbiguousRequestPayload` | `possible_intents: str[]`，需要用户消歧 |
| `out_of_scope` | *(跳过提取)* | 路由到超出范围响应节点 |
| `help` | *(跳过提取)* | 路由到帮助/能力节点 |
| `chitchat` | *(跳过提取)* | 路由到闲聊响应节点 |
| `complaint` | `ComplaintIntentPayload` | `subject: str, details: str` |
| `escalate` | `EscalateIntentPayload` | `reason: str, urgency: str` |

#### 自定义意图（按工作流）

| Intent | Payload 类 | 提取 / 路由 |
|--------|--------------|---------------------|
| `<领域意图>` | `<DomainIntentPayload>` | `field_values: dict[str, Any]` |

自定义意图遵循与 `provide_information` 相同的模式——实体提取填充一个领域特定的 payload，供下游工作流节点消费。Payload 类名由意图名派生（例如 `get_quote` → `GetQuoteIntentPayload`）。Complex 意图可能在首轮跳过提取，推迟到多轮槽位填充。

> **示例 — 家庭保险：** `get_quote` → `GetQuoteIntentPayload`（`field_values`），`file_claim` → `FileClaimIntentPayload`（`field_values`），`check_coverage` → `CheckCoverageIntentPayload`（`field_values`）。

### 5.3 意图分析提示词指南

当 LLM 分析用户消息时，应：

1. 识别所有存在的意图（可能多个）
2. 为每个意图提取任何关联的数据字段
3. 为**每个**检测到的意图返回一个 `ClassifiedIntent`，各自带有置信度分数
4. 不要将不同意图的数据合并到单个 payload 中

**示例：** "我要报理赔，我的电话是 123-456-7890" 产生两个 payload——一个 `FileClaimIntentPayload`（无数据）+ 一个 `ProvideInformationIntentPayload`（电话号码）。

### 5.4 置信度阈值校准

默认阈值 `0.7` 是起点。实践中，最优阈值因领域、意图复杂度和 LLM 模型选择而异。团队应如何校准阈值？选项包括：按意图的历史准确率分析、A/B 测试，或基于对话阶段的自适应阈值。

### 5.5 长对话中的意图漂移

在长时间对话中（例如 20+ 轮次），用户意图可能逐渐变化而非突然切换话题。框架应通过窗口化置信度趋势检测意图漂移，还是依赖第2层状态机检测阶段不匹配？

### 5.6 跨语言意图分类

框架应如何处理非英语输入？选项包括：(a) 分类前翻译为英语，(b) 在提示词中包含多语言示例，(c) 使用多语言嵌入模型。每种方案在延迟、成本和准确率方面有不同的权衡。

### 5.7 冷启动：Zero-Shot vs. Few-Shot 提示

对于没有提供训练示例的自定义意图，框架应回退到 zero-shot 提示，还是要求最少示例数？Zero-shot 更灵活，但对领域特定意图的准确率较低。

---

## 参考资料

- [高层设计](./2026-06-16-deterministic-workflow-framework-design.md) — 父文档
- [状态机设计](./2026-06-16-state-machine-design.md) — 意图+状态解析逻辑
