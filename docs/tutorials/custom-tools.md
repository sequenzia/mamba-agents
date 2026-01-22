# Creating Custom Tools

Learn how to create, test, and register custom tools for your Mamba Agents.

## What You'll Learn

- Create tools using decorators
- Handle parameters and return values
- Implement error handling
- Test your tools

## Prerequisites

- Python 3.12+
- Mamba Agents installed
- Basic understanding of type hints

## Step 1: Simple Tool with Decorator

The simplest way to create a tool is with the `@agent.tool` decorator:

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")

@agent.tool
def greet(name: str) -> str:
    """
    Greet a person by name.

    Args:
        name: The person's name to greet

    Returns:
        A friendly greeting message
    """
    return f"Hello, {name}! Nice to meet you."
```

## Step 2: Tool with Multiple Parameters

```python
@agent.tool
def calculate_area(length: float, width: float, unit: str = "meters") -> str:
    """
    Calculate the area of a rectangle.

    Args:
        length: The length of the rectangle
        width: The width of the rectangle
        unit: The unit of measurement (default: meters)

    Returns:
        The calculated area with units
    """
    area = length * width
    return f"The area is {area:.2f} square {unit}"
```

## Step 3: Async Tools

For operations that need to be async:

```python
import httpx

@agent.tool
async def fetch_weather(city: str) -> str:
    """
    Fetch weather information for a city.

    Args:
        city: The city name

    Returns:
        Weather information for the city
    """
    async with httpx.AsyncClient() as client:
        # Using a mock API for demonstration
        response = await client.get(
            f"https://api.weather.example.com/{city}"
        )
        data = response.json()
        return f"Weather in {city}: {data['temperature']}°C, {data['conditions']}"
```

## Step 4: Error Handling

By default, Mamba Agents automatically handles tool exceptions. When a tool raises an exception, it's converted to a `ModelRetry` that the LLM receives as an error message, allowing it to try a different approach.

```python
@agent.tool
def read_json_file(filepath: str) -> str:
    """
    Read and parse a JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        The parsed JSON content
    """
    import json

    with open(filepath) as f:
        return json.dumps(json.load(f), indent=2)
    # FileNotFoundError, JSONDecodeError, etc. are handled automatically
```

If the LLM calls this with an invalid path, it receives the error message and can retry with a different path.

### Custom Error Messages (Optional)

For more helpful error messages, you can still catch exceptions manually:

```python
@agent.tool
def read_json_file(filepath: str) -> str:
    """Read and parse a JSON file."""
    import json

    try:
        with open(filepath) as f:
            return json.dumps(json.load(f), indent=2)
    except FileNotFoundError:
        return f"Error: File '{filepath}' not found. Try listing the directory first."
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON at line {e.lineno} - {e.msg}"
```

### Critical Tools

For tools where failures should stop execution immediately, disable graceful error handling:

```python
@agent.tool_plain(graceful_errors=False)
def deploy_to_production(version: str) -> str:
    """Deploy to production - failures must stop the workflow."""
    # Exceptions will propagate and stop the agent
    ...
```

## Step 5: Using tool_plain

Use `tool_plain` when you don't need the agent context:

```python
@agent.tool_plain
def get_current_time() -> str:
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@agent.tool_plain
def generate_uuid() -> str:
    """Generate a unique identifier."""
    import uuid
    return str(uuid.uuid4())
```

## Step 6: Standalone Tool Functions

Create tools as standalone functions:

```python
def search_database(query: str, limit: int = 10) -> list[dict]:
    """
    Search the database for matching records.

    Args:
        query: Search query string
        limit: Maximum results to return

    Returns:
        List of matching records
    """
    # Your database logic here
    results = [
        {"id": 1, "name": "Result 1"},
        {"id": 2, "name": "Result 2"},
    ]
    return results[:limit]


# Register with agent
agent = Agent("gpt-4o", tools=[search_database])
```

## Step 7: Tools with Complex Types

Use Pydantic models for complex inputs/outputs:

```python
from pydantic import BaseModel
from typing import Optional

class SearchParams(BaseModel):
    query: str
    filters: Optional[dict] = None
    page: int = 1
    per_page: int = 10

class SearchResult(BaseModel):
    total: int
    results: list[dict]

@agent.tool
def advanced_search(params: SearchParams) -> SearchResult:
    """
    Perform an advanced search with filters.

    Args:
        params: Search parameters including query and filters

    Returns:
        Search results with total count
    """
    # Search logic here
    return SearchResult(
        total=100,
        results=[{"id": 1, "title": "Match"}]
    )
```

## Complete Example

Here's a complete example with multiple tools:

```python
import asyncio
from datetime import datetime
from mamba_agents import Agent, AgentConfig

# Create agent
agent = Agent(
    "gpt-4o",
    config=AgentConfig(
        system_prompt="You are a helpful assistant with various tools."
    ),
)

@agent.tool_plain
def get_timestamp() -> str:
    """Get current timestamp."""
    return datetime.now().isoformat()

@agent.tool
def math_operation(a: float, b: float, operation: str) -> str:
    """
    Perform a math operation.

    Args:
        a: First number
        b: Second number
        operation: One of: add, subtract, multiply, divide

    Returns:
        The result of the operation
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else "Error: Division by zero",
    }

    if operation not in operations:
        return f"Error: Unknown operation '{operation}'"

    result = operations[operation](a, b)
    return f"{a} {operation} {b} = {result}"

@agent.tool
def format_text(text: str, style: str = "upper") -> str:
    """
    Format text in different styles.

    Args:
        text: The text to format
        style: Format style (upper, lower, title, reverse)

    Returns:
        The formatted text
    """
    styles = {
        "upper": str.upper,
        "lower": str.lower,
        "title": str.title,
        "reverse": lambda s: s[::-1],
    }

    if style not in styles:
        return f"Error: Unknown style '{style}'"

    return styles[style](text)


async def main():
    # Test the tools
    result = await agent.run("What time is it?")
    print(result.output)

    result = await agent.run("Calculate 15 multiplied by 7")
    print(result.output)

    result = await agent.run("Format 'hello world' in title case")
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Tools

Test your tools independently:

```python
import pytest

def test_math_operation():
    result = math_operation(10, 5, "add")
    assert "15" in result

def test_math_operation_divide_by_zero():
    result = math_operation(10, 0, "divide")
    assert "Error" in result

def test_format_text():
    result = format_text("hello", "upper")
    assert result == "HELLO"
```

## Best Practices

1. **Clear Docstrings** - The model reads them to understand tool usage
2. **Type Hints** - Always include parameter and return types
3. **Let Errors Propagate** - Graceful error handling catches exceptions automatically; only add manual handling for custom error messages
4. **Validation** - Validate inputs before processing
5. **Concise Returns** - Keep return values informative but not excessive
6. **Critical Tools** - Use `graceful_errors=False` for tools that must fail loudly

## Next Steps

- [Agent Basics](../user-guide/agent-basics.md) - Using tools with agents
- [Tools API](../api/tools/index.md) - Built-in tools reference
- [ReAct Workflow](react-workflow.md) - Tools in workflows
