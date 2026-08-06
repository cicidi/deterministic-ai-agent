# Plaid — Developer Onboarding Analysis (#3 Overall)

> **Industry:** Fintech / Data Infrastructure | **Onboarding Type:** B2B Developer KYB + Bank Auth | **Overall:** 4.8/5 | **Date:** 2026-08-05

---

## Executive Summary — Why Plaid is #3

Plaid proves that even the highest-trust industry (access to consumer banking credentials) can be self-serve. Their April 2026 **Trial Plan** is the most elegant "build first, approve later" model in fintech:

**The breakthrough:** A developer signs up (name, email, password — 3 fields). Gets instant Sandbox access to ALL Plaid APIs with fake data. Clicks "Get Production Access" → identity verified (auto-approved) → gets 10 real Items, 8 core products (Auth, Transactions, Balance, Identity, Assets, Liabilities, Investments, Statements), access to major OAuth banks (Chase, BofA, Wells Fargo) — NO security questionnaire, NO MSA addendum, NO company registration required. Only when they need >10 Items or additional products does the full 25-question security review kick in.

**QBO equivalent:** Sign up with email → explore demo company → connect 1 real bank → see 10 auto-categorized transactions → run 1 basic report. NO full business verification, NO EIN, NO SSN upfront. Full verification only when user tries to run payroll, file taxes, or exceed 10 transactions.

**Concrete numbers:** 12,000+ financial institutions. 8,000+ apps/developers. 5-tier access. Trial Plan (April 2026) includes Chase, Wells Fargo, Bank of America. MCP Server + Sandbox MCP Server + AI Development Toolkit for Cursor/Claude Code/Windsurf.

---

## Detailed Comparison: QBO vs Plaid

### Field Collection
| Scenario | Plaid | QBO |
|----------|-------|-----|
| **First 30 seconds** | 3 fields: name, email, password. Instant Sandbox access. All APIs unlocked with fake data | ~25 fields on screen 1. No sandbox. No value until form complete |
| **Developer wants real data** | Trial Plan: identity verified → 10 real Items, 8 products, major OAuth banks. Auto-approved. No security review | QBO doesn't have a "capped scope auto-approved" tier at all |
| **Developer needs unlimited access** | Production Application + company profile + per-product use case + beneficial owners + MSA + 25-question security review. Days | Always full form upfront regardless of scope |
| **Pre-fill** | DNS domain verification via WorkOS. Otherwise minimal | Intuit has TurboTax, Mint, Credit Karma data but doesn't pre-fill QBO |

### Risk Decision
| Scenario | Plaid | QBO |
|----------|-------|-----|
| **New developer, wants to build a budgeting app** | Sandbox: instant. Trial: auto-approved. Plaid checks identity, verifies email domain. 10-Item cap + 8-product bundle = limited blast radius | QBO has no equivalent — no scoped access, no usage-based escalation |
| **Developer wants consumer bank credentials (Auth)** | Per-product use case justification. "We need to verify account ownership for ACH funding." Risk team reviews. Approved or additional questions | No per-product justification. One approval for everything |
| **Developer requests Income product (payroll data)** | NOT in Trial bundle. Requires full Production approval + separate use case justification. Risk team reviews income verification use case | No equivalent granular product gating |
| **Ongoing: 12-month reauthorization** | CFPB Section 1033 mandates Update Mode every 12 months. Periodic trust refresh | No periodic re-verification |

### Entitlement
| Tier | Plaid | QBO Equivalent (Should Be) |
|------|-------|--------------------------|
| **Sandbox** | All APIs, fake data, unlimited Items. 0 fields beyond signup | Demo company with fake transactions, fake reports, fake invoices |
| **Trial (auto-approved)** | 10 real Items, 8 products, OAuth banks. Identity verification only | 10 real bank transactions, basic P&L, basic invoicing. Identity only |
| **Production** | Unlimited Items, all products. Full compliance review | Unlimited transactions, payroll, tax filing. Full KYC/KYB |
| **Per-product addition** | Each product (Income, Assets, Signal) requires separate justification | Payroll, tax filing, ACH, credit each require separate activation |

### What QBO Should Actually Do
| Priority | Action | Model From Plaid | Impact |
|----------|--------|-----------------|--------|
| **P0** | 3-field signup: email, name, password → instant demo company with fake data | Plaid Sandbox | Users explore QBO before committing personal data. 30 seconds to first value |
| **P0** | Trial tier: 10 real bank transactions, auto-approved. Full verification only to exceed cap or activate payroll/tax | Plaid Trial Plan (10 Items, 8 products, no security review) | ~80% of users who just want to try QBO could start immediately |
| **P1** | Per-feature activation: payroll requires EIN. Tax filing requires full SSN. ACH requires bank micro-deposit confirmation. Each is a separate activation flow, not one giant upfront form | Plaid per-product use case justification | Users activate only what they need, when they need it |
| **P2** | MCP server + Sandbox MCP server for AI coding assistants (Cursor, Claude Code) to auto-generate QBO integrations | Plaid Sandbox MCP + AI Dev Toolkit | ISV developers integrate QBO in minutes, not days |

---

## Analysis Sections
- [01 — Fields Collected](01-fields-collected.md)
- [02 — Risk Decision](02-risk-decision.md)
- [03 — Entitlement Model](03-entitlement.md)
- [04 — UI/UX & Agentic](04-ui-ux-flow.md)
- [05 — SWOT vs QBO](05-swot-vs-qbo.md)

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
| 2026-08-06 | Enhanced Executive Summary and QBO Comparison with concrete scenarios |
