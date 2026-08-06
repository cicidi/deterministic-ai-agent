# Summary & Top 10 Recommendations

> **Status:** Complete — 101 companies analyzed across 6 industries
> **Last updated:** 2026-08-05

---

## 🏆 Top 10 Companies

### #1 — Stripe (5.0/5)
**Industry:** Fintech / Payment Infrastructure | **Type:** API-First Merchant KYC/KYB

**Why #1:** Stripe achieves what no other company does — *capability-based entitlement* where every feature independently tracks its own verification status (`card_payments.status`, `transfers.status`). Combined with ML-powered silent verification (80%+ auto-approved without document upload), "create first, verify later" account creation, and embedded onboarding components that let any SaaS platform become a payment facilitator. The Payments Foundation Model (Radar ML) recovered $6B in false declines. Agentic AI: MCP Server, Link AI Wallet, Issuing for Agents.

**Pattern to steal:** Capability-based entitlement — replace binary "access/no access" with granular per-feature gating.

---

### #2 — PayPal (4.7/5)
**Industry:** Fintech / Digital Payments | **Type:** Merchant KYC/KYB

**Why #2:** PayPal's *"gates on outflow, not inflow"* is the single most important design pattern in fintech onboarding. Merchants can receive payments 30 seconds after signup — but withdrawal is blocked until KYC completes. 4-tier progressive trust (email → bank → KYC → KYB) with data-driven graduation. 439M+ accounts generating the richest 2-sided network fraud data in payments. Agentic Commerce partnerships with Anthropic, Google, AWS, Microsoft.

**Pattern to steal:** Gate outflow not inflow — let users engage instantly, block sensitive actions behind progressive KYC.

---

### #3 — Plaid (4.8/5)
**Industry:** Fintech / Data Infrastructure | **Type:** Developer KYB + Bank Auth

**Why #3:** Plaid proves that even the highest-trust industry (consumer banking credentials) can be self-serve. 5-tier progressive access (Sandbox → Trial → Legacy Limited → Production → Custom). The April 2026 Trial Plan is the breakthrough: auto-approved 10-Item real data with 8 products, NO security questionnaire. MCP Server for AI coding assistants. Plaid Link embedded in Fin/Sierra AI agents for abandoned flow recovery.

**Pattern to steal:** Trial Plan model — auto-approved, capped-scope real data access as hook; full verification to exceed cap.

---

### #4 — Lemonade (4.5/5)
**Industry:** Insurtech | **Type:** AI-First Renters/Home/Pet/Life

**Why #4:** Lemonade's Maya AI chatbot handles the entire onboarding — quote → underwrite → bind → issue policy in *90 seconds*. Jim AI claims bot settled a claim in 2 seconds. This proves conversational AI can replace forms entirely for regulated onboarding. The Giveback program (donates unclaimed premiums to charity) uses behavioral economics to reduce fraud — no anti-fraud KYC burden needed.

**Pattern to steal:** Conversational AI onboarding — "Tell me about your business" replaces 25-field forms.

---

### #5 — Klarna (4.1/5)
**Industry:** Fintech / BNPL | **Type:** Consumer KYC — Post-Transaction

**Why #5:** Klarna inverted the entire KYC paradigm: *KYC happens AFTER the purchase, not before.* Consumer enters email + ZIP at checkout → Klarna runs millisecond soft credit check → approves → purchase completes → KYC happens later. This is the ultimate "verify after, not before" model. 150M+ users, 500K+ merchants. 20-30% conversion lift for merchants.

**Pattern to steal:** Post-transaction KYC — defer full verification until after value is delivered.

---

### #6 — Robinhood (4.0/5)
**Industry:** Fintech / Consumer Investing | **Type:** Consumer KYC (FINRA Regulated)

**Why #6:** Robinhood's *11-field, single-field-per-screen* signup + *"try-before-you-buy" sandbox* (explore the app and place fake trades before entering ANY personal data) redefined consumer finance onboarding. Free stock ($5-$200) as signup incentive. $1,000 instant deposit while ACH settles. Cortex AI investing assistant (95% satisfaction).

**Pattern to steal:** Single-field-per-screen + try-before-you-buy sandbox.

---

### #7 — Coinbase (4.2/5)
**Industry:** Crypto / Exchange | **Type:** Consumer + Institutional KYC

**Why #7:** Coinbase's *"Learn to Earn"* is the most innovative onboarding hook in fintech. Users earn $1-5 of crypto from educational content — building a stake BEFORE being asked for KYC. The crypto sits in their account, untouchable until they verify. User now has skin in the game and voluntarily completes KYC. 108M+ verified users.

**Pattern to steal:** Learn to Earn / stake-building — give users assets before asking for identity.

---

### #8 — Chime (4.0/5)
**Industry:** Fintech / Neobank | **Type:** Consumer KYC — Second-Chance Banking

**Why #8:** Chime proved that *rejecting ChexSystems + credit checks* opens the largest addressable market in consumer banking. Behavior-driven entitlement: SpotMe overdraft ($20-200) and MyPay wage advance ($500) unlock based on direct deposit history, not credit score. 2-minute mobile-only signup. 4.8★ App Store (750K+ reviews).

**Pattern to steal:** Behavior-driven entitlement — feature unlocks based on usage data, not credit scores.

---

### #9 — Brex (4.5/5)
**Industry:** Fintech / Corporate Spend | **Type:** Startup-First KYB

**Why #9:** Brex pioneered *"no personal guarantee" corporate cards* — underwriting based on company bank balance and investor backing, not founder FICO. NO personal SSN, NO personal credit check. Plaid instant bank verification. Plaid + Crunchbase/PitchBook data for underwriting. Proved that company financial data can replace personal credit for SMB underwriting.

**Pattern to steal:** Business data as credit score — QBO transaction history IS the underwriting signal.

---

### #10 — Progressive Insurance (4.6/5)
**Industry:** Insurance / Auto | **Type:** Consumer P&C

**Why #10:** Progressive's *Name Your Price tool* inverts the entire quoting paradigm — user enters budget, Progressive shows what coverage that buys. This eliminates sticker shock (the #1 reason users abandon insurance quotes). Combined with the Comparison Tool (shows competitor rates alongside Progressive's) and Snapshot telematics ($328 avg annual savings, 80% save or break even), Progressive creates a three-pronged conversion funnel: budget-first → transparency trust → telematics retention lock-in.

**Pattern to steal:** Budget-first product selection — "What's your budget?" instead of "Here's the price."

---

## 🎯 Top 10 Features Every Regulated Onboarding Should Have

| # | Feature | Best Example | What It Is |
|---|---------|-------------|------------|
| 1 | **Capability-based entitlement** | Stripe | Each feature independently gated behind its own verification. Replace binary "access/no access" |
| 2 | **Progressive KYC tiers** | Plaid, Coinbase | Sandbox → Trial → Verified → Enhanced. Start minimal, escalate with usage volume |
| 3 | **ML silent verification** | Stripe (80%+ auto-approved) | Verify identity/business via database cross-reference. Only request document upload on mismatch |
| 4 | **Gates on outflow, not inflow** | PayPal | Let users engage/receive value immediately. Gate sensitive actions (withdrawal, payouts) behind KYC |
| 5 | **Post-approval underwriting** | Klarna, Chime | Verify AFTER value is delivered. Retroactive enforcement (freeze, restrict) as safety net |
| 6 | **Conversational AI onboarding** | Lemonade (90-sec Maya chatbot) | Replace multi-field forms with natural-language AI conversation |
| 7 | **Behavior-driven entitlement** | Chime, Square | Feature unlocks based on usage data (transaction history, deposit patterns), not credit scores |
| 8 | **Single-field-per-screen** | Robinhood (11 fields, 16 clicks) | One question per screen reduces cognitive load and form abandonment |
| 9 | **Try-before-you-buy sandbox** | Robinhood, Webull | Let users explore the product with demo data before asking for any personal information |
| 10 | **Instant value delivery** | PayPal (receive $ in 30 sec), Geico (instant ID card) | Give the user something immediately — a digital card, a crypto reward, an instant deposit |

---

## 📊 Industry Benchmarks

| Industry | Avg Rating | Best | Worst | Key Insight |
|----------|-----------|------|-------|-------------|
| **Fintech** | 4.3 | Stripe (5.0) | Marcus (3.5) | Fintech leads all industries in onboarding innovation. Progressive KYC + ML verification + agentic AI |
| **Insurance** | 3.5 | Lemonade (4.5) | State Farm (2.5) | Budget-first quoting (Progressive) + conversational AI (Lemonade) are the innovations. Traditional agents slow onboarding |
| **Banking** | 3.0 | Capital One (3.8) | Deutsche Bank (2.3) | Traditional banks are 10 years behind fintech on onboarding UX. Best: digital-first (Ally, Capital One) |
| **Healthcare** | 3.0 | Kaiser (3.8) | Epic Systems (2.0) | Employer auto-enrollment is the only low-friction path. Individual onboarding is the worst in any industry |
| **Crypto** | 3.8 | Coinbase (4.2) | Gemini (3.8) | Tiered KYC is standard. Learn to Earn (Coinbase) is the most innovative hook. Self-custody (Ledger) skips KYC entirely |
| **Payroll/HR** | 3.6 | Gusto (4.5) | ADP (2.5) | Gusto/Rippling/Deel prove complex regulated onboarding (EIN, tax IDs, SSNs) can be beautiful |

---

## 🔴 QBO Gap Analysis — Where QuickBooks Online Stands vs The Industry

| Dimension | QBO Current | Industry Best | Gap |
|-----------|-------------|---------------|-----|
| **Fields at signup** | 25-30 upfront | Robinhood: 11, Plaid: 3 | QBO asks for everything upfront regardless of entity type or feature intent |
| **Progressive KYC** | No — binary access | Plaid: 5 tiers, Coinbase: 3 tiers | QBO has NO progressive KYC model |
| **Pre-fill / silent verify** | IRS database only | Stripe: ML OCR + database + website scan (80% auto-approval) | QBO doesn't pre-fill from its own ecosystem (TurboTax, Mint, Payroll data) effectively |
| **Instant value** | Must complete setup first | PayPal: receive $ in 30 seconds, Chime: 2-min signup | QBO gives nothing of value until setup is complete |
| **Capability entitlement** | Binary access | Stripe: per-feature status (pending → active → inactive) | QBO has no granular feature gating |
| **Conversational AI onboarding** | None | Lemonade: 90-sec chatbot quote-to-bind | QBO has no AI-powered onboarding |
| **Try-before-you-buy** | None | Robinhood: sandbox with fake trades | QBO has no demo/sandbox mode |
| **Behavior-driven entitlement** | None | Chime: SpotMe based on deposit history | QBO credit/payroll limits not linked to usage data |
| **Agentic APIs** | None | Plaid/Stripe: MCP Server + A2A + llms.txt | QBO has no agentic APIs |
| **Post-approval underwriting** | No | Klarna: KYC after purchase, PayPal: verify after transact | QBO can't retroactively restrict features |

---

## 🚀 Implementation Roadmap — What QBO Should Build

### P0 (Now — High Impact, Low-Medium Effort)

| # | Feature | Model From | What To Build |
|---|---------|-----------|---------------|
| 1 | **Capability-based entitlement** | Stripe | Replace binary access with: `dashboard_viewing`, `bank_connections`, `invoice_creation`, `payroll_processing`, `tax_filing` — each independently gated |
| 2 | **Instant value + delayed sensitive features** | PayPal | Let users connect bank, see transactions, view basic reports immediately. Gate payroll, tax filing, ACH behind progressive KYC |
| 3 | **Last-4 SSN only → full SSN deferred** | PayPal, Stripe | Collect minimum at signup. Full SSN only when tax filing or payroll features activate |
| 4 | **Entity-type branching** | Square, Stripe | Sole prop sees 12 fields; corporation sees 25. Cut form length by 50% for most common user type |

### P1 (Next Quarter — Medium Impact, Medium-High Effort)

| # | Feature | Model From | What To Build |
|---|---------|-----------|---------------|
| 5 | **Single-field-per-screen** | Robinhood | Re-architect QBO signup as one question per screen with plain-language WHY |
| 6 | **Try-before-you-buy sandbox** | Robinhood, Webull | Prospect explores a demo company with fake data before entering any personal info |
| 7 | **Trial Plan model** | Plaid | Auto-approved, capped-scope access (10 transactions/reports). Full verification to exceed cap |
| 8 | **ML silent verification** | Stripe | Check IRS/state databases first. Request document upload only on mismatch |
| 9 | **Front-door expectation setting** | PayPal | List required docs + time estimates before asking for anything — boosted PayPal growth 8%→10%+ |
| 10 | **AI assistant post-signup** | PayPal Assistant | Surface "3 things to do first" instead of dropping users into a cold dashboard |

### P2 (Strategic — High Effort, Long-Term)

| # | Feature | Model From | What To Build |
|---|---------|-----------|---------------|
| 11 | **Conversational AI onboarding** | Lemonade | "Tell me about your business" → AI asks clarifying questions → configures QBO — replaces form entirely |
| 12 | **Agentic APIs (MCP + A2A)** | Plaid, Stripe | MCP server for QBO so AI agents handle bookkeeping setup autonomously |
| 13 | **Behavior-driven entitlement** | Chime, Square | Payroll limits, credit offers scale with transaction history — not credit score |
| 14 | **Learn-to-Earn equivalent** | Coinbase | Free templates/reports build QBO stake before full setup. "Your free invoice template is ready — complete setup to customize" |
| 15 | **Post-approval underwriting** | Klarna, PayPal | Let users transact, investigate later. Retroactively restrict features if risk signals emerge |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
| 2026-08-05 | **Complete rewrite** — Top 10, Top 10 Features, Industry Benchmarks, QBO Gap Analysis, Implementation Roadmap |
