"""Generate example files."""

from pathlib import Path
from agentic_cli.templates.config import TemplateConfig


def generate_example_files(examples_dir: Path, config: TemplateConfig) -> None:
    """Generate example files."""
    content = f'''"""Example usage of {config.name}."""

import asyncio
from src.config import Settings


async def main():
    """Run example."""
    settings = Settings()
    print(f"Project: {config.name}")
    print(f"Use Case: {config.use_case.display_name}")
    print("Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
'''
    (examples_dir / "basic_example.py").write_text(content)
