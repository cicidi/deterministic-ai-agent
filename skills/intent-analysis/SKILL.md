---
name: intent-analysis
description: "Analyzes production conversation logs to find unhandled intents. Outputs prioritized gap report. Goal: today better than yesterday."
user-invocable: true
status: todo
---

# Intent Analysis (TODO)

See `TODO.md` for full specification.

## Summary

Analyzes production conversation logs to identify intents the current classifier cannot handle. Determines whether new intents should be added, whether they are edge cases of existing intents, or whether they are out of scope.

Outputs: "Today we missed X intents. Yesterday we missed Y. Change: +/-Z"
