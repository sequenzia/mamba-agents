"""ReAct (Reasoning and Acting) workflow implementation.

This module provides the ReActWorkflow class that implements the ReAct paradigm
for agentic task execution. ReAct interleaves reasoning traces (Thoughts) with
task-specific actions, enabling dynamic reasoning and plan adjustment.

Example:
    >>> from pydantic_agent import Agent
    >>> from pydantic_agent.workflows.react import ReActWorkflow, ReActConfig
    >>>
    >>> agent = Agent("gpt-4o", tools=[read_file, run_bash])
    >>> workflow = ReActWorkflow(
    ...     agent=agent,
    ...     config=ReActConfig(max_iterations=10),
    ... )
    >>> result = workflow.run_sync("Find the bug in main.py")
    >>> print(result.output)
"""

from pydantic_agent.workflows.react.config import ReActConfig
from pydantic_agent.workflows.react.hooks import ReActHooks
from pydantic_agent.workflows.react.state import ReActState, ScratchpadEntry
from pydantic_agent.workflows.react.workflow import ReActWorkflow

__all__ = [
    "ReActConfig",
    "ReActHooks",
    "ReActState",
    "ReActWorkflow",
    "ScratchpadEntry",
]
