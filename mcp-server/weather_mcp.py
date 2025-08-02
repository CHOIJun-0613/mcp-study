#!/usr/bin/env python3
"""
Weather MCP Server - Cursor에서 사용 가능한 MCP 서버
"""

import asyncio
import json
import sys
from typing import Any, Sequence
import httpx

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# National Weather Service API constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-mcp/1.0"

# Ollama API constants
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"

# Create server instance
server = Server("weather-mcp")

async def make_nws_request(url: str) -> dict | None:
    """Make a request to the National Weather Service API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error making NWS request to {url}: {e}", file=sys.stderr)
            return None

async def call_ollama(messages: list) -> dict:
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
    
    # 프롬프트 길이 제한
    if len(prompt) > 4000:
        prompt = prompt[:4000] + "\n\n[Content truncated due to length]"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024
        }
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            headers = {"Content-Type": "application/json"}
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """List available tools"""
    return ListToolsResult(
        tools=[
            Tool(
                name="get_forecast",
                description="Get weather forecast for a location",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of the location"
                        },
                        "longitude": {
                            "type": "number", 
                            "description": "Longitude of the location"
                        }
                    },
                    "required": ["latitude", "longitude"]
                }
            ),
            Tool(
                name="get_alerts",
                description="Get weather alerts for a US state",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Two-letter US state code (e.g. CA, NY)"
                        }
                    },
                    "required": ["state"]
                }
            ),
            Tool(
                name="process_weather_query",
                description="Process a natural language weather query with AI assistance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language weather query (Korean or English)"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls"""
    
    if name == "get_forecast":
        latitude = arguments["latitude"]
        longitude = arguments["longitude"]
        
        # Get forecast data
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_data = await make_nws_request(points_url)
        
        if points_data:
            forecast_url = points_data["properties"]["forecast"]
            forecast_data = await make_nws_request(forecast_url)
            
            if forecast_data:
                periods = forecast_data["properties"]["periods"]
                forecasts = []
                for period in periods[:5]:  # First 5 periods
                    forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
                    forecasts.append(forecast)
                
                result = "\n---\n".join(forecasts)
            else:
                result = "Unable to fetch forecast data."
        else:
            result = "Unable to fetch location data."
            
        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )
        
    elif name == "get_alerts":
        state = arguments["state"]
        
        # Get alerts data
        url = f"{NWS_API_BASE}/alerts/active/area/{state}"
        data = await make_nws_request(url)
        
        if data and "features" in data:
            if data["features"]:
                alerts = [format_alert(feature) for feature in data["features"]]
                result = "\n---\n".join(alerts)
            else:
                result = f"No active alerts for {state}."
        else:
            result = "Unable to fetch alerts data."
            
        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )
        
    elif name == "process_weather_query":
        query = arguments["query"]
        
        try:
            # 시스템 메시지 생성
            system_message = f"""
You are a helpful assistant with access to weather tools. 
Available tools: ['get_alerts', 'get_forecast']
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

            # 초기 Ollama 호출
            response = await call_ollama(messages)
            
            if "response" not in response:
                return CallToolResult(
                    content=[TextContent(type="text", text="AI 모델 응답을 받을 수 없습니다.")]
                )

            response_text = response["response"]
            
            # 날씨 관련 키워드 감지
            weather_keywords = ["weather", "forecast", "temperature", "날씨", "예보", "기온"]
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in weather_keywords):
                # 위치에 따른 도구 선택
                tool_name = None
                tool_args = {}
                
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
                
                # 날씨 API 호출
                if tool_name == "get_forecast":
                    points_url = f"{NWS_API_BASE}/points/{tool_args['latitude']},{tool_args['longitude']}"
                    points_data = await make_nws_request(points_url)
                    
                    if points_data:
                        forecast_url = points_data["properties"]["forecast"]
                        forecast_data = await make_nws_request(forecast_url)
                        
                        if forecast_data:
                            periods = forecast_data["properties"]["periods"]
                            forecasts = []
                            for period in periods[:5]:
                                forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
                                forecasts.append(forecast)
                            
                            weather_data = "\n---\n".join(forecasts)
                        else:
                            weather_data = "날씨 데이터를 가져올 수 없습니다."
                    else:
                        weather_data = "날씨 데이터를 가져올 수 없습니다."
                        
                elif tool_name == "get_alerts":
                    url = f"{NWS_API_BASE}/alerts/active/area/{tool_args['state']}"
                    data = await make_nws_request(url)
                    
                    if data and "features" in data:
                        if data["features"]:
                            alerts = [format_alert(feature) for feature in data["features"]]
                            weather_data = "\n---\n".join(alerts)
                        else:
                            weather_data = "이 지역에 활성화된 경보가 없습니다."
                    else:
                        weather_data = "경보 데이터를 가져올 수 없습니다."
                
                # 한국어 번역 요청
                translation_system_message = f"""
당신은 도움이 되는 어시스턴트입니다.
다음 날씨 정보를 한국어로 번역하고, 단위를 한국에서 사용하는 단위로 변경해주세요:

1. 화씨(°F) → 섭씨(°C)로 변환
2. 마일(mph) → 킬로미터(km/h)로 변환
3. 모든 텍스트를 자연스러운 한국어로 번역
4. 날씨 상태를 한국어로 표현 (예: sunny → 맑음, cloudy → 흐림)

답변은 반드시 한국어로만 작성해주세요.
"""
                
                translation_messages = [
                    {
                        "role": "system",
                        "content": translation_system_message
                    },
                    {
                        "role": "user", 
                        "content": f"다음 날씨 정보를 한국어로 번역하고 단위를 변환해주세요:\n\n{weather_data}"
                    }
                ]

                # 최종 번역 응답
                try:
                    final_response = await call_ollama(translation_messages)
                    if "response" in final_response:
                        result = final_response["response"]
                    else:
                        result = weather_data
                except Exception as e:
                    result = weather_data
            else:
                # 날씨 관련이 아닌 경우 기본 응답
                result = response_text
                
        except Exception as e:
            result = f"오류가 발생했습니다: {str(e)}"
            
        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server"""
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-mcp",
                server_version="1.0.0",
                capabilities={
                    "tools": {}
                },
            ),
        )

if __name__ == "__main__":
    asyncio.run(main()) 