"""ReAct (Reasoning and Acting) workflow implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

from mamba_agents.workflows.base import Workflow, WorkflowState, WorkflowStep
from mamba_agents.workflows.errors import WorkflowMaxIterationsError
from mamba_agents.workflows.react.config import ReActConfig
from mamba_agents.workflows.react.hooks import ReActHooks
from mamba_agents.workflows.react.prompts import (
    build_iteration_prompt,
    format_tool_call,
)
from mamba_agents.workflows.react.state import ReActState
from mamba_agents.workflows.react.termination import (
    detect_final_answer,
    extract_text_content,
    extract_tool_calls,
    extract_tool_results,
)
from mamba_agents.workflows.react.tools import create_final_answer_tool

if TYPE_CHECKING:
    from mamba_agents import Agent
    from mamba_agents.prompts import PromptManager
    from mamba_agents.tokens.tracker import TokenUsage

DepsT = TypeVar("DepsT")


class ReActWorkflow(Workflow[DepsT, str, ReActState]):
    """ReAct (Reasoning + Acting) workflow implementation.

    Implements the Thought -> Action -> Observation loop until the agent
    calls the final_answer tool to signal task completion.

    The workflow:
    1. Sends the task to the agent
    2. Agent thinks and calls tools
    3. Tool results become observations
    4. Loop continues until final_answer is called or max_iterations reached

    Example:
        >>> from mamba_agents import Agent
        >>> from mamba_agents.workflows.react import ReActWorkflow, ReActConfig
        >>>
        >>> agent = Agent("gpt-4o", tools=[read_file, run_bash])
        >>> workflow = ReActWorkflow(
        ...     agent=agent,
        ...     config=ReActConfig(max_iterations=10),
        ... )
        >>> result = workflow.run_sync("Find the bug in main.py")
        >>> print(result.output)  # Final answer
        >>> print(result.state.context.scratchpad)  # All steps
    """

    def __init__(
        self,
        agent: Agent[DepsT, Any],
        config: ReActConfig | None = None,
        hooks: ReActHooks | None = None,
        prompt_manager: PromptManager | None = None,
    ) -> None:
        """Initialize the ReAct workflow.

        Args:
            agent: Agent instance to use for execution.
            config: ReAct-specific configuration.
            hooks: Optional hooks for observability.
            prompt_manager: Optional PromptManager for template resolution.
        """
        self._react_config = config or ReActConfig()
        super().__init__(self._react_config, hooks)

        self._agent = agent
        self._react_hooks: ReActHooks = hooks or ReActHooks()
        self._last_state: ReActState | None = None
        self._prompt_manager = prompt_manager

        # Register the final_answer tool
        self._agent.tool_plain(
            create_final_answer_tool(),
            name=self._react_config.final_answer_tool_name,
            retries=self._react_config.tool_retry_count,
        )

    @property
    def name(self) -> str:
        """Get the workflow name."""
        return "react"

    @property
    def agent(self) -> Agent[DepsT, Any]:
        """Get the agent instance."""
        return self._agent

    @property
    def react_config(self) -> ReActConfig:
        """Get the ReAct-specific configuration."""
        return self._react_config

    @property
    def prompt_manager(self) -> PromptManager | None:
        """Get the prompt manager.

        Returns None if no prompt manager was provided or created.
        """
        return self._prompt_manager

    def _get_prompt_manager(self) -> PromptManager:
        """Get or create the prompt manager.

        Returns:
            PromptManager instance.
        """
        if self._prompt_manager is not None:
            return self._prompt_manager

        # Try to use agent's prompt manager
        if self._agent.prompt_manager is not None:
            return self._agent.prompt_manager

        # Create from agent settings
        from mamba_agents.prompts import PromptManager

        self._prompt_manager = PromptManager(config=self._agent.settings.prompts)
        return self._prompt_manager

    def _build_iteration_prompt(
        self,
        react_state: ReActState,
        force_action: bool = False,
    ) -> str:
        """Build the prompt for a ReAct iteration.

        Uses template if configured, otherwise falls back to default.

        Args:
            react_state: Current ReAct state.
            force_action: Whether to force action prompt.

        Returns:
            Prompt string for the iteration.
        """
        # Check if custom template is configured
        template_config = self._react_config.iteration_prompt_template
        if template_config is not None:
            manager = self._get_prompt_manager()
            return manager.render(
                name=template_config.name,
                version=template_config.version,
                scratchpad=react_state.get_scratchpad_text(self._react_config),
                force_action=force_action,
                config=self._react_config,
                **template_config.variables,
            )

        # Fall back to default implementation
        return build_iteration_prompt(
            self._react_config,
            react_state.get_scratchpad_text(self._react_config),
            force_action=force_action,
        )

    def _create_initial_state(self, prompt: str) -> WorkflowState[ReActState]:
        """Create initial workflow state.

        Args:
            prompt: The user's task/prompt.

        Returns:
            Initialized WorkflowState with ReActState context.
        """
        return WorkflowState(context=ReActState(task=prompt))

    async def _execute(
        self,
        prompt: str,
        state: WorkflowState[ReActState],
        deps: DepsT | None = None,
    ) -> str:
        """Execute the ReAct loop.

        Args:
            prompt: The user's task/prompt.
            state: Current workflow state.
            deps: Optional dependencies for agent calls.

        Returns:
            The final answer string.

        Raises:
            WorkflowMaxIterationsError: If max iterations exceeded.
        """
        react_state = state.context
        if react_state is None:
            raise ValueError("ReActState context is required")

        # Store reference for accessor methods
        self._last_state = react_state

        iteration = 0
        max_iter = self._react_config.max_iterations

        while iteration < max_iter and not react_state.is_terminated:
            iteration += 1
            state.iteration_count = iteration

            # Trigger iteration start hook
            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_iteration_start(state, iteration)

            # Check for context compaction
            await self._maybe_compact(react_state)

            # Determine if we need to force action
            force_action = (
                react_state.consecutive_thought_count >= self._react_config.max_consecutive_thoughts
            )

            # Build the iteration prompt
            if iteration == 1:
                # First iteration: use original prompt with system context
                iteration_prompt = prompt
            else:
                # Subsequent iterations: include scratchpad
                iteration_prompt = self._build_iteration_prompt(
                    react_state,
                    force_action=force_action,
                )

            # Create step record
            step = WorkflowStep(
                step_number=state.current_step,
                step_type="react_iteration",
                description=f"ReAct iteration {iteration}",
                input_data=iteration_prompt,
            )

            # Trigger step start hook
            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_step_start(
                    state, state.current_step, "react_iteration"
                )

            try:
                # Run the agent
                result = await self._agent.run(iteration_prompt, deps=deps)

                # Track token usage for this iteration
                usage = result.usage()
                iter_tokens = getattr(usage, "total_tokens", 0) or 0
                react_state.iteration_token_counts.append(iter_tokens)
                react_state.total_tokens_used += iter_tokens

                # Process the result
                await self._process_iteration_result(result, react_state)

                # Complete step record
                step.output_data = react_state.current_observation or react_state.current_thought
                step.agent_result = result
                step.completed_at = datetime.now(UTC)
                state.add_step(step)

                # Trigger step complete hook
                if self._react_config.enable_hooks:
                    await self._react_hooks.trigger_step_complete(state, step)

            except Exception as e:
                # Record error in step
                step.error = str(e)
                step.completed_at = datetime.now(UTC)
                state.add_step(step)

                # Trigger step error hook
                if self._react_config.enable_hooks:
                    await self._react_hooks.trigger_step_error(state, step, e)

                raise

            # Trigger iteration complete hook
            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_iteration_complete(state, iteration)

        # Check if we terminated normally
        if not react_state.is_terminated:
            react_state.is_terminated = True
            react_state.termination_reason = "max_iterations"
            raise WorkflowMaxIterationsError(
                f"ReAct workflow exceeded {max_iter} iterations without final answer"
            )

        return react_state.final_answer or ""

    async def _process_iteration_result(
        self,
        result: Any,
        react_state: ReActState,
    ) -> None:
        """Process an agent iteration result.

        Extracts thoughts, actions, and observations from the result
        and updates the ReAct state accordingly.

        Args:
            result: AgentResult from agent.run().
            react_state: Current ReAct state to update.
        """
        # Check for final_answer termination
        is_terminated, final_answer = detect_final_answer(
            result, self._react_config.final_answer_tool_name
        )

        if is_terminated:
            react_state.is_terminated = True
            react_state.termination_reason = "final_answer_tool"
            react_state.final_answer = final_answer

            # Add final observation
            react_state.add_observation(
                f"Task completed with answer: {final_answer}",
                metadata={"is_final": True},
            )
            return

        # Extract tool calls and results
        tool_calls = extract_tool_calls(result)
        tool_results = extract_tool_results(result)

        # Extract text content as thought
        text_content = extract_text_content(result)
        if text_content:
            react_state.add_thought(text_content)
            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_thought(react_state, text_content)

        # Process tool calls as actions
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            # Skip final_answer since it's handled above
            if tool_name == self._react_config.final_answer_tool_name:
                continue

            action_str = format_tool_call(tool_name, tool_args)
            react_state.add_action(
                action_str,
                metadata={"tool_name": tool_name, "tool_args": tool_args},
            )

            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_action(react_state, tool_name, tool_args)

        # Process tool results as observations
        for tr in tool_results:
            tool_name = tr["name"]
            content = tr["content"]

            # Skip final_answer confirmation
            if tool_name == self._react_config.final_answer_tool_name:
                continue

            # Check if this is an error observation
            is_error = content.startswith("Error:") or content.startswith("Exception:")

            react_state.add_observation(
                content,
                metadata={"tool_name": tool_name, "is_error": is_error},
            )

            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_observation(react_state, content, is_error)

    async def _maybe_compact(self, react_state: ReActState) -> None:
        """Check if context compaction is needed and perform it.

        Args:
            react_state: Current ReAct state to update compaction count.
        """
        if not self._react_config.auto_compact_in_workflow:
            return

        if self._agent.context_manager is None:
            return

        # Get current context state
        try:
            ctx = self._agent.get_context_state()
        except RuntimeError:
            # Context tracking disabled
            return

        # Calculate threshold using public config property
        compaction_config = self._agent.context_manager.config
        threshold = (
            self._react_config.compact_threshold_ratio * compaction_config.trigger_threshold_tokens
        )

        if ctx.token_count >= threshold:
            compaction_result = await self._agent.compact()
            react_state.compaction_count += 1

            if self._react_config.enable_hooks:
                await self._react_hooks.trigger_compaction(compaction_result)

    def get_token_usage(self) -> TokenUsage:
        """Get token usage statistics.

        Delegates to the agent's usage tracker.

        Returns:
            TokenUsage with total prompt/completion/total tokens.
        """
        return self._agent.get_usage()

    def get_cost(self) -> float:
        """Get estimated cost.

        Delegates to the agent's cost estimator.

        Returns:
            Estimated cost in USD.
        """
        return self._agent.get_cost()

    def get_scratchpad(self) -> list:
        """Get the scratchpad entries from the last run.

        Returns:
            List of ScratchpadEntry objects, or empty list if no run yet.
        """
        if self._last_state is None:
            return []
        return self._last_state.scratchpad

    def get_reasoning_trace(self) -> str:
        """Get formatted reasoning trace from the last run.

        Returns:
            Formatted scratchpad text, or empty string if no run yet.
        """
        if self._last_state is None:
            return ""
        return self._last_state.get_scratchpad_text(self._react_config)
