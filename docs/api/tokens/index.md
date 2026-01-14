# Tokens Module

Token counting and cost estimation.

## Classes

| Class | Description |
|-------|-------------|
| [TokenCounter](counter.md) | Count tokens in text |
| [UsageTracker](tracker.md) | Track usage across requests |
| [CostEstimator](cost.md) | Estimate costs |

## Quick Example

```python
from pydantic_agent.tokens import TokenCounter, UsageTracker, CostEstimator

# Count tokens
counter = TokenCounter()
count = counter.count("Hello, world!")

# Track usage
tracker = UsageTracker()
tracker.record_usage(prompt_tokens=100, completion_tokens=50)
usage = tracker.get_total_usage()

# Estimate cost
estimator = CostEstimator()
cost = estimator.estimate(usage, model="gpt-4o")
```

## Imports

```python
from pydantic_agent import TokenUsage, UsageRecord, CostBreakdown
from pydantic_agent.tokens import TokenCounter, UsageTracker, CostEstimator
```
