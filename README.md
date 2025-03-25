# Cloud AutoPkg Runner

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  <!-- Replace LICENSE with your actual license file -->
[![PyPI Version](https://img.shields.io/pypi/v/cloud-autopkg-runner)](https://pypi.org/project/cloud-autopkg-runner/) <!-- Update on PyPI -->
[![Coverage Status](https://img.shields.io/codecov/c/github/<your_github_org>/cloud-autopkg-runner)](https://codecov.io/gh/<your_github_org>/cloud-autopkg-runner) <!-- Update with your Codecov repo -->

## Description

Cloud AutoPkg Runner is a Python library designed to provide asynchronous tools and utilities for managing [AutoPkg](https://github.com/autopkg/autopkg) recipes and workflows. It streamlines AutoPkg automation in cloud environments and CI/CD pipelines, offering enhanced performance and scalability.

This library provides modules for:

* Managing metadata caching
* Processing AutoPkg recipes asynchronously
* Executing shell commands with robust error handling
* Centralized configuration management

## Features

* **Asynchronous Recipe Processing:** Run AutoPkg recipes concurrently for faster execution.
* **Metadata Caching:** Improve efficiency by caching metadata and reducing redundant data fetching.
* **Robust Error Handling:** Comprehensive exception handling and logging for reliable automation.
* **Flexible Configuration:** Easily configure the library using command-line arguments and environment variables.
* **Cloud-Friendly:** Designed for seamless integration with cloud environments and CI/CD systems.

## Installation

### Prerequisites

* Python 3.10 or higher
* [AutoPkg](https://github.com/autopkg/autopkg) installed and configured

### Installing with uv

```bash
uv add cloud-autopkg-runer
```

### Installing from PyPI

```bash
pip install cloud-autopkg-runner
```

## Usage

### Command Line

The cloud-autopkg-runner library provides a command-line interface (CLI) for running AutoPkg recipes. UV is recommended (`uv run autopkg-run`), but you can also call it as a python module (`python -m cloud_autopkg_runner`).

### Running a Recipe

```bash
uv run autopkg-run --recipe Firefox.pkg.recipe
```

### Running Multiple Recipes

```bash
uv run autopkg-run --recipe Firefox.pkg.recipe --recipe GoogleChrome.pkg.recipe
```

### Specifying a Recipe List from a JSON File

Create a JSON file (`recipes.json`) containing a list of recipe names:

```json
[
    "Firefox.pkg.recipe",
    "GoogleChrome.pkg.recipe"
]
```

Then, run the recipes using the `--recipe-list` option:

```bash
uv run autopkg-run --recipe-list recipes.json
```

### Setting the Verbosity Level

Use the `-v` option to control the verbosity level. You can specify it multiple times for increased verbosity (e.g., `-vvv`).

```bash
uv run autopkg-run -vv --recipe Firefox.pkg.recipe
```

### Specifying a Log File

Use the `--log-file` option to specify a log file for the script's output:

```bash
uv run autopkg-run --log-file autopkg_runner.log --recipe Firefox.pkg.recipe
```

### As a Python Library

You can also use `cloud-autopkg-runner` as a Python library in your own scripts.

#### Example: Running recipes programmatically

```python
import asyncio
from cloud_autopkg_runner import AppConfig, generate_recipe_list
from cloud_autopkg_runner.__main__ import (
    parse_arguments,
    load_metadata_cache,
    create_dummy_files,
    process_recipe_list,
)
from pathlib import Path

async def main():
    args = parse_arguments()

    # Configure the library
    AppConfig.set_config(verbosity_level=args.verbose, log_file=args.log_file)
    AppConfig.initialize_logger()

    # Generate the recipe list
    recipe_list = generate_recipe_list(args)

    # Load and create dummy files
    metadata_cache = load_metadata_cache(args.cache_file)
    create_dummy_files(recipe_list, metadata_cache)

    #Get preferences
    autopkg_preferences = AppConfig.autopkg_preferences()
    overrides_dir = autopkg_preferences.get("RECIPE_OVERRIDE_DIRS")

    # Run the recipes
    await process_recipe_list(
        Path(overrides_dir).expanduser(), recipe_list, Path("tmp")
    )  # replace with your working dir


if __name__ == "__main__":
    asyncio.run(main())
```

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgments

[AutoPkg](https://github.com/autopkg/autopkg)
