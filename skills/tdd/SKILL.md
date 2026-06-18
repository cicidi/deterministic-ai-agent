---
name: tdd
description: "Test-driven development for deterministic workflows. Defines test cases before implementation. Mocks LLMs by default to save tokens — only calls real LLM when explicitly requested."
user-invocable: true
status: todo
---

# TDD for Workflows (TODO)

See `TODO.md` for full specification.

## Summary

After implement-interview produces an implementation plan, generates test cases FIRST:
- User dialog tests
- Extract node tests
- Validate node tests
- Decision node tests
- Response node tests

Mocks LLMs by default. Only `--use-real-llm` triggers actual API calls — same as traditional API integration test mocking.
