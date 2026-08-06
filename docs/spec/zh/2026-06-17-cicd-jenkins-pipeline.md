# CI/CD 流水线 (Jenkins)

> 隶属于 [Deterministic Workflow Framework — 高层设计](./01-deterministic-workflow-framework-design.md)
> 涵盖: Jenkins 声明式流水线、eval 阶段、环境晋升、回滚策略。

---

## Changelog

| 日期 | 版本 | 变更 |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | 初始 CI/CD 流水线规范：Jenkins 阶段、mock/real LLM eval、环境晋升、回滚 |
| 2026-06-17 | 0.2.0 | 移除所有 Groovy 实现代码；替换为 YAML 流水线阶段 schema；添加声明式部署描述；添加实现方案对比（Jenkins、GitHub Actions、GitLab CI） |
| 2026-06-18 | 0.2.1 | 实际移除 §7.3 中残留的 Groovy 代码（v0.2.0 中遗漏）；替换为声明式 YAML 流水线描述 |

---

## 1. 职责

CI/CD 流水线自动化 deterministic workflow framework 的验证、评估与部署。每次变更按 **lint → eval → build → deploy** 流程流转，环境间升级需通过门禁。

```
Git Push / PR
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│                    JENKINS PIPELINE                        │
├─────────┬─────────┬─────────┬─────────┬─────────┬────────┤
│  Lint   │  Eval   │  Eval   │  Build  │  Deploy │ Deploy │
│         │ (Mock   │ (Real   │         │   dev   │  e2e   │
│         │  LLM)   │  LLM)   │         │         │        │
│  All    │  All    │  PR     │  On     │  Auto   │ Manual │
│  pushes │  pushes │  only   │  merge  │  on     │ trigger│
│         │         │         │         │  merge  │        │
└─────────┴─────────┴─────────┴─────────┴─────────┴────────┘
                                                      │
                                                      ▼
                                                ┌─────────┐
                                                │ Deploy  │
                                                │  prod   │
                                                │ Manual  │
                                                │ + approv│
                                                └─────────┘
```

### 1.1 流水线覆盖范围

- ✅ **Linting** — 代码风格、YAML schema 校验、类型检查
- ✅ **Evaluation** — mock LLM（快速，所有 push）+ real LLM（仅 PR）
- ✅ **Building** — Docker 镜像构建并推送至 registry
- ✅ **Deployment** — dev、e2e、prod，带门禁晋升
- ✅ **Rollback** — 回退至上一个 LangGraph checkpoint

### 1.2 流水线不覆盖范围

- ❌ **基础设施供应** — Kubernetes、DNS、网络（由 Terraform/IaC 处理）
- ❌ **数据库迁移** — checkpoint store 的 schema 变更（由独立的迁移流水线处理）
- ❌ **密钥轮换** — API key 轮换（由 Vault / 云密钥管理服务处理）
- ❌ **性能测试** — 压力测试、负载测试（未来添加）

---

## 2. 流水线阶段

### 2.1 阶段概览

| 阶段 | 触发条件 | LLM 模式 | 运行时间 | 门禁 |
|-------|---------|----------|---------|-------|
| **Lint** | 每次 push | N/A | ~30s | 必须通过 |
| **Eval (Mock LLM)** | 每次 push | Mock（离线） | ~2 min | 必须通过 |
| **Eval (Real LLM)** | 仅 PR | Real（OpenAI/Anthropic） | ~10 min | 合并前必须通过 |
| **Build** | 合并至 main | N/A | ~3 min | 必须通过 |
| **Deploy dev** | 合并至 main | Real | ~2 min | 自动 |
| **Deploy e2e** | 手动触发 | Real | ~2 min | 手动门禁 |
| **Deploy prod** | 手动触发 | Real | ~2 min | 手动 + 审批 |

### 2.2 阶段详情

#### Stage 1: Lint

```yaml
# 流水线阶段配置
stages:
  lint:
    name: "Lint"
    trigger: every_push
    parallel: true
    steps:
      - name: "Python lint (ruff)"
        command: "ruff check ."
        timeout_minutes: 2
      
      - name: "YAML validation"
        command: "python scripts/validate_workflows.py"
        description: "根据 schema 校验所有 .yaml 工作流定义"
        timeout_minutes: 2
      
      - name: "Type check (mypy)"
        command: "mypy src/ --strict"
        timeout_minutes: 3
    failure_action: stop_pipeline
```

#### Stage 2: Eval (Mock LLM)

使用 mock LLM 响应对所有工作流运行 eval。快速、确定性、无 API 费用。

```yaml
  eval_mock:
    name: "Eval (Mock LLM)"
    trigger: every_push
    parallel: false
    environment:
      ENV: e2e
      LLM_MODE: mock                # 离线 mock — 无 LLM API 调用
    steps:
      - name: "Run eval suite"
        command: >
          python -m pytest tests/evals/
          --eval-dataset=home-insurance-eval
          --mock-llm
          --junitxml=results/eval-mock-results.xml
        timeout_minutes: 5
    
    post:
      - name: "Archive eval results"
        archive:
          artifacts: "results/eval-mock-results.xml"
    
    failure_action: stop_pipeline
```

#### Stage 3: Eval (Real LLM)

使用真实 LLM 调用对变更的工作流运行 eval。仅在 PR 时触发，不在每次 push 时触发（成本 + 延迟控制）。

```yaml
  eval_real:
    name: "Eval (Real LLM)"
    trigger: pull_request            # 仅 PR — 跳过常规 push
    parallel: false
    environment:
      ENV: e2e
      LLM_MODE: real
      OPENAI_API_KEY: "${OPENAI_API_KEY_CREDENTIAL}"
      LANGSMITH_TRACING: "true"
    steps:
      - name: "Detect changed workflows"
        command: |
          CHANGED=$(git diff --name-only origin/main...HEAD -- 'workflows/*.yaml')
          echo "CHANGED_WORKFLOWS=${CHANGED}" > changed_workflows.env
      
      - name: "Run eval on changed workflows"
        command: >
          python -m pytest tests/evals/
          --eval-dataset=home-insurance-eval
          --real-llm
          --changed-workflows="${CHANGED_WORKFLOWS}"
          --junitxml=results/eval-real-results.xml
          --langsmith-project="ci-evals"
        timeout_minutes: 15
    
    post:
      always:
        - name: "Archive eval results"
          archive:
            artifacts: "results/eval-real-results.xml"
        - name: "Publish eval report"
          publish_junit: "results/eval-real-results.xml"
    
    failure_action: stop_pipeline
    gates:
      - metric: "intent_accuracy"
        threshold: ">= 0.90"
      - metric: "goal_check_pass_rate"
        threshold: ">= 0.85"
      - metric: "schema_violation_rate"
        threshold: "<= 0.05"
```

#### Stage 4: Build

```yaml
  build:
    name: "Build Docker Image"
    trigger: merge_to_main
    environment:
      DOCKER_REGISTRY: "${DOCKER_REGISTRY_URL}"
    steps:
      - name: "Build Docker image"
        command: |
          docker build \
            --tag "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}" \
            --tag "${DOCKER_REGISTRY}/deterministic-workflow:latest" \
            --build-arg ENV=prod \
            .
        timeout_minutes: 5
      
      - name: "Push to registry"
        command: |
          docker push "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
          docker push "${DOCKER_REGISTRY}/deterministic-workflow:latest"
        timeout_minutes: 5
    
    failure_action: stop_pipeline
```

#### Stage 5-7: Deploy (dev → e2e → prod)

```yaml
  deploy_dev:
    name: "Deploy to dev"
    trigger: merge_to_main
    environment: dev
    steps:
      - deploy:
          type: kubernetes
          namespace: dev
          deployment: deterministic-workflow-dev
          container: workflow
          image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
          timeout_minutes: 3
      - smoke_test:
          environment: dev
          endpoint: "https://dev-api.example.com"
          timeout_minutes: 2

  deploy_e2e:
    name: "Deploy to e2e"
    trigger: manual
    environment: e2e
    gates:
      - type: manual_approval
        message: "将构建 ${BUILD_NUMBER} 部署至 E2E？"
    steps:
      - deploy:
          type: kubernetes
          namespace: e2e
          deployment: deterministic-workflow-e2e
          container: workflow
          image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
      - smoke_test:
          environment: e2e
          endpoint: "https://e2e-api.example.com"
      - integration_test:
          environment: e2e
          suite: "tests/integration/"
          report: "results/integration-results.xml"
          timeout_minutes: 10

  deploy_prod:
    name: "Deploy to prod"
    trigger: manual
    environment: prod
    gates:
      - type: manual_approval
        message: "将构建 ${BUILD_NUMBER} 部署至生产环境？"
        approvers:
          - release-managers
    steps:
      - deploy_canary:
          type: kubernetes
          namespace: prod
          deployment: deterministic-workflow-prod-canary
          container: workflow
          image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
      - monitor_canary:
          duration_minutes: 10
          error_rate_threshold: 5
          latency_p95_threshold_ms: 5000
          auto_rollback: true
      - deploy_full:
          type: kubernetes
          namespace: prod
          deployment: deterministic-workflow-prod
          container: workflow
          image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
      - smoke_test:
          environment: prod
          endpoint: "https://api.example.com"
```

---

## 3. 流水线阶段 Schema (YAML)

流水线以 YAML schema 形式定义 — 而非可运行的 Groovy 代码。每个 CI/CD 平台消费此 schema 并翻译为其原生的流水线定义格式。

```yaml
# pipeline.yaml — 流水线阶段 Schema（声明式，非实现代码）
pipeline:
  name: "deterministic-workflow-ci-cd"
  version: "0.2.0"

  agent:
    type: container
    image: "python:3.12"
    resources:
      cpu: "2"
      memory: "4Gi"

  environment:
    ENV: ci
    DOCKER_REGISTRY:
      from: credential
      id: "docker-registry"
    OPENAI_API_KEY:
      from: credential
      id: "openai-api-key"
    LANGSMITH_API_KEY:
      from: credential
      id: "langsmith-api-key"

  options:
    timeout_minutes: 60
    build_retention:
      keep_count: 30
    timestamps: true

  triggers:
    - type: push
      branches: ["**"]
    - type: pull_request
      branches: ["main"]
    - type: merge_to_main
      branches: ["main"]
      condition: "not pull_request"

  stages:
    lint:
      name: "Lint"
      trigger: push_or_pr
      agent: container
      parallel:
        - name: "Python lint (ruff)"
          run: "ruff check ."
          timeout_minutes: 2
        - name: "YAML validation"
          run: "python scripts/validate_workflows.py"
          timeout_minutes: 2
        - name: "Type check (mypy)"
          run: "mypy src/ --strict"
          timeout_minutes: 3
      on_failure: stop_pipeline

    eval_mock:
      name: "Eval (Mock LLM)"
      trigger: push_or_pr
      env:
        LLM_MODE: mock
      steps:
        - name: "Install dev dependencies"
          run: "pip install -r requirements-dev.txt"
        - name: "Run mock eval suite"
          run: >
            python -m pytest tests/evals/
            --eval-dataset=home-insurance-eval
            --mock-llm
            --junitxml=results/eval-mock-results.xml
          timeout_minutes: 5
      post:
        always:
          - publish_junit: "results/eval-mock-results.xml"
      on_failure: stop_pipeline

    eval_real:
      name: "Eval (Real LLM)"
      trigger: pull_request_only
      env:
        LLM_MODE: real
        OPENAI_API_KEY:
          from: credential
          id: "openai-api-key"
        LANGSMITH_TRACING: "true"
      steps:
        - name: "Detect changed workflows"
          detect_changes:
            pattern: "workflows/*.yaml"
            output_variable: CHANGED_WORKFLOWS
        - name: "Run eval on changed workflows"
          run: >
            python -m pytest tests/evals/
            --eval-dataset=home-insurance-eval
            --real-llm
            --changed-workflows="${CHANGED_WORKFLOWS}"
            --junitxml=results/eval-real-results.xml
            --langsmith-project="ci-evals"
          timeout_minutes: 15
      post:
        always:
          - archive_artifacts: "results/eval-real-results.xml"
          - publish_junit: "results/eval-real-results.xml"
      gates:
        - metric: "intent_accuracy"
          threshold: ">= 0.90"
        - metric: "goal_check_pass_rate"
          threshold: ">= 0.85"
        - metric: "schema_violation_rate"
          threshold: "<= 0.05"
      on_failure: stop_pipeline

    build:
      name: "Build Docker Image"
      trigger: merge_to_main
      env:
        DOCKER_REGISTRY:
          from: credential
          id: "docker-registry"
      steps:
        - name: "Build Docker image"
          build_image:
            tags:
              - "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
              - "${DOCKER_REGISTRY}/deterministic-workflow:latest"
            build_args:
              ENV: prod
          timeout_minutes: 5
        - name: "Push to registry"
          push_image:
            tags:
              - "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
              - "${DOCKER_REGISTRY}/deterministic-workflow:latest"
          timeout_minutes: 5
      on_failure: stop_pipeline

    deploy_dev:
      name: "Deploy to Dev"
      trigger: merge_to_main
      env: dev
      steps:
        - name: "Deploy to dev"
          deploy:
            type: kubernetes
            environment: dev
            namespace: dev
            deployment: deterministic-workflow-dev
            container: workflow
            image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
          timeout_minutes: 3
        - name: "Smoke test"
          run: "python scripts/smoke_test.py --env=dev"
          timeout_minutes: 2

    deploy_e2e:
      name: "Deploy to E2E"
      trigger: manual
      env: e2e
      steps:
        - name: "Deploy to e2e"
          deploy:
            type: kubernetes
            environment: e2e
            namespace: e2e
            deployment: deterministic-workflow-e2e
            container: workflow
            image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
        - name: "E2E smoke test"
          run: "python scripts/smoke_test.py --env=e2e"
        - name: "Run integration tests"
          run: >
            python -m pytest tests/integration/
            --env=e2e
            --junitxml=results/integration-results.xml
          timeout_minutes: 10
      gates:
        - type: manual_approval
          message: "将构建 ${BUILD_NUMBER} 部署至 E2E？"

    deploy_prod:
      name: "Deploy to Production"
      trigger: manual
      env: prod
      gates:
        - type: manual_approval
          message: "将构建 ${BUILD_NUMBER} 部署至生产环境？"
          approvers: [release-managers]
      steps:
        - name: "Deploy to prod (canary)"
          deploy:
            type: kubernetes
            environment: prod
            namespace: prod
            deployment: deterministic-workflow-prod-canary
            container: workflow
            image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
        - name: "Canary monitoring"
          monitor:
            duration_minutes: 10
            error_rate_threshold: 5
            latency_threshold_p95: 5
            auto_rollback: true
        - name: "Full prod rollout"
          deploy:
            type: kubernetes
            environment: prod
            namespace: prod
            deployment: deterministic-workflow-prod
            container: workflow
            image: "${DOCKER_REGISTRY}/deterministic-workflow:${BUILD_NUMBER}"
        - name: "Post-deploy smoke test"
          run: "python scripts/smoke_test.py --env=prod"

  post:
    always:
      - clean_workspace: true
    on_failure:
      - notify:
          channel: "#ci-alerts"
          status: danger
          message: "流水线失败: ${JOB_NAME} #${BUILD_NUMBER}"
    on_success:
      - notify:
          channel: "#ci-alerts"
          status: good
          message: "流水线成功: ${JOB_NAME} #${BUILD_NUMBER}"
```

---

## 4. 评估阶段详情

### 4.1 Eval 套件

```yaml
# evals-create 测试配置
eval:
  suites:
    home_insurance_quote:
      dataset: home-insurance-eval
      test_cases:
        - name: "happy_path_full_quote"
          input: "我需要为我的三居室房屋购买家庭保险"
          expected:
            intent: get_quote
            completion_state: completed
          assert:
            - extracted.property_type is not null
            - extracted.address is not null
            - response_data.goal_met == true
        
        - name: "incomplete_info_graceful"
          input: "我想买保险"
          expected:
            intent: get_quote
            completion_state: active
          assert:
            - extracted.property_type is null
            - response_data.goal_met == false
            - response_data.gap_analysis is not null
        
        - name: "intent_misclassification_resilience"
          input: "告诉我你们与竞争对手相比的保险产品情况"
          expected:
            intent: general_inquiry
          assert:
            - intent != get_quote

  eval_gates:
    global:
      intent_accuracy: ">= 0.90"
      goal_check_pass_rate: ">= 0.85"
      schema_violation_rate: "<= 0.05"
    
    per_workflow:
      home_insurance_quote:
        extraction_f1: ">= 0.88"
        routing_accuracy: ">= 0.92"
```

### 4.2 Mock LLM 策略

```yaml
# 用于快速 eval 的 Mock LLM（无 API 费用，确定性）
eval:
  mock_llm:
    strategy: pre_recorded_responses      # pre_recorded_responses | rule_based
    
    pre_recorded_responses:
      # 从真实 LLM 运行中录制的响应，签入到仓库中
      source: tests/fixtures/mock_responses/
      format: jsonl
    
    # 替代方案：基于规则的 mock，根据输入返回固定 JSON
    # strategy: rule_based
    # rules:
    #   - match: "insurance.*house"
    #     response: { "intent": "get_quote", "confidence": 0.95 }
```

### 4.3 Real LLM Eval（仅 PR）

```yaml
eval:
  real_llm:
    trigger: pull_request                  # 仅 PR
    provider: openai                       # 用于 eval 的 LLM
    model: gpt-4o
    cost_estimate:
      per_run: "$2-5 USD"
      monthly_budget: "$200 USD"
    
    parallelism: 4                         # 并发 eval 运行数
    retry_on_flaky: true                   # 对不稳定的 LLM 运行进行重试
    max_retries_per_case: 2
    
    langsmith:
      tracing: true
      project: "ci-evals"
      # 每次 eval 运行成为一个 LangSmith 实验
```

---

## 5. 真实项目示例: home_insurance

### 5.1 概览

**home_insurance** 是一个家庭保险报价系统。其 chat 版本将用户路由至家庭保险报价工作流：收集房屋信息 → 收集财产信息 → 运行风险评估 → 呈现报价方案。

```
用户: "$500K 的家庭保险保单最佳报价是什么？"
    │
    ▼
Layer 1 (Extract): { intent: "get_home_insurance_quote", coverage_amount: 500000 }
Layer 2 (Route): home_insurance_quote workflow → collect_property_info phase
Layer 3 (Respond): "我很乐意帮您寻找 $500K 保额的报价。首先，让我问您..."
```

### 5.2 后端集成

框架的 chat 版本调用 home_insurance 的后端 API 进行报价计算：

```yaml
# 工作流集成配置
workflows:
  home_insurance_quote:
    backend:
      api: home_insurance
      base_url: "https://home-insurance-api.${ENV}.example.com"
      auth:
        type: api_key
        key: "${HOME_INSURANCE_API_KEY}"
      endpoints:
        submit_quote_application: "POST /v1/quote-applications"
        get_quote:                "GET  /v1/quote"
        run_risk_assessment:      "POST /v1/risk-assessment"
      timeout_seconds: 10
      retry:
        max_attempts: 2
        backoff: exponential
      circuit_breaker:
        failure_threshold: 5
        recovery_timeout_seconds: 30
```

### 5.3 home_insurance 的 Eval 数据集

```yaml
eval:
  suites:
    home_insurance_quote:
      dataset: home-insurance-quote-eval
      test_cases:
        - name: "happy_path_home_insurance_quote"
          input: "我需要一份 $500,000 的房屋保险报价，$1,000 免赔额"
          expected:
            intent: get_home_insurance_quote
          assert:
            - extracted.coverage_amount == 500000
            - extracted.deductible_amount == 1000
            - response_data.quote is not null
        
        - name: "high_risk_assessment"
          input: "能否为风险评分 580 的房产提供报价？"
          expected:
            intent: get_home_insurance_quote
          assert:
            - extracted.risk_score == 580
            - response_data.outcome == "declined"
            - response_data.reason contains "risk"
        
        - name: "high_value_property_routing"
          input: "需要一份加州 $1.2M 房产的报价"
          expected:
            intent: get_home_insurance_quote
          assert:
            - extracted.coverage_amount == 1200000
            - routing_decision.route == "high_value_property_specialist"
        
        - name: "first_time_homeowner_programs"
          input: "我是首次购房者，你们有什么特殊计划？"
          expected:
            intent: first_time_homeowner_inquiry
          assert:
            - extracted.first_time_homeowner == true
```

---

## 6. 环境晋升策略

### 6.1 晋升流程

```
dev（合并后自动触发）
  │
  │  开发者手动触发
  ▼
e2e（手动触发）
  │
  │  集成测试通过
  │  手动触发 + release-managers 审批
  ▼
prod（手动触发 + 审批）
```

### 6.2 晋升规则

```yaml
pipeline:
  promotion:
    dev_to_e2e:
      trigger: manual
      requires:
        - dev_smoke_test_passed
        - docker_image_built
      approver: any_developer
    
    e2e_to_prod:
      trigger: manual
      requires:
        - e2e_smoke_test_passed
        - integration_tests_passed
        - eval_mock_passed
        - eval_real_passed
      approver: release_managers      # 需要 release-managers 组审批
      canary:
        enabled: true
        duration_minutes: 10
        error_rate_threshold: 5       # canary 中最高 5% 错误率
        auto_rollback: true           # canary 失败时自动回滚
    
    deployment_strategy:
      method: rolling_update          # rolling_update | blue_green | canary
      max_surge: 1
      max_unavailable: 0
```

### 6.3 各环境静态分析门禁

```yaml
pipeline:
  gates:
    dev:
      - lint_passed
      - eval_mock_passed
    
    e2e:
      - lint_passed
      - eval_mock_passed
      - eval_real_passed
      - integration_tests_passed
    
    prod:
      - all_above
      - canary_passed
      - approval_granted
```

---

## 7. 回滚策略

### 7.1 LangGraph Checkpoint 回滚

```yaml
# 回滚将会话恢复至上一个已知正常的 checkpoint
rollback:
  strategy: checkpoint_revert
  
  checkpoint:
    # 每次部署前，流水线对 LangGraph checkpoint store 做快照
    pre_deploy_snapshot:
      enabled: true
      label: "pre-deploy-${BUILD_NUMBER}"
    
    # 回滚从快照恢复
    restore:
      command: "python scripts/rollback_checkpoint.py --label=pre-deploy-${BUILD_NUMBER}"
      # 此操作将所有活跃会话恢复至故障部署前
      # 的最后一个 checkpoint。
    
    # 在故障部署期间创建的会话：
    # - 如果未发送任何消息 → 删除（无数据丢失）
    # - 如果已发送消息 → checkpoint 可用，可以恢复
```

### 7.2 回滚流程

```yaml
rollback:
  steps:
    - name: "Trigger rollback"
      type: manual
      jenkins_job: "rollback-deterministic-workflow"
    
    - name: "Restore previous image"
      command: |
        kubectl set image deployment/deterministic-workflow-prod \
          workflow="${DOCKER_REGISTRY}/deterministic-workflow:${PREVIOUS_BUILD_NUMBER}" \
          --namespace=prod
    
    - name: "Restore checkpoints"
      command: |
        python scripts/rollback_checkpoint.py \
          --label="pre-deploy-${PREVIOUS_BUILD_NUMBER}" \
          --env=prod
    
    - name: "Verify restored state"
      command: |
        python scripts/verify_checkpoint_integrity.py \
          --env=prod \
          --label="pre-deploy-${PREVIOUS_BUILD_NUMBER}"
    
    - name: "Notify on-call"
      notify:
        slack_channel: "#oncall"
        message: "回滚完成 — 已恢复至构建 ${PREVIOUS_BUILD_NUMBER}"

  rollback_decision:
    # 满足以下条件时自动触发回滚：
    auto_triggers:
      - error_rate > 10% 持续 5 分钟
      - goal_check_422_rate > 30% 持续 5 分钟
      - critical_alert_fired (P1)
    
    # 随时可手动回滚
    manual_trigger:
      jenkins_job: "rollback-deterministic-workflow"
      parameters:
        - target_environment
        - target_build_number
        - reason
```

### 7.3 回滚流水线（声明式）

回滚流水线将之前的部署和 checkpoint 恢复至已知正常状态：

```yaml
# 回滚流水线 — 声明式阶段
rollback_pipeline:
  trigger: manual | auto
  auto_triggers:
    - error_rate > 10% 持续 5 分钟
    - goal_check_422_rate > 30% 持续 5 分钟
    - critical_alert_fired
  stages:
    - name: verify_rollback_target
      action: resolve_previous_build_number
      input:
        target_build: "previous" | <build_number>
    - name: deploy_previous_build
      action: set_container_image
      input:
        build: "{{rollback.build_number}}"
    - name: restore_checkpoints
      action: rollback_checkpoint
      input:
        label: "pre-deploy-{{rollback.build_number}}"
    - name: verify
      action: run_smoke_tests
```

---

## 8. 与其他框架组件的集成

### 8.1 Eval 指标流入可观测性

```yaml
# CI/CD 的 eval 结果推送到同一个 Prometheus/Grafana 技术栈
pipeline:
  eval_metrics_export:
    enabled: true
    pushgateway_url: "${PUSHGATEWAY_URL}"
    metrics:
      - eval_intent_accuracy
      - eval_extraction_f1
      - eval_goal_check_pass_rate
      - eval_schema_violation_rate
    labels:
      build_number: "${BUILD_NUMBER}"
      workflow: "{workflow_id}"
      commit_sha: "${GIT_COMMIT}"
```

### 8.2 通过可观测性告警发送通知

```yaml
pipeline:
  notifications:
    slack:
      channel: "#ci-alerts"
      events:
        - build_started
        - build_succeeded
        - build_failed
        - deploy_started
        - deploy_succeeded
        - deploy_failed
        - require_approval
        - rollback_started
        - rollback_completed
```

---

## 9. 待解决问题

| # | 问题 | 影响 |
|---|----------|--------|
| 1 | eval 数据集应存储在同一个仓库中（与工作流一起版本化），还是存储在独立的 eval-data 仓库中？ | 可审计性 vs 仓库膨胀 |
| 2 | 流水线应如何处理 `agentState` 的 schema 变更，这些变更可能在回滚时破坏 checkpoint 反序列化？ | 回滚安全性 |
| 3 | 在 e2e 和 prod 之间是否需要 staging 环境，还是有了 canary 部署后 e2e 就够了？ | 环境数量膨胀 |
| 4 | eval 门禁是否应按工作流单独配置（mortgage_rate_quote 可能需要与 home_insurance_quote 不同的准确率阈值）？ | 灵活性 vs 一致性 |
| 5 | 流水线应如何处理 real LLM eval 期间 LLM 服务商宕机？应跳过 eval 阶段还是让构建失败？ | CI 可靠性 |
| 6 | 部署时应提升 Docker 镜像标签（如 `dev-v1.2.3` → `e2e-v1.2.3` → `prod-v1.2.3`），还是在所有环境中使用相同的标签？ | 回滚清晰度 vs 标签膨胀 |

---

## References

- [高层设计](./01-deterministic-workflow-framework-design.md) — §2 核心架构，§4.1 框架原则
- [环境配置](./18-environment-config.md) — dev、e2e、prod 环境设置
- [可观测性与监控](./15-observability-monitoring.md) — 指标、告警、Grafana 仪表盘
- [LLM 网关](./14-llm-gateway.md) — Schema 校验（在 eval 阶段测试）
- [响应生成](./08-response-generation-layer-design.md) — Goal check 422 行为（eval 门禁）
- [提取层](./05-extraction-layer-design.md) — 实体提取（eval F1 指标）
- [意图分类](./04-intent-classification-design.md) — 意图准确率（eval 门禁）
- [会话生命周期](./07-conversation-lifecycle.md) — Checkpoint 回滚集成
- [Jenkins 声明式流水线](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Jenkins Kubernetes 插件](https://plugins.jenkins.io/kubernetes/)
