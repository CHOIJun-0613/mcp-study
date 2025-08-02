#!/usr/bin/env python3
"""
Simple MCP Test Server
"""

import sys
from mcp.server.fastmcp import FastMCP

# Set encoding for proper character handling
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Initialize FastMCP server
mcp = FastMCP("simple-test")

@mcp.tool()
async def hello(name: str = "World") -> str:
    """Say hello to someone.
    
    Args:
        name: Name to greet
    """
    return f"Hello, {name}!"

@mcp.tool()
async def echo(message: str) -> str:
    """Echo a message back.
    
    Args:
        message: Message to echo
    """
    return f"Echo: {message}"

if __name__ == "__main__":
    print("Simple MCP Test Server 시작...", file=sys.stderr)
    mcp.run(transport='stdio') 