"""Module for executing shell commands asynchronously in cloud-autopkg-runner.

This module provides functions for running shell commands in a non-blocking
manner, capturing their output, and handling errors. It is used to
interact with external tools and processes during AutoPkg workflows.
"""

import asyncio
import shlex
from typing import Optional, Union

from cloud_autopkg_runner import logger
from cloud_autopkg_runner.exceptions import AutoPkgRunnerException


async def run_cmd(
    cmd: Union[str, list[str]],
    cwd: Optional[str] = None,
    check: bool = True,
    capture_output: bool = True,
    timeout: Optional[int] = None,
) -> tuple[int, str, str]:
    """Asynchronously executes a command in a subprocess.

    This function provides a robust and flexible way to run shell commands,
    capturing their output, handling errors, and managing timeouts.

    Args:
        cmd: The command to execute. It can be provided as a string, which
            will be parsed using `shlex.split()`, or as a pre-split list of
            strings. Using a list is safer if you are constructing the command
            programmatically.
        cwd: An optional working directory to execute the command in. If `None`,
            the current working directory is used.
        check: A boolean value. If `True` (the default), an
            `AutoPkgRunnerException` is raised if the command returns a non-zero
            exit code. If `False`, the function will not raise an exception for
            non-zero exit codes, and the caller is responsible for checking the
            returned exit code.
        capture_output: A boolean value. If `True` (the default), the
            command's standard output and standard error are captured and
            returned as strings. If `False`, the command's output is directed
            to the parent process's standard output and standard error, and
            empty strings are returned for stdout and stderr.
        timeout: An optional integer specifying a timeout in seconds. If the
            command exceeds this timeout, it will be terminated, and the
            function will return a -1 returncode. If `None`, the command will
            run without a timeout.

    Returns:
        A tuple containing:
            - returncode (int): The exit code of the command. It will be -1 if the
              command times out or if another error prevents the process from
              completing.
            - stdout (str): The standard output of the command (if
              `capture_output` is `True`).
            - stderr (str): The standard error of the command (if
              `capture_output` is `True`).

    Raises:
        AutoPkgRunnerException: If any of the following occur:
            - The `cmd` string is invalid and cannot be parsed by `shlex.split()`.
            - The command returns a non-zero exit code and `check` is `True`.
            - A `FileNotFoundError` occurs (the command is not found).
            - An `OSError` occurs during subprocess creation.
            - Any other unexpected exception occurs during command execution.
    """
    if isinstance(cmd, str):
        try:
            cmd_list = shlex.split(cmd)
            cmd_str = cmd
        except ValueError as exc:
            raise AutoPkgRunnerException(
                f"Invalid command string: {cmd}. Error: {exc}"
            ) from exc
    else:
        cmd_list = cmd
        cmd_str = " ".join(cmd)

    logger.debug(f"Running command: {cmd_str}")
    if cwd:
        logger.debug(f"  in directory: {cwd}")

    returncode: int = -1

    try:
        if capture_output:
            proc = await asyncio.create_subprocess_exec(
                *cmd_list,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(*cmd_list, cwd=cwd)

        try:
            if capture_output:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
            else:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
                stdout, stderr = "", ""  # No output captured

        except asyncio.TimeoutError:
            logger.warning(f"Command timed out: {cmd_str}")
            if proc.returncode is None:  # Process still running
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

            stdout = ""
            stderr = f"Command timed out after {timeout} seconds."

            return returncode, stdout, stderr

        returncode = proc.returncode if proc.returncode is not None else -1

    except FileNotFoundError as exc:
        raise AutoPkgRunnerException(f"Command not found: {cmd_list[0]}") from exc
    except OSError as exc:
        raise AutoPkgRunnerException(
            f"OS error running command: {cmd_str}. Error: {exc}"
        ) from exc
    except Exception as exc:
        raise AutoPkgRunnerException(
            f"Unexpected error running command: {cmd_str}. Error: {exc}"
        ) from exc

    if check and returncode != 0:
        logger.error(f"Command failed: {cmd_str}")
        logger.error(f"  Exit code: {returncode}")
        logger.error(f"  Stdout: {stdout}")
        logger.error(f"  Stderr: {stderr}")
        raise AutoPkgRunnerException(
            f"Command failed with exit code {returncode}: {cmd_str}"
        )

    if capture_output:
        logger.debug(f"Command output:\n{stdout}\n{stderr}")

    return returncode, stdout, stderr
