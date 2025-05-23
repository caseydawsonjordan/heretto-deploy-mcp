"""Main entry point for running the module with python -m heretto_mcp"""
import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())