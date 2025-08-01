import asyncio
import os
import sys
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import httpx
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

def _flatten_to_str_list(obj):
    """리스트/튜플/딕셔너리 등 중첩 구조를 모두 문자열 리스트로 평탄화"""
    if isinstance(obj, (list, tuple)):
        result = []
        for item in obj:
            result.extend(_flatten_to_str_list(item))
        return result
    elif isinstance(obj, dict):
        return [str(obj)]
    else:
        return [str(obj)]

class MCPClientOllama:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama_url = ollama_url
        self.model = "llama3:8b"

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

    async def call_ollama(self, messages: list, tools: list = None) -> dict:
        """Call Ollama API"""
        # Convert messages to prompt format for Ollama
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\n\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n\n"
        
        prompt += "Assistant: "
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2048
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=30.0,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"Ollama API error: {str(e)}")

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        # Create a system message to guide the AI
        system_message = f"""You are a helpful assistant with access to weather tools. 
Available tools: {[tool.name for tool in self.tools]}

When asked about weather, I will automatically call the appropriate weather tool.
For Los Angeles weather, I will use the get_forecast tool with coordinates: latitude=34.0522, longitude=-118.2437"""

        messages = [
            {
                "role": "system",
                "content": system_message
            },
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

        # Initial Ollama API call
        try:
            response = await self.call_ollama(messages, available_tools)
        except Exception as e:
            return f"Error calling Ollama API: {str(e)}"

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        if "response" in response:
            response_text = response["response"]
            final_text.append(response_text)
            
            # Check if the response contains tool call instructions
            # For now, we'll use a simple approach to detect tool calls
            if "get_forecast" in response_text.lower() or "get_alerts" in response_text.lower():
                # Try to extract coordinates or state from the response
                if "los angeles" in response_text.lower() or "la" in response_text.lower():
                    # Call get_forecast for LA
                    tool_args = {"latitude": 34.0522, "longitude": -118.2437}
                    try:
                        result = await self.session.call_tool("get_forecast", tool_args)
                        tool_results.append({"call": "get_forecast", "result": result})
                        final_text.append(f"[Tool get_forecast executed successfully]")
                        
                        # Handle result content properly using flatten function
                        try:
                            if hasattr(result, 'content'):
                                content = result.content
                                if isinstance(content, str):
                                    final_text.append(content)
                                else:
                                    final_text.extend(_flatten_to_str_list(content))
                            else:
                                final_text.append(str(result))
                        except Exception as e:
                            print(f"Error processing result content: {e}")
                            final_text.append(f"[Result: {str(result)}]")

                        # Continue conversation with tool results
                        messages.append({
                            "role": "assistant",
                            "content": f"I called the get_forecast tool and got the following result: {result.content}"
                        })
                        messages.append({
                            "role": "user", 
                            "content": "Please provide a summary of the weather information."
                        })

                        # Get final response from Ollama
                        final_response = await self.call_ollama(messages)
                        
                        if "response" in final_response:
                            final_text.append(str(final_response["response"]))
                        
                    except Exception as e:
                        error_msg = f"[Error calling tool get_forecast: {str(e)}]"
                        final_text.append(error_msg)
                        print(error_msg)

        # Ensure all items in final_text are strings
        final_text = [str(item) for item in final_text if item is not None]
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
        print("\nMCP Client with Ollama Started!")
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
        print("Usage: python client_ollama.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClientOllama()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main()) 