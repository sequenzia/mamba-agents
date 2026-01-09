"""Bash command execution tool."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass


@dataclass
class BashResult:
    """Result of a bash command execution.

    Attributes:
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        return_code: Exit code of the command.
        timed_out: Whether the command timed out.
    """

    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False


def run_bash(
    command: str,
    working_dir: str = ".",
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> BashResult:
    """Execute a shell command.

    Args:
        command: The shell command to execute.
        working_dir: Working directory for the command.
        timeout: Timeout in seconds (default: 30).
        env: Optional environment variables to add.

    Returns:
        BashResult with stdout, stderr, and return code.

    Raises:
        TimeoutError: If the command times out.
    """
    import os

    # Merge environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return BashResult(
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )
    except subprocess.TimeoutExpired as e:
        return BashResult(
            stdout=e.stdout or "" if isinstance(e.stdout, str) else (e.stdout or b"").decode(),
            stderr=e.stderr or "" if isinstance(e.stderr, str) else (e.stderr or b"").decode(),
            return_code=-1,
            timed_out=True,
        )


async def run_bash_async(
    command: str,
    working_dir: str = ".",
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> BashResult:
    """Execute a shell command asynchronously.

    Args:
        command: The shell command to execute.
        working_dir: Working directory for the command.
        timeout: Timeout in seconds (default: 30).
        env: Optional environment variables to add.

    Returns:
        BashResult with stdout, stderr, and return code.
    """
    import os

    # Merge environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            env=full_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )

        return BashResult(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            return_code=proc.returncode or 0,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return BashResult(
            stdout="",
            stderr="Command timed out",
            return_code=-1,
            timed_out=True,
        )
