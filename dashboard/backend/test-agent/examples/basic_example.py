"""Example usage of test-agent."""

import asyncio
from src.config import Settings


async def main():
    """Run example."""
    settings = Settings()
    print(f"Project: test-agent")
    print(f"Use Case: Basic Agent")
    print("Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
