# Home Insurance — End-to-End Scenarios

> Walkthroughs for [workflow.yaml](./workflow.yaml). Trace the full path from user input to completion.

---

## Scenario 1: Quote & Purchase

### Dialogue Flow

```
User:   "I want a home insurance quote for my apartment"

-- collect_property_info -----------------------------------------
  [LLM → stream]
  "Of course! Let me gather some details about your property.
   What type of property is it? And could you share the address,
   building age, floor area, and construction material?"

User:   "It's an apartment at 88 Nanjing Road, Shanghai 200001.
         Built in 2015, 95 square meters, concrete structure."

  [LLM + tool: lookup_property_record("88 Nanjing Road, Shanghai")]
  Internal: Property record verified. Flood zone: low. Crime rate: low.
  [output_schema populated: property_type=apartment, address=..., building_age=11, floor_area=95, construction_material=concrete]
  → guard passed: all required fields non-null → enter collect_coverage_needs

-- collect_coverage_needs ----------------------------------------
  [LLM → stream]
  "Great, your apartment is 95 sqm in a concrete building from 2015.
   What coverage do you need? Building only, contents only, or both?
   Also, what amount and deductible do you prefer?"

User:   "Both building and contents. Building 2,000,000 CNY,
         contents 500,000 CNY. Standard deductible is fine.
         Add fire and theft riders."

  [output_schema populated: coverage_type=both, building_coverage=2000000, contents_coverage=500000, deductible=standard, riders=[fire, theft]]
  → guard passed → enter assess_risk

-- assess_risk ---------------------------------------------------
  [code] compute_risk_score(age=11, material=concrete, flood_zone=low, crime_rate=low)
  → risk_score = 18 (low risk)
  → risk_factors = ["concrete_structure", "low_flood_zone", "low_crime"]
  → rate_multiplier = 0.8 + (18/250) = 0.872

  exit_guard: risk_score(18) < 70 → passed → enter calculate_premium

-- calculate_premium ---------------------------------------------
  [code] compute_home_premium:
    base_rate = 3.5 CNY per 1000 CNY coverage
    annual_premium = 3.5 * 0.872 * 2000000 / 1000 = 6,104 CNY
    monthly_premium = 508.67 CNY
    discount_applied = 0 (first year, no loyalty discount)

  exit_guard: annual_premium(6104) < 50000 → passed → enter present_quote

-- present_quote -------------------------------------------------
  [LLM → generate]
  "Here's your home insurance quote:

   Property: Apartment at 88 Nanjing Road, Shanghai 200001
   Coverage: Building 2,000,000 CNY + Contents 500,000 CNY
   Annual Premium: 6,104 CNY (508.67 CNY/month)
   Deductible: Standard (2,000 CNY)
   Riders: Fire, Theft

   Would you like to purchase this policy?"

  *** trigger interrupt(): paused, awaiting human approval ***

  --- audit: 2026-06-16 10:15:30 | present_quote | waiting_human ---

  Reviewer reviews quote → [Approve]

  --- audit: 2026-06-16 10:16:12 | present_quote | approved_by: agent_wang ---

User:   "Yes, I'll purchase it"

-- confirm_purchase ----------------------------------------------
  [code] create_home_policy()
  → policy_id: "HOM-2026-00142"
  → policy_status: active

  [LLM → stream]
  "Purchase confirmed! Your home insurance policy HOM-2026-00142 is active.
   Coverage effective immediately. You'll receive the policy document via email."

  → enter done

-- done ----------------------------------------------------------
  [code] log_conversation() → audit trail archived
```

### Key Design Points

| Feature | How Demonstrated |
|---------|-----------------|
| LLM info collection | `collect_property_info`, `collect_coverage_needs` — conversational data gathering |
| Tool calling | `lookup_property_record` called by LLM to verify address |
| Deterministic business logic | `assess_risk`, `calculate_premium` — pure code, no LLM |
| Guard-based routing | `exit_guard: risk_score < 70` prevents high-risk auto-approval |
| Human-in-the-loop | `present_quote` triggers interrupt for compliance review |
| Guard meta-variables | `context_incomplete`, `exit_guard_pass` auto-managed by framework |

### Audit Log (Quote Path)

```json
[
  {"ts":"10:15:00","state":"collect_property_info", "action":"llm_query",  "tokens":120, "output":"property_type=apartment,address=..."},
  {"ts":"10:15:05","state":"collect_property_info", "action":"tool_call",  "tool":"lookup_property_record", "args":{"address":"88 Nanjing Road, Shanghai"}, "result":{"flood_zone":"low","crime_rate":"low"}},
  {"ts":"10:15:05","state":"collect_property_info", "action":"transition", "from":"collect_property_info","to":"collect_coverage_needs","guard":"all_fields_present","result":"passed"},
  {"ts":"10:15:15","state":"collect_coverage_needs", "action":"transition", "from":"collect_coverage_needs","to":"assess_risk","guard":"building_coverage>0","result":"passed"},
  {"ts":"10:15:15","state":"assess_risk",           "action":"code_exec",  "fn":"compute_risk_score","input":{"age":11,"material":"concrete"},"result":{"risk_score":18,"rate_multiplier":0.872}},
  {"ts":"10:15:15","state":"assess_risk",           "action":"transition", "from":"assess_risk","to":"calculate_premium","guard":"exit_guard_pass","result":"passed"},
  {"ts":"10:15:15","state":"calculate_premium",     "action":"code_exec",  "fn":"compute_home_premium","result":{"annual_premium":6104,"monthly_premium":508.67}},
  {"ts":"10:15:15","state":"calculate_premium",     "action":"transition", "from":"calculate_premium","to":"present_quote","guard":"annual_premium<50000","result":"passed"},
  {"ts":"10:15:30","state":"present_quote",         "action":"interrupt",  "reason":"human_review"},
  {"ts":"10:16:12","state":"present_quote",         "action":"approved",   "approver":"agent_wang"},
  {"ts":"10:16:15","state":"present_quote",         "action":"transition", "from":"present_quote","to":"confirm_purchase","guard":"user_says_yes","result":"passed"},
  {"ts":"10:16:15","state":"confirm_purchase",      "action":"code_exec",  "fn":"create_home_policy","result":{"policy_id":"HOM-2026-00142","status":"active"}},
  {"ts":"10:16:15","state":"done",                  "action":"complete"}
]
```

---

## Scenario 2: File & Settle Claim

### Dialogue Flow

```
User:   "There was a fire in my kitchen last night, I need to file a claim"

-- file_claim ----------------------------------------------------
  [LLM → stream]
  "I'm sorry to hear that. I'll help you file a claim right away.
   First, can you tell me:
   - When exactly did the incident happen?
   - Can you describe the damage?
   - What's your estimated loss amount?
   - Do you have any photos you can upload?"

User:   "It happened yesterday evening around 8pm, June 10th.
         Kitchen cabinets and appliances damaged by fire and smoke.
         I estimate about 80,000 CNY in damage.
         Here are the photos." [uploads 3 images]

  [LLM + tool: upload_attachment(img1,img2,img3)]
  [LLM + tool: lookup_policy(user_id) → policy_id=HOM-2026-00142, status=active]

  output:
    incident_type = "fire"
    incident_date = "2026-06-10"
    damage_description = "Kitchen cabinets and appliances damaged by fire/smoke"
    estimated_loss = 80000
    attachments = ["img_001.jpg", "img_002.jpg", "img_003.jpg"]

  → guard passed → enter validate_claim

-- validate_claim ------------------------------------------------
  [code] run_claim_validations:
    Step 1: check_policy_active("HOM-2026-00142") → active ✓
    Step 2: check_incident_covered("fire") → fire is covered ✓
    Step 3: check_incident_in_period("2026-06-10", policy_start) → within coverage ✓
    Step 4: check_duplicate_claim("fire", "2026-06-10") → no duplicate ✓
  validation_passed: true
  coverage_limit: 2000000  (building coverage)

  exit_guard: validation_passed → enter assess_damage

-- assess_damage -------------------------------------------------
  [LLM + tool: estimate_repair_cost(kitchen_fire, photos=[...])]
  → adjuster_report: {
      damage_type: "fire_smoke",
      affected_areas: ["kitchen_cabinets", "countertops", "appliances", "wall_repaint"],
      repair_estimate: 75000,
      replacement_estimate: 85000,
      recommended: "repair"
    }

  assessed_amount = 75000
  deductible = 2000 (standard)
  covered_amount = min(75000 - 2000, 2000000) = 73000

  exit_guard: assessed_amount(75000) > 0 → enter approve_claim

-- approve_claim -------------------------------------------------
  [LLM → generate]
  "Claim assessment complete:

   Incident: Kitchen fire on 2026-06-10
   Assessed Damage: 75,000 CNY
   Deductible: 2,000 CNY
   Covered Amount: 73,000 CNY
   Coverage Limit: 2,000,000 CNY

   Your claim is ready for approval."

  *** trigger interrupt(): paused, awaiting human approval ***

  --- audit: 2026-06-11 09:30:45 | approve_claim | waiting_human ---

  Claims adjuster reviews → [Approve]

  --- audit: 2026-06-11 09:45:00 | approve_claim | approved_by: adjuster_li ---

-- process_claim_payment -----------------------------------------
  [code] execute_claim_payout:
    idempotency_key = "idem_claim_HOM-2026-00142_fire_20260610"
    POST /payouts {policy_id: "HOM-2026-00142", amount: 73000, key: "idem_..."}
    → payout_id: "PAY-2026-00842"
    → payout_status: "completed"

  postcondition: payout_id="PAY-2026-00842" passed

  [LLM → stream]
  "Claim approved and payout processed! 73,000 CNY has been transferred
   to your registered account. Payout reference: PAY-2026-00842.
   You'll receive a detailed settlement letter by email."

  → enter done

-- done ----------------------------------------------------------
  [code] log_conversation() → audit trail archived
```

### Key Design Points

| Feature | How Demonstrated |
|---------|-----------------|
| Intent-based entry routing | `intent=file_claim` enters claim branch from `start` |
| Tool-augmented LLM | `upload_attachment`, `estimate_repair_cost` called during LLM states |
| Multi-step deterministic validation | `validate_claim` runs 4 checks as pure code |
| Deductible + coverage limit math | `assess_damage` computes `covered_amount = assessed - deductible`, capped at limit |
| Idempotent payout | `process_claim_payment` uses `idempotency_key` to prevent duplicate transfers |
| Error recovery path | `on_error: claim_error_recovery` catches payment gateway failures |

---

## Scenario 3: High Risk → Manual Review → Rejection

```
User:   "I want a quote for my wooden villa in a flood zone"

-- collect_property_info -----------------------------------------
  → property_type=villa, building_age=45, construction_material=wood_frame
  → flood_zone detected via lookup_property_record: "high"

-- collect_coverage_needs ----------------------------------------
  → coverage_type=both, building_coverage=5000000, deductible=standard

-- assess_risk ---------------------------------------------------
  [code] compute_risk_score(age=45, material=wood_frame, flood_zone=high)
  → risk_score = 91 (very high risk)
  → risk_factors = ["wood_frame_structure", "building_age_45", "high_flood_zone"]
  → rate_multiplier = 1.164

  exit_guard: risk_score(91) < 70 → FAILED
  exit_guard_blocked → routed to high_risk_review (NOT calculate_premium)

-- high_risk_review ----------------------------------------------
  *** trigger interrupt(): entered underwriter review queue ***

  Underwriter reviews → [Reject]
  Reason: "Flood zone high, wood frame — risk exceeds underwriting guidelines"

  guard: manual_review_rejected → enter done
  → Workflow ends without quote
```

This scenario demonstrates **guard-based alternate routing**: the `exit_guard` on `assess_risk` actively blocks the normal path and redirects to manual review, where a human makes the final decision.

---

## Cross-Reference

| Concept | Quote Path | Claim Path |
|---------|-----------|------------|
| LLM data collection | `collect_property_info` | `file_claim` |
| Deterministic validation | `assess_risk` | `validate_claim` |
| LLM assessment | — | `assess_damage` |
| Human review | `present_quote` | `approve_claim` |
| Irreversible operation | `confirm_purchase` | `process_claim_payment` |
| Error recovery | `error_recovery` | `claim_error_recovery` |
| Guard routing | `exit_guard: risk_score < 70` | `exit_guard: validation_passed` |
