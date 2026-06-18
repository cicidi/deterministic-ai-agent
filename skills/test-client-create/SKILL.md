---
name: test-client-create
description: "Creates a simulated LLM-based test client that drives conversations to completion and measures end-to-end transaction completion rate."
user-invocable: true
status: todo
---

# Test Client Create (TODO)

See `TODO.md` for full specification.

## Summary

Creates a test client LLM persona that:
1. Receives the agent's response
2. Understands the conversation state
3. Generates a natural next user message
4. Continues until the workflow completes or abandons

Measures: completion rate, average turns, drop-off points, intent switch frequency, clarification rate.
