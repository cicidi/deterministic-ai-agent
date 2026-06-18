---
name: multi-llm-runner
description: "Runs the same eval test suite across multiple LLM providers side-by-side. Compares accuracy, latency, and cost. Also tests client-side LLM understanding of our agent's responses."
user-invocable: true
status: todo
---

# Multi-LLM Runner (TODO)

See `TODO.md` for full specification.

## Summary

1. Load eval test suites (from evals-create skill)
2. Run same test cases against multiple LLMs: deepseek-v4, gpt-4o, claude-sonnet, etc.
3. Compare: accuracy, latency, token cost per LLM
4. Client-side LLM test: simulate user receiving our response → can the client LLM correctly understand the next step?
5. Output comparison report + recommendation

## Open-Source Frameworks

| Framework | Purpose | Use |
|-----------|---------|-----|
| **promptfoo** | Multi-provider LLM evaluation | Run same prompt suite against multiple models, compare side-by-side |
| **DeepEval** | LLM evaluation metrics | Faithfulness, relevancy, correctness scores per model |
| **RAGAS** | RAG pipeline evaluation | Evaluate knowledge base retrieval quality |
