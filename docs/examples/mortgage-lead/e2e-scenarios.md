# E2E Scenarios — Mortgage Lead Submission

> Derived from mfangdai (mRateQuote) production API. Each scenario walks through a complete conversation flow with expected state transitions, LLM calls, and framework behavior.

---

## Scenario 1: Purchase Lead — First-Time Borrower

**User:** "I want to get a mortgage for a new home"

**Expected flow:**

| Turn | User/System | Intent | State | Key Data |
|------|------------|--------|-------|----------|
| 1 | User: "I want to get a mortgage for a new home" | `submit_lead` | `identify_borrower` | New user detected |
| 2 | System: "Welcome! I'll help you submit a mortgage application. First, what's your name, email, and phone?" | - | `identify_borrower` | - |
| 3 | User: "John Smith, john@example.com, 650-555-1234" | `provide_lead_detail` | `collect_lead_purpose` | first_name=John, last_name=Smith, email=john@example.com, phone=6505551234 |
| 4 | System: "Thanks John. Are you buying a new home or refinancing?" | - | `collect_lead_purpose` | - |
| 5 | User: "Buying" | `provide_lead_detail` | `collect_loan_amount` | loanPurpose=PURCHASE |
| 6 | System: "How much are you looking to borrow, and what's the estimated home value?" | - | `collect_loan_amount` | - |
| 7 | User: "Loan 500k, home is about 625k in San Francisco, 94105. It's a condo." | `provide_lead_detail` | `collect_purchase_details` | loanAmount=500000, homeValue=625000, state=CA, zipCode=94105, homeDescription=CONDO |
| 8 | System: "First-time buyer? Already working with an agent?" | - | `collect_purchase_details` | - |
| 9 | User: "First time, yes. No agent yet, can you recommend one?" | `provide_lead_detail` | `collect_financial_profile` | firstTimeHomeBuyer=true, hasRealEstateAgent=false, needRealEstateAgent=true |
| 10 | System: "Got it. What's your credit situation and employment?" | - | `collect_financial_profile` | - |
| 11 | User: "Credit is good, I'm employed, household income around 150k" | `provide_lead_detail` | `collect_preferences` | creditScoreRange=GOOD, employmentStatus=EMPLOYED, annualHouseholdIncome=100K_200K |
| 12 | System: "Preferred mortgage product? Any 30-year fixed?" | - | `collect_preferences` | - |
| 13 | User: "30 year fixed preferred. Just looking for best rate" | `provide_lead_detail` | `confirm_submission` | mortgageProducts="30Yr Fixed" |
| 14 | System: "Here's your summary: Purchase, $500k loan on $625k condo in CA 94105, 30Yr Fixed. Submit?" | - | `confirm_submission` | - |
| 15 | User: "Yes, submit" | `confirm` | `submit_lead` | confirmed=true |
| 16 | System: "Lead submitted! ID: LEAD-abc123. Loan officers will review and send quotes. I'll notify you." | - | `lead_submitted` | lead_id=LEAD-abc123 |

**Framework events:**
- 8 LLM calls (identify → purpose → amount → purchase → financial → preferences → confirm → response)
- 1 code executor (create_lead)
- 1 lead distribution trigger (PushModelLeadDistributor)
- 1 LeadAssignment created (to first eligible loan officer in queue)

---

## Scenario 2: Refinance Lead — Returning Borrower

**User:** "I want to refinance my mortgage"

**Expected flow:**

| Turn | User/System | Intent | State | Key Data |
|------|------------|--------|-------|----------|
| 1 | User: "I want to refinance my mortgage" | `submit_lead` | `identify_borrower` | Returning user (session cookie) |
| 2 | System: "Welcome back Jane! Refinancing? Current loan details?" | - | `collect_lead_purpose` | - |
| 3 | User: "Yes, refi. Current rate 6.5%, want to get lower" | `provide_lead_detail` | `collect_loan_amount` | loanPurpose=REFINANCE |
| 4 | System: "Loan amount and property details?" | - | `collect_loan_amount` | - |
| 5 | User: "Loan 300k, home worth 500k in Austin TX, single family" | `provide_lead_detail` | `collect_refinance_details` | loanAmount=300000, homeValue=500000, state=TX, homeDescription=SINGLE_FAMILY |
| 6 | System: "Current rate 6.5%. Any second mortgage? Cash-out needed?" | - | `collect_refinance_details` | - |
| 7 | User: "No second mortgage. No cash-out, just rate reduction" | `provide_lead_detail` | `collect_financial_profile` | currentMortgageRate=6.5, haveSecondMortgage=false, additionalLoanAmount=0 |
| 8 | ... (financial profile, preferences, confirm, submit) | - | - | Similar to Scenario 1 |

---

## Scenario 3: Lead Status Check

**User:** "What's happening with my lead LEAD-abc123?"

| Turn | User/System | Intent | State |
|------|------------|--------|-------|
| 1 | User: "What's happening with my lead LEAD-abc123?" | `check_lead_status` | (query) |
| 2 | System: "Your lead was submitted 2 hours ago. 3 loan officers have viewed it. 1 quote received: 30Yr Fixed at 5.875% from Agent Chen at ABC Lending. View details?" | - | - |

---

## Scenario 4: Loan Officer Quote Flow

**User (Loan Officer):** "Show me available leads in California"

| Turn | User/System | Intent | State |
|------|------------|--------|-------|
| 1 | User: "Show me available leads in California" | `search_leads` | (query) |
| 2 | System: "Found 12 available leads in CA. [Lists with loan amount, purpose, credit range]" | - | - |
| 3 | User: "Quote on LEAD-abc123: 30Yr Fixed, 5.875%, no points, $1500 lender credit" | `create_quote` | (create) |
| 4 | System: "Quote submitted. Borrower will be notified." | - | - |

---

## Scenario 5: Error — Missing Required Fields

**User:** "I want a mortgage"

| Turn | User/System | Intent | State |
|------|------------|--------|-------|
| 1 | User: "I want a mortgage" | `submit_lead` | `identify_borrower` |
| 2 | System: "I'll help. What's your name and contact?" | - | `identify_borrower` |
| 3 | User: "Just give me a loan" | `unrecognized_intent` | `errorNode` → `ask_clarify` |
| 4 | System: "I need some details to proceed. At minimum: your name, email, phone, loan amount, property location. Can you provide these?" | - | `identify_borrower` (retry) |

---

## Scenario 6: OAuth — Registered Borrower Returns

**Pre-condition:** Borrower has Keycloak account (credentialId exists), valid JWT in session.

| Turn | User/System | Auth | Intent | State |
|------|------------|------|--------|-------|
| 1 | User: "Check my leads" | JWT valid, ROLE_BORROWER | `check_lead_status` | (query) |
| 2 | System: [Returns borrower's active leads from database] | - | - | - |

**Verification:** No re-registration prompt. Borrower identity resolved from JWT `sub` claim → credentialId → Borrower entity.

---

## Scenario 7: Rate Limiting — Chitchat Exhausted

**User:** 11th non-business message in same conversation

| Turn | User/System | Intent | State |
|------|------------|--------|-------|
| 11 | User: "How's the weather?" | `small_talk` | `errorNode` |
| 12 | System: "I'm here to help with your mortgage application. Would you like to continue with your lead submission, or is there a mortgage-related question I can answer?" | - | previous state (return) |

---

## Scenario 8: Daily Budget Exceeded

**Pre-condition:** Server has used $20.00 of LLM tokens today.

| Turn | User/System | Behavior |
|------|------------|----------|
| 1 | User: "I want to submit a lead" | Gateway checks daily_cost ≥ $20.00 → HTTP 500 |
| 2 | System: Returns 500. Admin notified. Service resumes next day (UTC midnight reset). | - |

---

## Expected Statistics (per Scenario 1)

| LLM Calls | Nodes | Retries | Deterministic Fallbacks | Escalations |
|-----------|-------|---------|------------------------|-------------|
| 8 | 9 (1 code) | 0 (all pass first attempt) | 0 | 0 |
