# CostEstimator

Estimate costs based on token usage.

## Quick Example

```python
from pydantic_agent.tokens import CostEstimator

estimator = CostEstimator()

# Estimate cost
breakdown = estimator.estimate(
    prompt_tokens=1000,
    completion_tokens=500,
    model="gpt-4o",
)
print(f"Total: ${breakdown.total_cost:.4f}")

# Custom rates
estimator.set_rate("my-model", 0.002)

# Get rates
all_rates = estimator.get_all_rates()
```

## Default Rates

| Model | Input (per 1M) | Output (per 1M) |
|-------|----------------|-----------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| Local models | $0.00 | $0.00 |

## API Reference

::: pydantic_agent.tokens.cost.CostEstimator
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.tokens.cost.CostBreakdown
    options:
      show_root_heading: true
