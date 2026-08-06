# Coinbase — UI/UX & Agentic Experience

| Attribute | Detail |
|-----------|--------|
| Steps | 21 (from download to first crypto purchase) |
| Time | 8-12 min (happy path); 2-10 days (manual review) |
| Mobile-first | >85% sign-ups on mobile; camera-dependent KYC; Face ID/fingerprint login |
| AI features | Coinbase Assistant chatbot, AI market insights, auto-invest DCA, smart portfolio tracking |

```mermaid
journey
    title Coinbase Onboarding (Happy Path)
    section Discovery
      Download App: 5: User
      Create Account (Email+PW): 5: User
    section Learn to Earn
      Watch Educational Video: 5: User, Coinbase
      Answer Quiz Question: 5: User
      Earn Crypto ($1-5): 5: User, Coinbase
    section Identity Verification
      Enter Personal Info: 4: User
      Scan Photo ID: 3: User
      Take Selfie (Liveness): 2: User
    section First Purchase
      Link Payment Method: 3: User
      Select BTC Amount ($25/50/100): 4: User
      Confirm Purchase: 5: User
      Confetti Animation: 5: Coinbase
```

**Notable patterns:** Learn to Earn, simple BTC buy as first action, confetti on completion, bottom-sheet transactions, progressive feature disclosure (Advanced Trade revealed after first buy), Coinbase Wallet as separate "graduation" app.

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
