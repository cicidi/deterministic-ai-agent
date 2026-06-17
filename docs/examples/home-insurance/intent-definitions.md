# Home Insurance — Intent Definitions

> Custom intents for the home insurance domain, extending the [system intents](../../specs/2026-06-16-intent-classification-design.md#21-system-intents-built-in).

## Custom Intents

### Intent Definition Schema

```
IntentDef {
  name:         string      // unique identifier
  description:  string      // guides LLM classification
  keywords:     string[]    // deterministic fallback patterns
  examples:     string[]    // few-shot examples for LLM prompt
}
```

### Intent Catalog

```yaml
intents:
  - name: get_quote
    description: User wants a home insurance premium quote
    keywords: [quote, price, cost, how much, premium, estimate]
    examples:
      - "I want to get a home insurance quote for my apartment"
      - "How much for insuring my house?"
      - "What's the annual premium for a villa?"
      - "Can you give me an estimate for home coverage?"

  - name: file_claim
    description: User wants to file a home insurance claim for damage or loss
    keywords: [claim, damage, fire, flood, theft, break-in, accident, loss]
    examples:
      - "My house was damaged in a fire, I need to file a claim"
      - "There was water damage from a burst pipe"
      - "Someone broke into my apartment, I want to claim for theft"
      - "A tree fell on my roof during the storm, how do I claim?"

  - name: check_coverage
    description: User wants to check what their policy covers
    keywords: [coverage, covered, policy details, what does my insurance cover, includes]
    examples:
      - "Does my policy cover earthquake damage?"
      - "What's covered under my home insurance?"
      - "Is water damage from heavy rain included?"
      - "What are my policy limits for contents?"

  - name: renew_policy
    description: User wants to renew an expiring home insurance policy
    keywords: [renew, renewal, extension, expire, extend, continue]
    examples:
      - "I want to renew my home insurance policy"
      - "My policy is expiring next month, how do I renew?"
      - "Can you help me extend my coverage?"
      - "I received a renewal notice, what do I do?"

  - name: update_policy
    description: User wants to modify an existing policy (coverage amount, address, riders)
    keywords: [update, change, modify, adjust, add rider, revise]
    examples:
      - "I renovated my house, need to update the coverage amount"
      - "Add flood coverage to my existing policy"
      - "Change my address because I moved"
      - "I want to increase my building coverage"

  - name: cancel_policy
    description: User wants to cancel their home insurance policy
    keywords: [cancel, stop, terminate, end policy, discontinue]
    examples:
      - "I want to cancel my home insurance"
      - "Stop my policy effective immediately"
      - "How do I terminate my coverage?"
      - "I sold my house, need to cancel the insurance"

  - name: ask_about_claim_status
    description: User wants to check the status of an existing claim
    keywords: [claim status, progress, update on claim, when will, track]
    examples:
      - "What's the status of my claim CLM-2026-0042?"
      - "When will I receive the claim payout?"
      - "Any update on my fire damage claim?"
      - "How long does claim processing usually take?"
```

## Intent → State Mapping

| Intent | Entry State | Workflow Branch |
|--------|-------------|-----------------|
| `get_quote` | `collect_property_info` | Quote |
| `file_claim` | `file_claim` | Claim |
| `check_coverage` | `lookup_policy` (sub-workflow, TBD) | Service |
| `renew_policy` | `collect_property_info` | Quote (renewal variant) |
| `update_policy` | `collect_property_info` | Quote (update variant) |
| `cancel_policy` | `confirm_cancellation` (TBD) | Service |
| `ask_about_claim_status` | `lookup_claim` (TBD) | Service |

> **Note:** `check_coverage`, `cancel_policy`, and `ask_about_claim_status` are mapped to service sub-workflows not yet defined in the current `workflow.yaml`. See [open questions](../../specs/2026-06-16-state-machine-design.md#appendix-c-implementation-planning--open-questions-state-machine) C.1 for sub-workflow design.
