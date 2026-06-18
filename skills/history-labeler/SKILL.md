---
name: history-labeler
description: "Labels correct/incorrect conversation turns from history logs. Correctly handled turns → positive examples. Incorrectly handled turns → negative examples. Generates labeled test datasets for retraining and eval."
user-invocable: true
status: todo
---

# History Labeler (TODO)

See `TODO.md` for full specification.

## Summary

1. Load production conversation history logs
2. For each turn, determine if it was handled correctly:
   - Correct: intent matched, entities extracted, next step progressed
   - Incorrect: unrecognized_intent, validation failed, goal check 422, user rephrased
3. Label correctly handled turns as positive, incorrect as incorrect
4. Output labeled dataset for retraining/eval

## Open-Source Frameworks

| Framework | Purpose | Use |
|-----------|---------|-----|
| **Argilla** | Data labeling platform | Annotate conversation turns as correct/incorrect |
| **Label Studio** | Data labeling tool | Alternative to Argilla |
| **TRL (Transformers RLHF)** | RLHF training | Fine-tune models with labeled data |
