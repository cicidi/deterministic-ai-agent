# Intent Definitions — Mortgage Lead

> Derived from mfangdai (mRateQuote) production system. Purpose-based lending, lead marketplace.

## System Intents

| Intent | Type | Description | Complex |
|--------|------|-------------|---------|
| `submit_lead` | Write | Borrower submits a mortgage lead | No |
| `check_lead_status` | Read | Borrower checks lead status | No |
| `check_rates` | Read | Borrower asks about current rates | No |
| `provide_lead_detail` | Write | Borrower provides more detail to an existing lead | No |
| `register_borrower` | Write | First-time borrower registration | No |
| `register_loan_officer` | Write | Loan officer registration | No |
| `update_loan_officer_profile` | Write | Update NMLS, licensed states, products | No |
| `search_leads` | Read | Loan officer searches available leads | No |
| `create_quote` | Write | Loan officer submits a quote on a lead | No |
| `add_product_quote` | Write | Add another product to an existing quote | No |
| `view_quotes` | Read | Borrower views quotes from loan officers | No |
| `start_conversation` | Control | Start a new conversation | No |
| `finish_conversation` | Control | End conversation | No |
| `confirm` | Control | Confirm or agree | No |
| `decline` | Control | Decline or disagree | No |
| `correction` | Control | Correct previous information | No |
| `ask_question` | Control | Ask a general question | No |
| `unrecognized_intent` | Control | Unrecognized input | No |

## Intent Payloads

### submit_lead — LeadPayload

```yaml
output_schema:
  loanPurpose: { type: string, enum: [PURCHASE, REFINANCE], required: true }
  loanAmount: { type: number, minimum: 50000, required: true }
  homeValue: { type: number, minimum: 50000, required: true }
  state: { type: string, required: true }
  zipCode: { type: string, minLength: 5, required: true }
  homeDescription: { type: string, required: false }
  residenceType: { type: string, required: false }
  creditScoreRange: { type: string, required: false }
  employmentStatus: { type: string, required: false }
  annualHouseholdIncome: { type: string, required: false }
  mortgageProducts: { type: string, required: false }
  message: { type: string, maxLength: 2000, required: false }
  # Purchase-specific
  hasRealEstateAgent: { type: boolean, required: false }
  firstTimeHomeBuyer: { type: boolean, required: false }
  # Refinance-specific
  currentMortgageRate: { type: number, required: false }
  haveSecondMortgage: { type: boolean, required: false }
```

### create_quote — QuotePayload

```yaml
output_schema:
  leadId: { type: string, format: uuid, required: true }
  mortgageProduct: { type: string, required: true }
  interestRate: { type: number, minimum: 0, maximum: 20, required: true }
  cost: { type: number, required: false }
  credit: { type: number, required: false }
  message: { type: string, maxLength: 500, required: false }
```

## Agent Dispatch

| Intent | Target |
|--------|--------|
| `check_rates` | ReadOnlyAgent → RAG pipeline (current rate data) |
| `ask_question` | ReadOnlyAgent → RAG pipeline (FAQ) |
| `search_leads` | ReadOnlyAgent → lead database query |
| `submit_lead`, `provide_lead_detail`, `check_lead_status`, `view_quotes` | State machine (deterministic write/read) |
| `create_quote`, `add_product_quote` | State machine |
| `register_borrower`, `register_loan_officer`, `update_loan_officer_profile` | State machine |
