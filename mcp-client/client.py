import asyncio
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import groq
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.groq_client = groq.Groq()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        if is_python:
            # For Python scripts, use python directly with the full path
            server_dir = os.path.dirname(os.path.abspath(server_script_path))
            command = sys.executable  # Use the current Python interpreter
            args = [server_script_path]
            env = os.environ.copy()
            # Set encoding to handle special characters
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            # Add the server's virtual environment to PYTHONPATH
            server_venv = os.path.join(server_dir, '.venv', 'Lib', 'site-packages')
            if os.path.exists(server_venv):
                if 'PYTHONPATH' in env:
                    env['PYTHONPATH'] = f"{server_venv};{env['PYTHONPATH']}"
                else:
                    env['PYTHONPATH'] = server_venv
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
        else:
            command = "node"
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=None
            )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools  # Store tools for later use
        print("\nConnected to server with tools:", [tool.name for tool in self.tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Groq and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        available_tools = [{ 
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in self.tools]

        # Initial Groq API call
        response = self.groq_client.chat.completions.create(
            model="llama3-8b-8192",
            #max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for choice in response.choices:
            message = choice.message
            if message.content:
                final_text.append(message.content)
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    
                    # Parse arguments if they are JSON string
                    if isinstance(tool_args, str):
                        import json
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse tool arguments: {tool_args}")
                            continue
                    
                    # Convert parameter types based on tool schema
                    tool_args = self._convert_parameter_types(tool_name, tool_args)
                
                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if message.content:
                    messages.append({
                      "role": "assistant",
                      "content": message.content
                    })
                messages.append({
                    "role": "user", 
                    "content": result.content
                })

                # Get next response from Groq
                response = self.groq_client.chat.completions.create(
                    model="llama3-8b-8192",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.choices[0].message.content)

        return "\n".join(final_text)

    def _convert_parameter_types(self, tool_name: str, tool_args: dict) -> dict:
        """Convert parameter types based on tool schema"""
        # Find tool schema
        tool_schema = None
        for tool in self.tools:
            if tool.name == tool_name:
                tool_schema = tool.inputSchema
                break
        
        if tool_schema and "properties" in tool_schema:
            for param_name, param_value in tool_args.items():
                if param_name in tool_schema["properties"]:
                    param_type = tool_schema["properties"][param_name].get("type")
                    
                    # Convert string to appropriate type
                    if isinstance(param_value, str):
                        if param_type == "number":
                            try:
                                tool_args[param_name] = float(param_value)
                            except ValueError:
                                print(f"Warning: Could not convert {param_name} to float: {param_value}")
                        elif param_type == "integer":
                            try:
                                tool_args[param_name] = int(param_value)
                            except ValueError:
                                print(f"Warning: Could not convert {param_name} to int: {param_value}")
                        elif param_type == "boolean":
                            tool_args[param_name] = param_value.lower() in ("true", "1", "yes", "on")
        
        return tool_args

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
            # Ignore cleanup errors to prevent cascading failures

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())