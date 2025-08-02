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
        
        # 프롬프트 길이 제한 (Ollama 모델 제한 고려)
        if len(prompt) > 4000:
            prompt = prompt[:4000] + "\n\n[Content truncated due to length]"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024  # 토큰 수 제한
            }
        }
        
        # print(f"Debug: Sending request to {self.ollama_url}/api/generate")
        # print(f"Debug: Payload: {payload}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                # 수정: 올바른 Ollama API 엔드포인트 사용
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    headers=headers
                )
                # print(f"Debug: Response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                # print(f"Debug: Response received successfully")
                return result
            except httpx.HTTPStatusError as e:
                print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Ollama API HTTP error: {e.response.status_code}")
            except httpx.RequestError as e:
                print(f"Request Error: {e}")
                print(f"Request Error Type: {type(e)}")
                raise Exception(f"Ollama API request error: {str(e)}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                print(f"Error Type: {type(e)}")
                raise Exception(f"Ollama API error: {str(e)}")

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        # Create a system message to guide the AI
        system_message =f"""
You are a helpful assistant with access to weather tools. 
Available tools: {[tool.name for tool in self.tools]}
When asked about weather, I will automatically call the appropriate weather tool.
답변은 한국어로 해주세요.
"""

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
            # print(f"Debug: Ollama response keys: {list(response.keys())}")  # 디버깅용
        except Exception as e:
            return f"Error calling Ollama API: {str(e)}"

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        # 수정: 응답 처리 로직 개선
        if "response" in response:
            response_text = response["response"]
            # 첫 번째 응답은 제거하고 실제 도구 호출 결과만 사용
            # final_text.append(response_text)
            # print(f"Debug: Response text: {response_text[:100]}...")  # 디버깅용
            
            # 개선된 도구 호출 로직
            should_call_tool = False
            tool_name = None
            tool_args = {}
            
            # 날씨 관련 키워드 감지
            weather_keywords = ["weather", "forecast", "temperature", "날씨", "예보", "기온"]
            location_keywords = ["los angeles", "la", "california", "ca", "뉴욕", "new york", "ny"]
            
            query_lower = query.lower()
            response_lower = response_text.lower()
            
            # 날씨 관련 질문인지 확인
            if any(keyword in query_lower for keyword in weather_keywords):
                should_call_tool = True
                
                # 위치에 따른 도구 선택
                if any(location in query_lower for location in ["los angeles", "la", "캘리포니아", "california"]):
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 34.0522, "longitude": -118.2437}
                elif any(location in query_lower for location in ["new york", "뉴욕", "ny"]):
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 40.7128, "longitude": -74.0060}
                elif any(location in query_lower for location in ["texas", "텍사스", "tx"]):
                    tool_name = "get_alerts"
                    tool_args = {"state": "TX"}
                elif any(location in query_lower for location in ["california", "캘리포니아", "ca"]):
                    tool_name = "get_alerts"
                    tool_args = {"state": "CA"}
                else:
                    # 기본적으로 LA 날씨 제공
                    tool_name = "get_forecast"
                    tool_args = {"latitude": 34.0522, "longitude": -118.2437}
            
            # 도구 호출 실행
            if should_call_tool and tool_name:
                try:
                    # print(f"Debug: Calling tool {tool_name} with args {tool_args}")  # 디버깅용
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({"call": tool_name, "result": result})
                    final_text.append(f"[Tool {tool_name} executed successfully]")
                    
                    # 결과 처리
                    try:
                        if hasattr(result, 'content'):
                            content = result.content
                            # if isinstance(content, str):
                            #     final_text.append(content)
                            # else:
                            #     final_text.extend(_flatten_to_str_list(content))
                        else:
                            final_text.append(str(result))
                    except Exception as e:
                        print(f"Error processing result content: {e}")
                        final_text.append(f"[Result: {str(result)}]")

                    # 도구 결과를 포함한 추가 응답 생성 - 메시지 길이 제한
                    weather_summary = result.content
                    system_message = f"""
당신은 도움이 되는 어시스턴트입니다.
다음 날씨 정보를 한국어로 번역하고, 단위를 한국에서 사용하는 단위로 변경해주세요:

1. 화씨(°F) → 섭씨(°C)로 변환
2. 마일(mph) → 킬로미터(km/h)로 변환
3. 모든 텍스트를 자연스러운 한국어로 번역
4. 날씨 상태를 한국어로 표현 (예: sunny → 맑음, cloudy → 흐림)

답변은 반드시 한국어로만 작성해주세요.
"""
                    
                    follow_up_messages = [
                        {
                            "role": "system",
                            "content": system_message
                        },
                        {
                            "role": "user", 
                            "content": f"다음 날씨 정보를 한국어로 번역하고 단위를 변환해주세요:\n\n{weather_summary}"
                        }
                    ]

                    # 최종 응답 생성 - 타임아웃 증가
                    try:
                        final_response = await self.call_ollama(follow_up_messages)
                        if "response" in final_response:
                            final_text.append(str(final_response["response"]))
                    except Exception as e:
                        # print(f"Debug: Final response error details: {e}")
                        # 에러가 발생해도 기본 요약 제공
                        #final_text.append("날씨 정보를 성공적으로 가져왔습니다. 위의 상세 정보를 확인해주세요.")
                        pass
                        
                except Exception as e:
                    error_msg = f"[Error calling tool {tool_name}: {str(e)}]"
                    final_text.append(error_msg)
                    print(error_msg)
        else:
            # 응답에 "response" 키가 없는 경우
            final_text.append("I received a response from Ollama but couldn't process it properly.")
            final_text.append(f"Response structure: {list(response.keys())}")

        # Ensure all items in final_text are strings and not empty
        final_text = [str(item) for item in final_text if item is not None and str(item).strip()]
        
        if not final_text:
            final_text.append("I couldn't generate a proper response. Please try again.")
            
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
                query = input("\n[Query]: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                if not query:
                    print("Please enter a query.")
                    continue
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.")
    
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