# Methodology

## Research Approach

For each company, we conduct a 5-dimensional analysis using:

1. **Public documentation** — developer docs, API references, support/help center pages, user agreements, compliance pages
2. **Third-party analysis** — UX case studies, blog posts, industry reports, regulatory filings
3. **Competitive intelligence** — product comparison pages, review sites (G2, Trustpilot), forum discussions
4. **Live testing** — where accessible without creating real accounts: public demos, interactive tours, screenshots from product pages
5. **Academic/industry research** — regulatory frameworks (BSA, AML, KYC/KYB requirements), published studies on conversion and fraud

## Rating Scale

Each dimension is rated 1-5:

| Rating | Meaning |
|--------|---------|
| 1 | Significantly below industry standard — major gaps |
| 2 | Below average — notable weaknesses |
| 3 | Industry standard — competent but not innovative |
| 4 | Above average — notable strengths; best practice |
| 5 | Industry-leading — sets the benchmark; everyone else should copy this |

## Analysis Dimensions

### 1. Fields Collected & Collection Strategy
- WHAT fields are collected at each step
- HOW they are collected (progressive disclosure, multi-step wizard, single-page)
- WHY each field is collected (regulatory, risk, business need)
- Minimization strategy: what is NOT asked, what is deferred
- Pre-fill sources: partner API, Plaid/Yodlee, credit bureau, government database, device fingerprint
- Conversion tactics: instant verification, social sign-in, save-and-resume, skip options

### 2. Risk Decision Process
- KYC/KYB verification tiers and triggers
- Identity verification methods (document OCR, biometric liveness, database cross-reference, video KYC)
- Fraud detection signals (device fingerprint, IP geolocation, email/phone reputation, velocity, behavioral)
- Sanctions/watchlist screening (OFAC, UN, EU, PEP, adverse media)
- Decision logic: automated vs manual, scoring models, thresholds
- Ongoing monitoring: post-approval risk assessment, periodic re-verification, change detection

### 3. Entitlement Model
- Progressive trust tiers: what's unlocked at each verification stage
- Sending/receiving/withdrawal/feature limits at each tier
- Hold periods, reserve requirements, and graduation criteria
- Instant vs delayed entitlement
- Gates and triggers for escalation

### 4. UI/UX Flow & Agentic Experience
- Step-by-step flow description
- Total steps and estimated completion time
- Mobile vs desktop experience differences
- AI/agentic features (chatbots, smart form fill, document scanning, MCP servers, A2A)
- Friction points, why they exist, and mitigation attempts
- Notable UI patterns (progress indicators, inline validation, contextual help)
- Drop-off analysis and conversion optimization

### 5. SWOT vs Intuit QuickBooks Online
- Company SWOT: strengths, weaknesses, opportunities, threats
- QBO reference SWOT for comparison
- Direct comparison matrix across all 4 dimensions
- Actionable recommendations: what QBO should steal, what QBO already does better

## Sources

All analysis is based on publicly available information as of the analysis date. Sources are cited inline in each document. We do not have access to internal data (actual conversion rates, fraud rates, decision models) — estimates are based on public disclosures, third-party research, and inference from observable behavior.

## Limitations

1. **No internal data** — conversion rates, fraud rates, and decision logic are inferred from public information
2. **Regional variation** — onboarding flows differ by country; analysis focuses on US flows unless otherwise noted
3. **Time sensitivity** — companies update onboarding flows frequently; analysis reflects a point in time
4. **Survivor bias** — we analyze companies whose onboarding is successful enough to have public documentation; companies with terrible onboarding that led to failure may not be represented

## Change Log

| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation — methodology document |
