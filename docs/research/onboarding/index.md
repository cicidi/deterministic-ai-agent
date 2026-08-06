# Onboarding Research — Sensitive Data Collection Analysis

> **100+ companies. 5 industries. One question: how do you collect sensitive data, minimize risk, and maximize conversion?**

---

## What This Research Covers

Every regulated company faces the same trade-off: **more verification = less fraud, but fewer customers.** This research analyzes how the world's best companies solve this problem — what fields they collect, how they decide risk, what access they grant at each stage, and how their UX design minimizes drop-off.

### Industries Covered

| Industry | Companies (target) | Key Sensitive Data |
|----------|-------------------|--------------------|
| **Fintech / Payments** | 25+ | SSN, bank account, tax ID, identity docs |
| **Banking** | 20+ | Full KYC, income, assets, credit history |
| **Healthcare** | 20+ | PHI, insurance ID, medical history, SSN |
| **Insurance** | 15+ | Property details, driving record, health data, SSN |
| **Crypto / Web3** | 10+ | Identity docs, wallet addresses, source of funds |
| **Other Regulated** | 10+ | Industry-specific sensitive data |

### Analysis Framework

Every company is analyzed across 5 dimensions:

| Dimension | Key Questions |
|-----------|---------------|
| **Fields Collected** | WHAT do they collect? HOW (progressive, multi-step, single-page)? WHY each field? How do they minimize? |
| **Risk Decision** | KYC/KYB tiers, fraud detection signals, sanctions screening, decision logic, ongoing monitoring |
| **Entitlement Model** | What can users do at each verification stage? How do limits graduate with trust? |
| **UI/UX Flow** | Step-by-step flow, friction points, AI/agentic features, mobile vs desktop, drop-off analysis |
| **SWOT vs QBO** | Strengths, weaknesses, opportunities, threats. Direct comparison with QuickBooks Online. |

### The Core Trade-off

```
                    More Fields Collected
                         ↑
                    Lower Risk
                         ↑
    ←──────────────────────┼──────────────────────→
                    Higher Drop-off          Higher Conversion
                         ↓                        ↓
                    Fewer Customers          Higher Fraud Risk
```

The best companies don't pick a side — they **break the trade-off** through:

1. **Progressive disclosure** — ask for the right info at the right time, not everything upfront
2. **Silent verification** — check databases first, surface document requests only on mismatch
3. **Gating outflow, not inflow** — let users engage immediately, restrict sensitive actions behind verification
4. **Post-approval underwriting** — let users transact, investigate later, retroactively enforce if needed
5. **AI/agentic assistance** — chatbots, smart form fill, document scanning, real-time validation

---

## Companies Analyzed

| # | Company | Industry | Type | Rating | Key Insight |
|---|---------|----------|------|--------|-------------|
| 1 | [PayPal](paypal/README.md) | Fintech / Payments | Merchant (KYC+KYB) | 4.7/5 | Gates on outflow, not inflow — instant receive + delayed withdraw |
| 2 | [Stripe](stripe/README.md) | Fintech / Payments | Merchant (KYC+KYB) — API-first | 5.0/5 | Capability-based entitlement + ML silent verification + "create first, verify later" |
| 3 | [Square](square/README.md) | Fintech / POS + Banking | Hardware-anchored PayFac | 4.3/5 | Hardware as onboarding anchor + ecosystem-driven progressive access |
| 4 | [Plaid](plaid/README.md) | Fintech / Data Infrastructure | Developer (KYB + Bank Auth) | 4.8/5 | 5-tier progressive access + per-product justification + Trial Plan skips security review |
| 5 | [Robinhood](robinhood/README.md) | Fintech / Consumer Investing | Consumer KYC (FINRA regulated) | 4.0/5 | 11-field single-field-per-screen + try-before-you-buy + $1K instant deposit |
| 6 | [Coinbase](coinbase/README.md) | Crypto / Digital Assets | Consumer + Institutional KYC | 4.2/5 | Learn to Earn builds stake before KYC — most innovative onboarding hook |
| 7 | [Chime](chime/README.md) | Fintech / Neobank | Consumer KYC — Second-Chance | 4.0/5 | No ChexSystems + behavior-driven SpotMe/MyPay + 2-min mobile signup |
| 8 | [Revolut](revolut/README.md) | Fintech / Global Neobank | Consumer + Business | 4.3/5 | Geographic KYC adaptation — same UX, jurisdiction-specific requirements |
| 9 | [Klarna](klarna/README.md) | Fintech / BNPL | Consumer KYC — Post-Transaction | 4.1/5 | Email+ZIP at checkout, KYC AFTER purchase — inverts verify-then-transact |
| 10 | [Wise](wise/README.md) | Fintech / Cross-Border | Consumer + Business KYC/KYB | 4.4/5 | Progressive: transfer amount = verification depth |
| 11 | [Bank of America](bank-of-america/README.md) | Banking / Traditional | Consumer + Business KYC/KYB | 2.8/5 | Traditional bank baseline — heavy KYC upfront, excellent pre-fill for existing, SafeBalance fallback |
| 12 | [Chase](chase/README.md) | Banking / Traditional | Consumer + Business KYC/KYB | 3.2/5 | EWS co-owner = best fraud data in US banking. Credit Journey as no-obligation funnel |
| 13 | [UnitedHealth Group](unitedhealth/README.md) | Healthcare / Health Insurance | Consumer (Policyholder + Member) | 2.8/5 | Employer auto-enrollment = zero-friction gold standard. Individual onboarding is a HIPAA compliance form-fest. Optum AI prior auth creates trust deficit. |
| 14 | Wells Fargo | Banking / Traditional | Consumer + Business KYC/KYB | Coming soon | — |
| ... | ... | ... | ... | ... | ... |

---

## Methodology

See [Methodology](_templates/METHODOLOGY.md) for research methodology, sources, and quality standards.

---

## Quick Navigation

- [Summary & Top 10 Recommendations](_summary/index.md) — once 50+ companies are analyzed
- [Methodology](_templates/METHODOLOGY.md)
- [PayPal — Pilot Company](paypal/README.md)

---

*Research initiative: `onboarding-research`. Last updated: 2026-08-05.*
