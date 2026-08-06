# Klarna — BNPL Onboarding (#5 Overall)

> **Industry:** Fintech / Buy Now Pay Later | **Onboarding Type:** Consumer KYC — Post-Transaction | **Overall:** 4.1/5 | **Date:** 2026-08-05

---

## Executive Summary — Why Klarna is #5

Klarna inverted the KYC paradigm: **verify AFTER the purchase, not before.** Here's why this matters:

**Traditional checkout with financing:** User clicks "finance this purchase" → redirected to loan application → fills SSN, income, employer → waits for approval → may be denied → abandons purchase. **20-40% drop-off.**

**Klarna checkout:** User sees "Pay in 4 installments of $25" → enters email + ZIP code (2 fields) → Klarna runs millisecond soft credit check → approved → purchase completes → KYC (full identity verification) happens later. **20-30% conversion lift for merchants.**

The key trade-off: Klarna accepts that some users who pass the 2-field check won't complete full KYC later — those accounts get restricted. But the alternative is losing ALL those users at checkout. By separating "can this person pay?" (2-field soft check at checkout) from "who is this person?" (full KYC post-purchase), Klarna captures revenue that traditional financing loses.

**QBO equivalent:** User needs to create an invoice NOW. "Enter email to get started" → instant invoice created → send to client → KYC completed later. Instead of "fill 25 fields before you can send your first invoice."

**Concrete numbers:** 150M+ users, 500K+ merchants, 20-30% merchant conversion lift. Late fees capped (and banned entirely in some markets). Soft credit check only at checkout.

---

## Detailed Comparison: QBO vs Klarna

### The Post-Transaction KYC Model
| Step | Klarna | QBO Equivalent (Should Be) |
|------|--------|--------------------------|
| **At time of need** | User needs to pay. Enters email + ZIP. Soft credit check. Approved. Purchase completes | User needs to invoice a client. Enters email. Invoice created. Sent to client. $ received. |
| **Post-transaction** | Klarna runs full KYC. User uploads ID. If fails, account restricted (can't make future purchases) | QBO runs full business verification. If fails, account restricted (can't run payroll, can't file taxes) |
| **Risk management** | Purchase amount is small (typically $50-500). Fraud loss contained. Account restriction prevents repeat fraud | Invoice fraud risk is low (payment goes to business's own bank account). Tax/payroll risks are gated behind verification |

### What This Model Actually Fixes
| Problem | Traditional Solution | Klarna's Solution | QBO's Current Approach |
|---------|--------------------|--------------------|-----------------------|
| "I need this NOW but I don't have my documents" | Wait until you have documents, then apply | Use it now, verify later | QBO: wait until you have EIN, business license, bank details, SSN. Come back when ready |
| "I'll come back later" (but never does) | Lost customer | Customer captured, revenue earned, KYC completed later | Lost customer. Every friction point in the 25-field form loses permanent customers |
| Fraud risk of deferred verification | Don't defer | Accept limited fraud risk on small transactions. Restrict accounts that don't complete KYC. Retroactive enforcement | No deferred verification at all — loses legitimate customers to prevent fraud |

### What QBO Should Actually Do
| Priority | Action | Model From Klarna | Impact |
|----------|--------|-----------------|--------|
| **P0** | "Create your first invoice in 60 seconds" — email + business name only. Invoice created, sent, payment received. Full KYC deferred | Klarna email+ZIP at checkout | Users experience QBO's core value BEFORE hitting the KYC wall |
| **P1** | Post-creation KYC: after 3 invoices or $1,000 received, full business verification required. Account restricted (can't create new invoices) if not completed | Klarna account restriction for incomplete KYC | Captures casual users who would abandon during full signup. Graduates them to verified |
| **P1** | Risk-based limits: unverified users can process up to $1,000 in invoices. Verified users unlimited | Klarna transaction size limits by verification tier | Contains fraud while maximizing legitimate user conversion |

---

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
| 2026-08-06 | Enhanced with post-transaction KYC model and QBO equivalents |
