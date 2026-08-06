# Coinbase — Entitlement Model

```mermaid
stateDiagram-v2
    [*] --> Unverified: Email only
    state Unverified { Browse + Learn: Earn $1-5 crypto; Deposit crypto only }
    state Verified { Full trading; Fiat in/out; Send crypto; Staking; Coinbase Card; Coinbase One }
    state Enhanced { Higher limits; Wire transfers; OTC desk; Pro features }
    state Prime { Institutional custody; OTC block trading; Multi-user RBAC; Prime brokerage }
    Unverified --> Verified: Photo ID + Selfie + SSN
    Verified --> Enhanced: Employment + Income + Source of funds
    Enhanced --> Prime: Entity docs + UBOs + Source of wealth
```

| Tier | Requirements | Key Capabilities | Limits |
|------|-------------|-----------------|--------|
| Unverified | Email | Browse, Learn to Earn, deposit crypto | No fiat, no trade, no send |
| Verified | Photo ID + selfie + SSN | Full trading, fiat in/out, send crypto, staking, Coinbase One ($5-300/mo) | Algorithmically calculated per-user |
| Enhanced | Employment + income + source of funds | Higher limits, wire transfers, OTC, Pro | Significantly higher; per-account |
| Institutional | Entity docs + EIN + UBOs + source of wealth | Coinbase Prime: custody, OTC block trading, RBAC, API/FIX, staking-as-a-service | High/no practical limits |

**Key pattern:** Verifying unlocks YOUR OWN crypto from Learn to Earn — creating voluntary KYC conversion.

## Change Log
| Date | Change |
|------|--------|
| 2026-08-05 | Initial creation |
