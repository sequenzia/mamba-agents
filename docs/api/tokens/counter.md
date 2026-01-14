# TokenCounter

Token counting using tiktoken.

## Quick Example

```python
from pydantic_agent.tokens import TokenCounter

counter = TokenCounter(encoding="cl100k_base")

# Count text tokens
count = counter.count("Hello, world!")

# Count message tokens
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
]
count = counter.count_messages(messages)
```

## API Reference

::: pydantic_agent.tokens.counter.TokenCounter
    options:
      show_root_heading: true
      show_source: true
