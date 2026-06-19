# User Authentication & Authorization Token Verification

> Part of [Deterministic Workflow Framework — High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md)
> Covers: OAuth / OIDC login, token issuance, token verification, user context injection into agentState.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial auth spec: OAuth/OIDC login, token verification, user context, provider integration |
| 2026-06-17 | 0.2.0 | Simplify to identity-first: focus on token verification + UserContext injection; role-based enforcement deferred to a future interface |

---

## 1. Role

Every workflow interaction must carry a verified user identity. The framework does NOT implement its own auth system — it verifies tokens issued by a standard OAuth / OIDC provider and injects the user context into `agentState`.

```
User Request (with Bearer token)
    │
    ▼
[Token Verification]  ← OAuth / OIDC provider (Auth0, Okta, Keycloak, ...)
    │
    ├── invalid / expired → 401 Unauthorized
    │
    └── valid → extract user context
                    │
                    ▼
              agentState.user = UserContext {
                user_id, roles, scopes, ...
              }
                    │
                    ▼
              [Permission Enforcer]  ← config-level + role-based checks
                    │
                    ▼
              [Layer 1: UNDERSTAND]
```

### 1.1 What the Framework Does NOT Do

- ❌ **NOT an identity provider** — does not store passwords, issue tokens, or manage user directories
- ❌ **NOT a session manager** — session management is delegated to the OAuth provider or application layer
- ❌ **NOT an OAuth server** — does not implement OAuth grant flows (authorization code, client credentials)

### 1.2 What the Framework Does

- ✅ **Verifies tokens** — validates JWT signatures, expiry, issuer, audience
- ✅ **Extracts user context** — maps token claims to `UserContext`
- ✅ **Injects into agentState** — populates `agentState.user` for permission enforcement
- ✅ **Passes to tool layer** — tools receive the verified user context
- ✅ **Audits** — every workflow interaction records the authenticated user

---

## 2. Token Verification Flow

### 2.1 Supported Token Types

| Type | Verification | Use Case |
|------|-------------|----------|
| **JWT (RS256/ES256)** | Public key from JWKS endpoint | Most common, stateless verification |
| **Opaque token** | Token introspection endpoint | Centralized token validation |
| **API Key** | Hashed comparison against stored key | Machine-to-machine, dev environments |

### 2.2 Verification Steps

```
1. Extract token from Authorization: Bearer <token>
2. Determine token type:
     JWT → verify signature with public key (JWKS)
     opaque → POST /introspect to provider
     API key → hash compare
3. Validate claims:
     exp  — not expired
     iss  — matches expected issuer
     aud  — matches expected audience
     iat  — not in the future
4. Extract UserContext from token claims
5. Inject into agentState.user
```

### 2.3 UserContext Schema

```
UserContext {
  user_id:         string        // unique user identifier
  roles:           string[]      // e.g., ["admin", "operator", "user"]
  scopes:          string[]      // e.g., ["sensitive_data:read", "dangerous_operation:write"]
  tenant_id?:      string        // multi-tenant deployments
  session_id?:     string        // for audit correlation
  auth_provider:   string        // "auth0" | "okta" | "keycloak" | "custom"
  auth_time:       datetime      // when the token was issued
}
```

### 2.4 Verification Order

When both JWT and OAuth are configured, the framework verifies in order:

1. **JWT first** — Fast local verification (public key, no network call). If valid, skip OAuth.
2. **OAuth second** — If JWT is missing or expired, validate via OAuth token introspection endpoint. This adds latency (network call) but handles token revocation.

```yaml
auth:
  verification_order: [jwt, oauth]     # jwt_first | oauth_only | jwt_only
  jwt:
    enabled: true
  oauth:
    enabled: true
    introspection_endpoint: "https://auth.example.com/oauth2/introspect"
```

If neither succeeds, return 401. Failed OAuth introspection (provider down) with no valid JWT → 503 (service unavailable, retry later).

---

## 3. Implementation Options

### Option A: OIDC Provider — Auth0 / Okta / Keycloak (Recommended)

Relies on a dedicated identity provider. The framework only verifies tokens.

| Provider | Protocol | Verification |
|----------|----------|-------------|
| **Auth0** | OIDC (JWT RS256) | Public key from `https://<domain>/.well-known/jwks.json` |
| **Okta** | OIDC (JWT RS256) | Public key from `https://<domain>/oauth2/default/v1/keys` |
| **Keycloak** | OIDC (JWT RS256) | Public key from `https://<domain>/realms/<realm>/protocol/openid-connect/certs` |
| **Google Identity** | OIDC (JWT RS256) | Public key from `https://www.googleapis.com/oauth2/v3/certs` |

Note: OIDC endpoint paths vary by provider. Above are the standard paths for Auth0 and Okta org authorization servers. For custom Okta authorization servers, use `/oauth2/<authorizationServerId>/v1/keys`. For other providers (Keycloak, Azure AD, Google Identity), consult provider documentation. The framework accepts a configurable `jwks_uri`, not a provider enum.

```yaml
# framework.yaml
auth:
  provider: auth0               # auth0 | okta | keycloak | custom
  token_type: jwt               # jwt | opaque | api_key
  issuer: "https://my-app.auth0.com/"
  audience: "https://api.my-app.com"
  jwks_uri: "https://my-app.auth0.com/.well-known/jwks.json"
  claims_mapping:
    user_id: sub
    roles: "https://my-app.com/roles"
    scopes: scope
    tenant_id: "https://my-app.com/tenant_id"
```

### Option B: Custom Token Issuer

The framework calls a custom introspection endpoint for every token. Useful for legacy systems.

```yaml
auth:
  provider: custom
  token_type: opaque
  introspection_endpoint: "https://internal-auth.example.com/introspect"
  introspection_method: POST
  headers:
    Authorization: "Bearer ${INTROSPECTION_API_KEY}"
```

### Option C: API Key (Dev / Machine-to-Machine)

Simple key comparison. Not recommended for production user auth.

```yaml
auth:
  provider: api_key
  token_type: api_key
  api_keys:
    - key: "${DEV_API_KEY}"
      user_id: dev-user
      roles: [admin]
      scopes: ["*"]
      env: dev        # only active in dev
```

### 3.1 Comparison Matrix

| Dimension | Option A (OIDC Provider) | Option B (Custom Introspect) | Option C (API Key) |
|-----------|-------------------------|------------------------------|--------------------|
| Identity source | External (Auth0/Okta/Keycloak) | Custom legacy system | Static config |
| Token type | JWT | Opaque | API Key |
| Verification | Offline (public key) | Online (introspect call) | Hash compare |
| Latency | <1ms (cached JWKS) | ~50ms (HTTP call) | <1ms |
| Security | High (signed JWT) | Depends on introspection provider | Low (static key) |
| Scalability | Stateless, any instance | Extra traffic to introspect endpoint | N/A |
| Use case | Production | Legacy system bridge | Dev / M2M only |

---

## 4. Environment-Specific Auth

```yaml
# framework.yaml — per-environment override
auth:
  dev:
    provider: api_key           # skip full OAuth for local dev
    token_type: api_key
    api_keys:
      - key: "dev-token-123"
        user_id: dev-user
        roles: [admin]
        scopes: ["*"]

  e2e:
    provider: auth0
    token_type: jwt
    issuer: "https://e2e-auth.example.com/"
    audience: "https://api.e2e.example.com"

  prod:
    provider: auth0
    token_type: jwt
    issuer: "https://auth.example.com/"
    audience: "https://api.example.com"
```

---

## 5. Role-Based Access (Interface Placeholder)

All identity checks supported above answer the question: **"Who is this user?"** (Authentication).

**"What is this user allowed to do?"** (Authorization / Role-Based Access Control) is deferred to a future interface. The current design defines only the contract — the implementation will follow in a later spec.

### 5.1 RoleResolver Interface

```
RoleResolver {
  resolve(user_context: UserContext) → ResolvedRoles

  // External source → internal role mapping.
  // Source can be: IdP groups, LDAP, custom HR API, static config.
}

ResolvedRoles {
  user_id:       string
  groups:        string[]    // raw groups from IdP (e.g., "insurance_agent", "underwriter_l2")
  permissions:   string[]    // mapped permissions (e.g., "quote:read", "claim:approve")
  tenant_id?:    string
}
```

### 5.2 Configuration

```yaml
# framework.yaml — role resolution is a pluggable interface
auth:
  role_resolution:
    source: jwt_groups           # jwt_groups | ldap | custom_api | static | none
    # jwt_groups: read groups from the token itself (Okta/Azure AD include them)
    # none: skip role resolution entirely (identity-only mode)

  # When source = jwt_groups:
  jwt_groups:
    groups_claim: groups         # which JWT claim contains group names

  # When source = custom_api:
  custom_api:
    endpoint: "https://internal-hr.example.com/roles/{user_id}"
    cache_ttl_seconds: 300
```

### 5.3 What Is Deferred

| Question | Status |
|----------|--------|
| How to map IdP group names to internal tool/transition permissions | Deferred — will be part of permission model design |
| pycasbin integration for complex RBAC | Already defined in Tool Ecosystem spec §6, but the RoleResolver→casbin bridge is deferred |
| Custom role API contract | Deferred |
| Role change propagation (user promoted → permissions update without re-login) | Deferred |

---

## 6. Multi-Tenant Isolation

For SaaS deployments, the verified tenant from the token is injected into `agentState` and passed to every tool call.

```yaml
auth:
  multi_tenant: false             # true for SaaS
  tenant_claim: "https://my-app.com/tenant_id"    # JWT claim
```

When enabled, the framework:
- Injects `tenant_id` into agentState
- Scopes checkpoints to the tenant
- Tags audit logs with tenant

---

## 7. Audit Trail

Every identity verification records:

```
AuthAuditEntry {
  timestamp:        datetime
  user_id:          string
  auth_provider:    string
  token_valid:      boolean
  action:           "token_verified" | "token_expired" | "token_invalid"
  workflow_id?:     string
}
```

---

## 8. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should the framework cache JWKS keys in-memory with a TTL, or fetch on every request? | Latency vs key rotation safety |
| 2 | For multi-instance deployments, should token verification be centralized (API gateway) or per-instance? | Architecture complexity |
| 3 | Should the framework support token refresh (sliding expiration) or only initial verification? | Long-running conversations |
| 4 | How to handle token revocation — push notification from provider or poll the revocation list? | Security posture |
| 5 | Should the framework support multiple simultaneous auth providers (e.g., Auth0 for customers + Okta for internal operators)? | Enterprise deployment flexibility |
| 6 | RoleResolver — should it be a plugin architecture (like rule engines) or a single configurable module? | Extensibility vs simplicity |

---

## References

- [High-Level Design](./2026-06-16-deterministic-workflow-framework-design.md) — §4.4 Permission Model
- [Routing & Execution](./2026-06-17-routing-execution-layer-design.md) — §7 Permission Model details, §1.2 agentState concurrency
- [Tool Ecosystem](./2026-06-17-tool-ecosystem.md) — §6 pycasbin permission engine
- [Environment Config](./2026-06-17-environment-config.md) — per-environment auth settings
