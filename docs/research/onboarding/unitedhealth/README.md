# UnitedHealth Group (UNH) — Health Insurance Consumer Onboarding Analysis

> **Industry:** Healthcare / Health Insurance
> **Onboarding Type:** Consumer (Policyholder + Member)
> **Sensitive Data:** Yes — PHI (Protected Health Information) under HIPAA
> **Analysis Date:** 2026-08-05

---

## Executive Summary

UnitedHealth Group is the largest US health insurer (50M+ members, ~14% of US population). Their onboarding is fundamentally different from financial KYC: it is governed by HIPAA (not BSA/AML), involves PHI collection (not credit checks), and features multiple acquisition channels — employer-sponsored auto-enrollment, ACA marketplace exchange, Medicare Advantage (CMS-regulated), and direct-to-consumer. The defining tension: employer auto-enrollment has zero friction, but individual consumers face high drop-off from premium sticker shock. UNH's Optum division uses AI for prior authorization — a controversial practice with documented high denial rates that has drawn Congressional scrutiny.

| Dimension | Rating (1-5) | Why |
|-----------|-------------|-----|
| Field Minimization | 2 | Heavy upfront collection: SSN, DOB, full address, dependents, medical history, PCP selection, Rx list, payment. Field count varies dramatically by channel. |
| Pre-fill Strategy | 4 | Employer channel: HR system integration pre-fills everything. Marketplace: HealthCare.gov API pre-fills subsidy eligibility. Medicare: CMS data cross-reference. |
| Risk Intelligence | 3 | MIB (Medical Information Bureau) check, PBM database cross-ref, SSN identity verification. NO credit check (unlike banking). Risk is medical underwriting, not creditworthiness. |
| Conversion Optimization | 2 | Employer channel = auto-enrollment (zero friction). Individual channel = high drop-off from premium sticker shock and medical questionnaire abandonment. No "try before you buy." |
| Agentic/AI Experience | 3 | Optum AI prior auth (controversial), symptom checker chatbot, plan selection Q&A bot, automated claims. Ahead of most insurers, behind fintech. |
| Entitlement Design | 3 | Digital insurance card issued immediately; physical card 7-14 days. Prior authorization gates access to procedures behind medical necessity review. Progressive access by plan tier. |
| **Overall** | **2.8** | Employer auto-enrollment is best-in-class frictionless. Individual onboarding is burdensome. Optum AI controversy creates trust deficit. Healthcare's regulatory constraints inherently limit UX innovation. |

**One-sentence verdict:** UNH's employer auto-enrollment is the zero-friction gold standard, but individual consumer onboarding is a compliance-heavy, high-drop-off experience — and Optum's AI-driven prior authorization creates a fundamental trust problem that no amount of UX polish can fix.

---

## Quick Comparison: QBO vs UnitedHealth Group

| Dimension | QuickBooks Online | UnitedHealth Group | Gap |
|-----------|-------------------|--------------------|-----|
| Steps to complete | 15-25 | 8-30+ (varies by channel) | UNH wider range; employer is faster than QBO |
| Fields required | 25-30 | 15-40 (varies by channel) | UNH more variable; employer pre-fill reduces count |
| ID verification method | Email + SSN + bank verify | SSN + DOB + MIB cross-ref | UNH: medical database check, no credit check |
| Instant entitlement | Full access after setup | Digital card immediate; physical 7-14 days; prior auth gated | UNH: access is layered, not binary |
| Pre-fill capabilities | Bank connection (Plaid) | Employer HR system, HealthCare.gov API, CMS data | UNH pre-fill exceeds QBO in breadth |
| AI/agentic features | None | Optum AI prior auth, symptom checker, plan chatbot | UNH ahead on AI, behind on UX polish |

---

## Analysis Sections

- [01 — Fields Collected & Collection Strategy](01-fields-collected.md)
- [02 — Risk Decision Process](02-risk-decision.md)
- [03 — Entitlement Model](03-entitlement.md)
- [04 — UI/UX Flow & Agentic Experience](04-ui-ux-flow.md)
- [05 — SWOT vs Intuit QuickBooks](05-swot-vs-qbo.md)

---

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation — UnitedHealth Group analysis |
