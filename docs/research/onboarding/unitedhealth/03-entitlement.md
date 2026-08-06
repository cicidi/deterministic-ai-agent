# UnitedHealth Group — Entitlement Model

## Core Insight

**Healthcare entitlement is a two-phase model: membership activation (instant digital card) AND service access (gated behind prior authorization).** This is fundamentally different from banking/fintech where entitlement is purely about transaction limits. In healthcare, the "transaction" is a medical procedure or prescription — and access is gated by medical necessity review, not just identity verification.

```mermaid
stateDiagram-v2
    [*] --> Unenrolled: No coverage
    state Unenrolled { Browse plans; Premium calculator; Provider directory search }
    state Enrolled_Pending { Digital card issued; PCP selection; Rx formulary access; No claims yet }
    state Active_Basic { Preventive care (no PA required); Generic Rx; Telehealth; Urgent care }
    state Active_Full { Specialist visits; Diagnostic tests; Brand-name Rx; Hospitalization (PA required) }
    state Active_Enhanced { Out-of-network coverage; DME; Home health; Experimental treatments (PA required) }
    state Lapsed { Coverage terminated; COBRA election window; Grace period }
    Unenrolled --> Enrolled_Pending: Enrollment + Identity verification + Payment
    Enrolled_Pending --> Active_Basic: First premium processed
    Active_Basic --> Active_Full: Prior authorization (per procedure)
    Active_Full --> Active_Enhanced: Prior authorization + Medical necessity review
    Active_Basic --> Lapsed: Non-payment (after grace period)
    Active_Full --> Lapsed: Non-payment (after grace period)
```

## Entitlement Gates

| Stage | Requirements | What's Unlocked | Limits / Gates |
|-------|-------------|-----------------|----------------|
| **Unenrolled** | None | Plan browsing, premium calculator, provider directory, formulary lookup, agent/broker consultation | Cannot access care; cannot see negotiated rates |
| **Enrolled (Pending)** | Identity verified, payment method validated, first premium scheduled | Digital insurance card (immediate via app/portal), PCP selection, member portal access, Rx formulary, cost estimator tool | No claims processed until first premium clears; physical card 7-14 days by mail |
| **Active — Basic** | First premium processed, PCP selected | Preventive care (no PA required): annual physical, vaccinations, screenings. Generic prescriptions. Telehealth visits. Urgent care. | Limited to in-network, no-referral services; $0 copay preventive only |
| **Active — Full** | Prior authorization (procedure-specific) | Specialist visits (referral required for HMO), diagnostic imaging (MRI/CT/PET), surgical procedures, brand-name prescriptions, hospitalization, mental health, physical therapy | Per-procedure PA required; step therapy for Rx; in-network only; annual deductible + OOP max apply |
| **Active — Enhanced** | Prior authorization + Medical Necessity Review | Out-of-network care, durable medical equipment, home health services, skilled nursing facility, experimental/clinical trial treatments | Stringent PA with higher denial rates; higher cost-sharing |
| **Lapsed** | Coverage terminated | COBRA continuation (18 months), Special Enrollment Period eligibility via Marketplace, grace period for reinstatement | No claims processed during lapse; reinstatement subject to waiting periods |

## Prior Authorization: The Critical Gate

Prior authorization is the defining entitlement mechanism in healthcare — and the most controversial aspect of UNH's model.

| PA Metric | Detail |
|-----------|--------|
| **Scope** | 30-40% of all medical services require prior authorization at UNH |
| **Decision Time** | Standard: 3-14 days. Expedited: 24-72 hours. Emergency: retroactive. |
| **Denial Rate (UNH)** | Estimated 15-25% initial denials (varies by plan type and service) |
| **Appeal Rate** | <1% of denials are appealed by patients (AMA estimate) |
| **Overturn Rate on Appeal** | 40-60% of appealed denials are overturned (suggesting over-denial at initial review) |
| **AI Role (Optum)** | Optum's AI-assisted PA system reviews claims, flags for denial, and in some cases auto-denies without human clinician review |
| **Controversy** | 2023-2024: Congressional investigation into Medicare Advantage PA denial rates. Class-action lawsuits alleging systematic AI-driven denial without proper medical review. CMS proposed rule (2024) requiring human review of all AI-assisted denials. |

---

## Takeaways for QBO

1. **Prior authorization = feature gating.** The PA model translates to software: certain features require "review" before access. QBO's equivalent: payroll features require EIN verification; tax filing requires SSN validation. This is already partially implemented.

2. **Digital-first entitlement.** UNH issues a digital card immediately on enrollment — before payment clears. QBO equivalent: grant dashboard access and basic features immediately on signup, gate advanced features (payroll, tax filing, accountant access) behind verification.

3. **The denial-to-overturn pipeline signals over-gating.** UNH's high overturn rate on appeal suggests the initial PA gate is too aggressive. QBO's risk: gating too many features behind verification will create the same pattern of high "denial" (blocked access) followed by manual override — undermining the automation rationale.

4. **Retroactive authorization exists in healthcare.** Emergency care is authorized retroactively. This pattern applies to any system where the cost of delay exceeds the cost of fraud: let the action proceed, review afterward, claw back if needed.

---

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
