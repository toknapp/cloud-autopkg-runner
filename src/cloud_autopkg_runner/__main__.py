"""The main entry point for the cloud-autopkg-runner application.

This module defines the `main` function, which is executed when the
package is run as a script. It handles command-line argument parsing,
initialization, and orchestration of the main application logic.

The `main` function initializes the logging system, generates a list
of recipes to be processed, loads the metadata cache, creates dummy
files based on the recipe list and metadata, retrieves AutoPkg
preferences from the user's system, and processes the recipe list using
AutoPkg override directories. It leverages asynchronous programming to
execute these tasks efficiently.
"""

import asyncio
import json
import os
import signal
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from pathlib import Path
from types import FrameType
from typing import Iterable, NoReturn, Optional

from cloud_autopkg_runner import AppConfig, logger
from cloud_autopkg_runner.autopkg_prefs import AutoPkgPrefs
from cloud_autopkg_runner.exceptions import AutoPkgRunnerException
from cloud_autopkg_runner.metadata_cache import create_dummy_files, load_metadata_cache
from cloud_autopkg_runner.recipe import ConsolidatedReport, Recipe


def generate_recipe_list(args: Namespace) -> set[str]:
    """Combine the various inputs to generate a comprehensive list of recipes to run.

    Aggregates recipe names from a JSON file, command-line arguments, and the 'RECIPE'
    environment variable. Ensures the final list contains only unique recipe names.

    Args:
        args: A Namespace object containing parsed command-line arguments, including:
            - recipe_list (Path): Path to a JSON file containing a list of recipe names.
            - recipe (list[str]): List of recipe names passed directly as arguments.

    Returns:
        A set of strings, where each string is a recipe name.

    Raises:
        AutoPkgRunnerException: If the JSON file specified by 'args.recipe_list'
            contains invalid JSON.
    """
    logger.debug("Generating recipe list...")

    output: set[str] = set()

    if args.recipe_list:
        try:
            output.update(json.loads(Path(args.recipe_list).read_text()))
        except json.JSONDecodeError as exc:
            raise AutoPkgRunnerException(
                f"Invalid file contents in {args.recipe_list}"
            ) from exc

    if args.recipe:
        output.update(args.recipe)

    if os.getenv("RECIPE"):
        output.add(os.getenv("RECIPE", ""))

    logger.debug(f"Recipe list generated: {output}")
    return output


def parse_arguments() -> Namespace:
    """Parse command-line arguments using argparse.

    Defines the expected command-line arguments and converts them into a Namespace
    object for easy access. These arguments control the verbosity level,
    specify recipes to run, provide a path to a list of recipes in JSON format,
    and allow customization of the cache file and log file locations.

    Returns:
        A Namespace object containing the parsed command-line arguments.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity level. Can be specified multiple times. (-vvv)",
    )
    parser.add_argument(
        "-r",
        "--recipe",
        action="append",
        help="A recipe name. Can be specified multiple times. (--recipe Firefox.pkg.recipe --recipe GoogleChrome.pkg.recipe)",
    )
    parser.add_argument(
        "--recipe-list",
        help="Path to a list of recipe names in JSON format.",
        type=Path,
    )
    parser.add_argument(
        "--cache-file",
        default="metadata_cache.json",
        help="Path to the file that stores the download metadata cache.",
        type=Path,
    )
    parser.add_argument(
        "--log-file",
        help="Path to the log file. If not specified, no file logging will occur.",
        type=Path,
    )
    return parser.parse_args()


async def process_recipe_list(
    overrides_paths: list[Path], recipe_list: Iterable[str], working_dir: Path
) -> None:
    """Process a list of recipe names to create Recipe objects and run them in parallel.

    Creates `Recipe` objects from a list of recipe names and then executes them
    concurrently using a `ThreadPoolExecutor`.  It searches for each recipe
    in the specified override directories and creates a `Recipe` object
    if the recipe file is found.

    Args:
        overrides_paths: A list of paths to AutoPkg recipe override directories.
                         These directories are searched in order for the recipe files.
        recipe_list: An iterable of recipe names (strings).
        working_dir: The temporary directory where the recipes will be run.

    Raises:
        (Exceptions raised within `run_recipe` are caught and logged as warnings.
        Exceptions during `Recipe` object creation are not explicitly handled.)
    """
    logger.debug("Processing recipes...")

    recipes: list[Recipe] = []
    for recipe_name in recipe_list:
        for overrides_path in overrides_paths:
            recipe_path = Path(overrides_path).expanduser() / recipe_name
            if recipe_path.exists():
                recipes.append(Recipe(recipe_path, working_dir))
                break

    recipe_output: dict[str, ConsolidatedReport] = {}
    for recipe in recipes:
        recipe_output[recipe.name] = await recipe.run()


def signal_handler(sig: int, _frame: Optional[FrameType]) -> NoReturn:
    """Handles signals (e.g., Ctrl+C) for graceful exit.

    This function is registered with the `signal` module to catch signals
    such as `SIGINT` (Ctrl+C) and `SIGTERM` (the `kill` command). When a
    signal is received, this handler logs an error message and then exits
    the application.

    Args:
        sig: The signal number (an integer).
        _frame:  Unused frame object.  Required by signal.signal().
    """
    logger.error(f"Signal {sig} received. Exiting...")
    sys.exit(0)  # Trigger a normal exit


async def async_main() -> None:
    """Asynchronous entry point of the script.

    This function orchestrates the core logic of the script:
    - Parses command-line arguments to configure script behavior.
    - Initializes logging for debugging and monitoring.
    - Generates a list of recipes to be processed.
    - Loads the metadata cache to improve efficiency.
    - Creates dummy files based on the recipe list and metadata,
      to simulate previous downloads for testing or development.
    - Retrieves AutoPkg preferences from the user's system.
    - Processes the recipe list using AutoPkg override directories,
      running each recipe asynchronously.
    """
    args = parse_arguments()

    AppConfig.set_config(
        verbosity_level=args.verbose, log_file=args.log_file, cache_file=args.cache_file
    )
    AppConfig.initialize_logger()

    recipe_list = generate_recipe_list(args)

    metadata_cache = load_metadata_cache(args.cache_file)
    create_dummy_files(recipe_list, metadata_cache)

    autopkg_preferences = AutoPkgPrefs()
    overrides_dir = autopkg_preferences["RECIPE_OVERRIDE_DIRS"]

    with tempfile.TemporaryDirectory(prefix="autopkg_") as temp_dir_str:
        temp_working_dir = Path(temp_dir_str)
        logger.debug(f"Temporary directory created: {temp_working_dir}")

        await process_recipe_list(overrides_dir, recipe_list, temp_working_dir)


def main() -> None:
    """Entry point for the script.

    This function serves as a bridge between the synchronous environment
    expected by `project.scripts` and the asynchronous `async_main` function.
    It uses `asyncio.run()` to execute the asynchronous main function within
    a new event loop. This ensures that the asynchronous code is properly
    executed when the script is invoked from the command line. It also sets
    up signal handlers for graceful exit.
    """
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # `kill` command

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
