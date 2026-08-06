# Stripe — Merchant Onboarding Analysis (#1 Overall)

> **Industry:** Fintech / Payment Infrastructure | **Onboarding Type:** API-First Merchant KYC/KYB | **Overall:** 5.0/5 | **Date:** 2026-08-05

---

## Executive Summary — Why Stripe is #1

Stripe's onboarding is the most complete system in fintech. Three innovations define it:

**1. capability-based entitlement (the single best pattern in this research).** Instead of one "verified/not verified" binary, each feature has its own status. A merchant can have `card_payments = active` while `transfers = pending` — accepting payments before their bank account is fully verified. QBO's equivalent: `basic_reports = active`, `payroll = pending KYC`, `tax_filing = pending EIN verification`. This ONE pattern replaces QBO's entire all-or-nothing access model.

**2. ML silent verification (80%+ auto-approved, zero document upload).** Stripe's Radar ML scans the merchant's website with an LLM, cross-references the business against Secretary of State databases, verifies identity against credit bureaus — all silently. If everything matches, the merchant is approved without ever seeing a document upload screen. QBO currently asks EVERY user to manually enter EIN, business address, and upload formation documents — even though Intuit already has their TurboTax data, Mint transaction history, and Credit Karma credit profile.

**3. Embedded components (any SaaS platform becomes a payment facilitator).** Stripe's React SDK renders a fully compliant, mobile-optimized KYC/KYB form inside any partner's UI. Shopify, Squarespace, and thousands of platforms use this. The partner's users never leave the platform, never create a separate Stripe account, and never re-enter data the platform already has. QBO has NO equivalent — ISV partners must redirect users to Intuit's signup flow.

**Concrete numbers:** Stripe Connect powers 2M+ businesses on platforms. The Payments Foundation Model recovered $6B in false declines (2024). Authorization Boost improved approval rates without increasing fraud losses. AI Smart Disputes increased chargeback win rates by 13%.

---

## Detailed Comparison: QBO vs Stripe

### Field Collection — What You Actually See
| Scenario | Stripe | QBO |
|----------|--------|-----|
| **Sole proprietor, US, card payments only** | ~15 fields. SSN last 4. Full SSN and EIN are `eventually_due` (triggered at $1,500 volume or 30 days — whichever is LATER) | ~25 fields. Full SSN, full EIN, full business address, business type, industry code, bank account — ALL upfront |
| **LLC with 3 owners** | ~20 fields at signup. Beneficial owner fields (DOB, SSN last-4, address, ownership %) only appear IF ownership >25%. One owner with 15% = never asked | Same ~25 fields regardless of entity type. QBO doesn't distinguish between entity types in its onboarding form |
| **What happens if you stop halfway?** | Account exists. Onboarding link works. Can resume anytime. `charges_enabled = false` but account object is real | Application abandoned. Must restart. No partial-save for new users without an Intuit account |
| **Pre-fill from existing data** | Platform passes name, email, DOB, address, business type, URL, MCC, estimated volume — user CONFIRMS, doesn't type | Intuit HAS TurboTax income data, Mint bank connections, Credit Karma credit profile, and QuickBooks Payroll employer data — but QBO doesn't pre-fill any of it |

### Risk Decision — What Actually Happens Behind the Scenes
| Scenario | Stripe | QBO |
|----------|--------|-----|
| **Clean match: business website matches stated industry, SSN+DOB matches credit bureau, OFAC clear** | Auto-approved in seconds. No human review. No doc upload. `charges_enabled = true` immediately | Manual review takes 1-3 days. IRS database check only. No website scan, no business registry cross-reference |
| **Mismatch: stated address ≠ Secretary of State records** | `requirements.errors` shows `invalid_street_address` with human-readable fix: "The provided street address cannot be found. Please verify the street name and number." Merchant fixes and resubmits | Application goes into review queue. User gets email: "Additional information needed." No specific field guidance |
| **High-risk: crypto exchange, gambling, adult** | Stripe may reject outright, OR apply rolling reserve (10-30% of transactions held 90-180 days) + higher processing fees. Transparent about why | QBO has no equivalent risk tiering. Either approves or denies. No "approve with conditions" |

### Entitlement — What You Can Actually Do
| Scenario | Stripe | QBO |
|----------|--------|-----|
| **Just signed up, no verification** | Account object exists. Onboarding link works. GET capabilities return all `pending`. Nothing charged yet | Nothing. Must complete setup before seeing any dashboard |
| **Minimal KYC submitted (name, DOB, last-4 SSN, bank)** | `card_payments = active`. Can accept payments. `transfers.status = active` but first payout held 7-14 days. | No equivalent progressive model |
| **Full KYC complete** | All standard capabilities active. Payouts T+2. Rolling reserve may apply. | Full access — one-time grant, never revoked unless account closed |
| **6+ months clean history, low chargebacks** | Reserve reduced/removed. Instant Payouts eligible (~30 min, 0.5% fee). Custom pricing available | No behavior-based entitlement graduation |

### What QBO Should Actually Do — Not Theory, Specific Actions
| Priority | Action | Model From Stripe | Impact |
|----------|--------|-----------------|--------|
| **P0** | Add `currently_due` vs `eventually_due` fields concept. User sees "3 things needed to start" vs "5 things needed before you can file taxes" | Stripe account requirements API | Cuts initial form from 25 fields to ~12. Deferred SSN/EIN to tax/payroll activation |
| **P0** | Implement capability status per feature: `bank_connections`, `reports`, `invoicing`, `payroll`, `tax_filing` — each independently `pending` / `active` / `inactive` | Stripe Connect capabilities model | Users who just want to see reports can start immediately. Payroll/tax filing gated behind EIN verification |
| **P1** | Auto-verify businesses via Secretary of State API + IRS TIN matching BEFORE asking users to upload documents. Only surface document upload when API checks fail | Stripe Radar ML silent verification | Could match Stripe's 80% auto-approval rate for existing Intuit customers (TurboTax data already IRS-verified) |
| **P1** | Expose an embedded QBO onboarding component (React SDK) that ISV partners can render inside their own UI | Stripe Connect Embedded Components | Accountants/ISVs could offer QBO signup without users leaving their platform |

---

## Analysis Sections
- [01 — Fields Collected & Collection Strategy](01-fields-collected.md)
- [02 — Risk Decision Process](02-risk-decision.md)
- [03 — Entitlement Model](03-entitlement.md)
- [04 — UI/UX Flow & Agentic Experience](04-ui-ux-flow.md)
- [05 — SWOT vs Intuit QuickBooks](05-swot-vs-qbo.md)

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
| 2026-08-06 | Enhanced Executive Summary and QBO Comparison with concrete scenarios |
