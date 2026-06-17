# Redaction Service Design — PII Detection & Tokenization

**Status:** Draft
**Scope:** Architecture discussion only. No implementation code.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-17 | 0.1.0 | Initial draft: three-layer detection, redaction key pattern, vault storage |

---

## 1. Problem Statement

Chat messages contain PII (names, card numbers, addresses, phone numbers, etc.). Chat history must never store raw PII. A redaction service is needed to:

1. Detect and extract PII from incoming messages
2. Replace PII with redaction keys (placeholder tokens)
3. Store the original PII in a separate, secure vault
4. Allow authorized access to reveal original values when needed

---

## 2. Architecture: Three-Layer Detection

```
User Message (raw)
       │
       ▼
┌─────────────────────────────┐
│ Layer 1: Regex & Pattern    │  ← Deterministic, no LLM
│ - Credit card numbers        │
│ - Phone numbers              │
│ - Email addresses            │
│ - SSN / ID numbers           │
│ - IBAN / bank accounts       │
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ Layer 2: Entity Recognition  │  ← ML-based NER
│ - Person names               │
│ - Addresses                  │
│ - Organization names         │
│ - Dates of birth             │
│ - Custom entity types        │
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ Layer 3: Context-Aware LLM   │  ← LLM for ambiguous cases
│ - "my wife's name is..."     │
│ - Implicit PII references    │
│ - Cross-sentence context     │
└────────────┬────────────────┘
             ▼
       Redacted Message
```

### Layer 1: Regex & Pattern (Deterministic)

| Pattern | Example | Regex Hint |
|---------|---------|------------|
| Credit card | `4111-1111-1111-1111` | Luhn check + format |
| Phone | `+86 138-0000-0000` | Country-specific patterns |
| Email | `user@example.com` | RFC 5322 |
| SSN/ID | `123-45-6789` | Format patterns |
| IBAN | `DE89 3704 0044 0532 0130 00` | Country prefix + checksum |

### Layer 2: ML-Based NER

- Model: spaCy / HuggingFace NER pipeline (configurable)
- Entity types: PERSON, ADDRESS, ORG, DATE_OF_BIRTH, LOCATION
- Custom entity training for domain-specific PII (e.g., insurance policy numbers)

### Layer 3: LLM Context-Aware

- Triggered when Layer 1+2 flag "possible" but uncertain
- LLM resolves ambiguity: "the guy who called yesterday" → not PII; "my account 1234" → partial PII
- Can be turned off for latency-sensitive paths; missing a PII is a false negative risk tradeoff

---

## 3. Redaction Key Pattern

Each detected PII span is replaced with a deterministic key:

```
Raw:     "我叫张三，卡号 6222-1234-5678-9012，电话 13800000000"
         │        │                        │
         ▼        ▼                        ▼
Masked:  "我叫 <REDACT_k1>，卡号 <REDACT_k2>，电话 <REDACT_k3>"
```

### Key Format

```
<REDACT_{vault_id}:{key_id}>
```

- `vault_id`: identifies which redaction vault (tenant-scoped)
- `key_id`: unique key within that vault
- Vault stores: `{key_id: "张三", key_id: "6222-1234-5678-9012", ...}`

### Key Properties

| Property | Strategy |
|----------|----------|
| Uniqueness | UUID per detected span |
| Determinism | Same PII value across messages → same key (for dedup in vault) |
| Non-reversible | Key alone reveals nothing; must call `reveal()` with auth |
| Format-safe | `<REDACT_*>` does not break JSON/XML/embedded markup |

---

## 4. Redaction Flow

```
┌──────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Client   │────▶│ Redaction Svc   │────▶│ Redaction Vault   │
│ (Gateway) │     │                 │     │ (Separate DB)     │
└──────────┘     │ 1. Detect PII   │     │                   │
                 │ 2. Generate keys│     │ key: "张三"        │
                 │ 3. Replace text │     │ key: "6222-..."    │
                 │ 4. Store in     │     │ key: "138..."      │
                 │    vault ───────┼────▶│                   │
                 │                 │     └──────────────────┘
                 │ 5. Return       │
                 │    masked_text──┼────▶ Chat History Store
                 │    + key_list   │     (只存 masked 版本)
                 └─────────────────┘
```

### API

```
POST /redact
  Request:  { "text": "我叫张三，卡号 6222...", "tenant_id": "t_001" }
  Response: {
    "masked_text": "我叫 <REDACT_t_001:k1>，卡号 <REDACT_t_001:k2>",
    "keys": [
      {"key": "k1", "type": "person_name", "source": "layer_2_ner"},
      {"key": "k2", "type": "credit_card", "source": "layer_1_regex"}
    ]
  }

POST /reveal
  Request:  { "keys": ["k1", "k2"], "tenant_id": "t_001", "auth": "..." }
  Response: { "k1": "张三", "k2": "6222-1234-5678-9012" }

DELETE /vault/{tenant_id}/keys
  Request:  { "keys": ["k1", "k2"] }
  Purpose:  GDPR "right to be forgotten" — purge PII from vault
```

---

## 5. Redaction Vault Storage

Vault is physically separate from chat history storage. Options:

| Backend | Use Case |
|---------|----------|
| PostgreSQL (separate schema/db) | Standard, same ops team |
| HashiCorp Vault | Enterprise secrets management |
| AWS KMS + DynamoDB | Cloud-native encryption |
| Hardware HSM | Maximum security (payment industry) |

Interface abstraction:

```python
class RedactionVault(ABC):
    @abstractmethod
    def store(self, tenant_id: str, key: str, value: str, pii_type: str) -> None: ...
    @abstractmethod
    def reveal(self, tenant_id: str, keys: list[str], auth: AuthContext) -> dict[str, str]: ...
    @abstractmethod
    def delete(self, tenant_id: str, keys: list[str]) -> None: ...
    @abstractmethod
    def audit_access(self, tenant_id: str, key: str) -> list[AccessLog]: ...
```

---

## 6. ChatHistory Message Integration

ChatHistory 只存脱敏后的消息：

```python
@dataclass
class ChatMessage:
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str              # ← 已是 redacted 版本，无原始 PII
    redaction_keys: list[str] # ← ["k1", "k2", "k3"] 用于审计关联
    token_count: int | None
    turn_number: int
    meta: dict
    created_at: datetime
```

存消息前调用 `POST /redact`，拿到 `masked_text` 和 `keys` 后写入 ChatHistory。

---

## 7. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Layer 2 NER model selection — spaCy vs HuggingFace vs cloud API? | Deferred to implementation |
| 2 | Layer 3 LLM latency budget — how many ms acceptable before fallback to Layer 1+2 only? | Deferred to implementation |
| 3 | Deterministic key generation — same value → same key: use hash or vault lookup first? | Hash preferred for dedup, with salt per tenant |
| 4 | Vault encryption at rest — which encryption standard and key rotation policy? | Deferred to security review |
| 5 | Batch redaction for high-throughput — support `POST /redact/batch`? | Yes, for bulk message processing |

---

## References

- [Chat History Storage Design](./2026-06-17-chat-history-storage-design.md)
- [Deterministic Workflow Framework Design](./2026-06-16-deterministic-workflow-framework-design.md)
- PCI DSS v4.0 — Requirement 3.4: Render PAN unreadable
- GDPR Art. 17 — Right to erasure ("right to be forgotten")
