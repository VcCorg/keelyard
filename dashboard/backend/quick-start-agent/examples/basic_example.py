"""Example usage of quick-start-agent."""

import asyncio
from src.config import Settings


async def main():
    """Run example."""
    settings = Settings()
    print(f"Project: quick-start-agent")
    print(f"Use Case: Multi-Agent System")
    print("Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
