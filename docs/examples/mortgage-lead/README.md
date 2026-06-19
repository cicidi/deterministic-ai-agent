# Mortgage Lead — Example Workflow

> Extracted from **mfangdai (mRateQuote)** production mortgage lead marketplace platform.

## Overview

A borrower submits a mortgage lead (purchase or refinance). The system validates, extracts entity data, collects missing fields, and submits to push-model distribution. Loan officers receive lead assignments and can submit quotes.

## Files

| File | Description |
|------|-------------|
| `workflow.yaml` | Mortgage lead submission workflow (10 states) |
| `intent-definitions.md` | 18 intents with payload schemas and agent dispatch |
| `e2e-scenarios.md` | 8 scenarios covering purchase, refinance, error, OAuth, budget |

## Domain Model

See `../../domain-models/mortgage-lead.yaml` — OpenAPI 3.1 schemas for:
- **Lead** — loanPurpose, loanAmount, homeValue, state, credit/income profile, purchase/refinance fields
- **Borrower** — name, contact, credit score, languages
- **LoanOfficer** — NMLS, licensed states, products, subscription tier
- **Quote** / **ProductQuote** — mortgage product offers with rate/cost/credit

## Key Differences from Home Insurance

| Aspect | Home Insurance | Mortgage Lead |
|--------|---------------|---------------|
| Primary intent | `get_quote`, `file_claim` | `submit_lead`, `check_rates` |
| Domain entities | PropertyInfo, CoverageInfo, ClaimDetails | Lead, Borrower, LoanOfficer, Quote, ProductQuote |
| Business flow | Quote → Risk Assessment → Policy | Submit Lead → Push Distribution → Quotes |
| OAuth | Standard OIDC | Keycloak realm + API key (dual auth) |
| Post-submission | Policy issuance | Lead marketplace (multiple loan officers compete) |

## Auth Configuration

OAuth config extracted from mfangdai production system (Keycloak `mRateQuote` realm). See `docs/specs/2026-06-17-auth-token-verification.md` §2.5 for the full Keycloak configuration sample.
