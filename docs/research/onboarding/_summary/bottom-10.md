# 🔴 Bottom 10 — The Worst Onboarding Experiences (And What QBO Must Avoid)

> These companies represent **anti-patterns** — onboarding so broken that it destroys conversion, infuriates users, or exists only because of regulatory capture. QBO should study these as cautionary tales.

---

## #1 Worst — Epic Systems (2.0/5)
**Industry:** Healthcare EHR | **Problem:** 12-24 month hospital implementation, $50M-$500M+

**The disaster:** Epic doesn't do "onboarding" in any normal sense. A hospital signs a contract → a team of Epic implementation specialists descends on the hospital for 12-24 months → they map every department, configure every workflow, integrate every billing system. There is NO self-serve. There is NO digital onboarding. "Go live" is a celebrated milestone that takes 2 years to reach.

**Why it's broken:** Epic has no incentive to improve. They have 250M+ patient records across most major US hospitals. Switching costs are astronomical (the hospital already spent $100M+ and 2 years implementing). This is regulatory capture + monopoly dynamics, not a product failure. But for QBO, the lesson is: NEVER let your product become so entrenched that you stop caring about onboarding.

**What QBO must avoid:** Becoming the "Epic of accounting" — where switching costs are so high that you can afford to ignore onboarding UX. Intuit's 80% SMB accounting market share already puts QBO in this danger zone.

---

## #2 Worst — Deutsche Bank (2.3/5)
**Industry:** Banking (Germany) | **Problem:** 3-6 month corporate KYC

**The disaster:** Deutsche Bank's post-financial-crisis compliance overhaul made KYC notoriously slow. A corporate client wanting to open an account goes through relationship manager meetings → entity document collection → UBO disclosure → source-of-wealth verification → PEP screening → compliance committee approval → account opening. This takes 3-6 months. Meanwhile, the client opens an account with a fintech in 10 minutes.

**Why QBO should care:** Every month of KYC delay = permanent customer loss. QBO's current manual verification (1-3 business days) isn't Deustche-level bad, but the lesson is: compliance burden that scales non-linearly with regulation eventually becomes a competitive moat for disruptors.

---

## #3 Worst — State Farm (2.5/5)
**Industry:** Insurance | **Problem:** Pure agent model — ZERO self-serve digital onboarding

**The disaster:** You cannot open a State Farm policy online without talking to an agent. The website is a lead-gen form that routes you to a local agent's phone number. 19,000+ agents are the distribution MOAT — and the innovation ANCHOR. A 25-year-old who's never spoken to an insurance agent has no path to State Farm that doesn't involve a phone call or an in-person meeting.

**Concrete example:** Geico: ZIP code → 15 minutes → bound policy → digital ID card in Apple Wallet. State Farm: ZIP code → "Find an agent near you" → phone call → schedule meeting → discuss coverage → get quote → wait for paperwork. Days vs 15 minutes.

**What QBO must avoid:** QBO's accountant network is its State Farm-like MOAT. But if accountants are the ONLY path to QBO, younger business owners who've never hired an accountant will go to FreshBooks or Xero. Self-serve + accountant-assisted must coexist.

---

## #4 Worst — ADP (2.5/5)
**Industry:** Payroll | **Problem:** 4-12 week enterprise implementation

**The disaster:** ADP's SMB product (RUN) is decent. But the enterprise product requires a dedicated implementation team, data migration from legacy systems, tax agency setup in every jurisdiction, and weeks of testing. A company switching from ADP to Gusto pays with money; a company switching from Gusto to ADP pays with TIME.

**Concrete example:** Gusto SMB onboarding: EIN → Gusto auto-fetches state tax IDs → add employees (name + SSN + pay rate) → first payroll run in ~1 hour. ADP enterprise: contract signed → implementation team assigned → data collection begins → tax agency registration → parallel testing → go live. 4-12 weeks.

**What QBO must avoid:** QBO has both self-serve and accountant-assisted paths. ADP's mistake was keeping the enterprise complexity and layering a self-serve product on top, with the two sharing nothing. QBO's self-serve and accountant paths must share the same data model and verification pipeline.

---

## #5 Worst — Prudential (2.5/5)
**Industry:** Life Insurance | **Problem:** Paramedical exam — blood draw, urine sample

**The disaster:** To buy a significant life insurance policy from Prudential, you must schedule a paramedical exam. A nurse comes to your home or office. They draw blood, collect a urine sample, measure height/weight/blood pressure, and ask detailed health history questions. This is the most invasive consumer onboarding in ANY industry we studied. The exam itself adds 2-4 weeks to the process.

**Concrete example:** Lemonade: 90 seconds, AI chatbot, policy issued. Prudential: 3-6 weeks, blood draw, nurse visit, health questionnaire, MIB check, lab results, underwriter review. Both sell regulated insurance products requiring risk assessment. ONE chose to rebuild the model; ONE chose to keep the legacy model and add a digital wrapper (Assurance IQ for small no-exam policies).

**What QBO must avoid:** Adding a "digital layer" on top of a fundamentally analog process doesn't make it digital onboarding. You have to rebuild the process.

---

## #6 Worst — HSBC (2.5/5)
**Industry:** Banking (Global) | **Problem:** Post-scandal compliance burden

**The disaster:** After a $1.9B deferred prosecution agreement for money laundering failures (2012), HSBC overcorrected. KYC became a weapon. Even simple personal account openings involve weeks of document requests, in-branch verification, and repeated compliance queries. "World's local bank" became "world's slowest bank."

**What QBO must avoid:** Compliance overcorrection. Wells Fargo's fake-accounts scandal led to intrusive consent checkpoints. HSBC's money-laundering scandal led to glacial KYC. When regulators punish you, the instinct is to add friction. Resist it. Fix the compliance engine, not the user experience.

---

## #7 Worst — Optum (2.5/5)
**Industry:** Healthcare (B2B) | **Problem:** Provider credentialing maze

**The disaster:** A doctor wanting to join an Optum network must submit: NPI number, DEA registration, state medical license(s), board certification(s), malpractice insurance, hospital affiliations, Medicare/Medicaid enrollment, and references. This takes 90-120 days. During this time, the doctor cannot see Optum patients or bill Optum. This is "onboarding" as credential verification — pure gatekeeping with zero user experience consideration.

**What QBO must avoid:** QBO's accountant network (QBO Accountant) requires verifying accountant credentials. The Optum lesson: credential verification is necessary, but 90-120 days destroys the business relationship. Automate it or parallelize it.

---

## #8 Worst — Bank of America (2.8/5)
**Industry:** Banking | **Problem:** Traditional mega-bank — 20+ fields, ChexSystems, no minimization

**The disaster:** BOA's consumer checking onboarding collects 20+ fields. ChexSystems + credit soft pull are mandatory. SafeBalance (no-overdraft) is offered as a fallback — good — but the primary flow asks for everything upfront. The contrast with Chime (10 fields, no ChexSystems, no credit check, 2 minutes) is brutal.

**Concrete example:** Chime: SSN + name + DOB + address + phone. 2-minute signup. Instant virtual card. BOA: all of the above + government photo ID upload + employment/income info + initial deposit funding + ChexSystems consent + overdraft election + debit card design preference + paperless statement opt-in. Multi-page wizard, 10-15 minutes.

**What QBO must avoid:** BOA's form is the exact experience QBO currently has — asking for 25+ fields upfront because "we've always done it that way." Every field QBO adds beyond the legal minimum loses users.

---

## #9 Worst — Wells Fargo (3.0/5)
**Industry:** Banking | **Problem:** Post-scandal consent architecture makes onboarding feel like a liability waiver

**The disaster:** After opening 3.5M+ fake accounts, Wells Fargo implemented explicit consent checkpoints at every step. Overdraft requires Reg E double opt-in. Every product-add requires a separate confirmation screen. Account opening is now centralized (branches can't open accounts without corporate oversight). The result: the most consent-burdened onboarding in banking. 70M+ customers are reminded, at every interaction, that their bank defrauded them.

**What QBO must avoid:** Consent architecture is necessary. But when every step feels like "we're protecting ourselves from being sued again," the user feels like a liability, not a customer. Consent should build trust, not signal distrust.

---

## #10 Worst — Vanguard (3.0/5)
**Industry:** Investment Management | **Problem:** Functional but clunky — the "we don't need good UX because we have low fees" trap

**The disaster:** Vanguard has $8T+ AUM, 50M+ investors, the lowest fees in the industry. Their onboarding is functional — it technically works. But it feels like software from 2008. The contrast with Robinhood (11-field wizard) or Wealthfront (goal-based planning questionnaire) is stark. Vanguard's implicit assumption: "people will tolerate mediocre UX for the lowest fees." That assumption is aging — Gen Z and millennial investors are choosing Robinhood and Wealthfront despite higher total costs.

**What QBO must avoid:** "We're the market leader, our UX doesn't need to be great." QBO has 80% SMB market share. That's not a reason to settle — it's a reason to invest before competitors eat your base from below.

---

## 🔴 Common Failure Patterns Across the Bottom 10

| Anti-Pattern | Companies | Lesson for QBO |
|-------------|-----------|---------------|
| **Regulatory capture** — "they have to use us, so onboarding doesn't matter" | Epic (2.0), Vanguard (3.0) | Never let market share become an excuse for ignoring onboarding UX |
| **Compliance overcorrection** — "we got fined, so now onboarding is a punishment" | HSBC (2.5), Wells Fargo (3.0) | Fix the compliance engine, not the user experience |
| **Agent-only distribution** — "our agents handle onboarding, we don't need digital" | State Farm (2.5) | Agents are a MOAT and an ANCHOR. Self-serve must coexist |
| **Enterprise complexity preserved** — "our product is complex, so onboarding must be complex" | ADP (2.5), Epic (2.0), Deutsche (2.3) | Complex products need the BEST onboarding, not an excuse for bad onboarding |
| **Invasive data collection** — "we need blood/urine/5-year history before we can trust you" | Prudential (2.5), Optum (2.5) | Challenge every data requirement. "Why do we need this? Can we defer it? Can we verify it silently?" |
| **Legacy form design** — "we've always collected these 20 fields, so we'll keep collecting them" | BOA (2.8), TD Bank (2.8) | Every field beyond the legal minimum loses users. Field audit required |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-08-06 | Initial creation — Bottom 10 anti-pattern analysis |
