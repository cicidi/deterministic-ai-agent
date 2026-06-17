# Home Insurance Workflow — Examples

> Reference examples for [Deterministic Workflow Framework](../../specs/2026-06-16-deterministic-workflow-framework-design.md).
> All examples use **home insurance** as the unified domain.

## Files

| File | Description |
|------|-------------|
| [workflow.yaml](./workflow.yaml) | Complete home insurance workflow definition (quote + claim branches) |
| [intent-definitions.md](./intent-definitions.md) | Custom intent definitions for home insurance domain |
| [e2e-scenarios.md](./e2e-scenarios.md) | End-to-end walkthroughs: quote flow & claim flow |
| [audit-log-sample.json](./audit-log-sample.json) | Sample audit log for a complete quote+claim conversation |

## Workflow Overview

```
                    +------------------+
                    |      start       |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
         intent=get_quote            intent=file_claim
              |                             |
    +---------v----------+       +----------v---------+
    | collect_property   |       | file_claim         |
    | _info (llm)        |       |   (llm)            |
    +---------+----------+       +----------+---------+
              |                             |
    +---------v----------+       +----------v---------+
    | collect_coverage   |       | validate_claim     |
    | _needs (llm)       |       |   (code)           |
    +---------+----------+       +----------+---------+
              |                             |
    +---------v----------+       +----------v---------+
    | assess_risk (code) |       | assess_damage      |
    +---------+----------+       |   (llm)            |
              |                  +----------+---------+
    +---------v----------+                  |
    | calculate_premium  |       +----------v---------+
    |   (code)           |       | approve_claim      |
    +---------+----------+       |   (llm + HI)       |
              |                  +----------+---------+
    +---------v----------+                  |
    | present_quote      |       +----------v---------+
    |   (llm + HI)       |       | process_claim      |
    +---------+----------+       | _payment (code)    |
              |                  +----------+---------+
    +---------v----------+                  |
    | confirm_purchase   |       +----------v---------+
    |   (code)           |       | done               |
    +---------+----------+       +--------------------+
              |
    +---------v----------+
    | done               |
    +--------------------+
```

## Key Design Decisions

1. **Quote and claim share one workflow YAML** — demonstrates conditional branching from `start` based on user intent.
2. **Human review** at `present_quote` and `approve_claim` — critical compliance checkpoints.
3. **Risk scoring** (`assess_risk`) determines premium routing — high-risk properties get underwriter review before quoting.
4. **Idempotent payouts** — `process_claim_payment` uses idempotency keys to prevent duplicate payments.
