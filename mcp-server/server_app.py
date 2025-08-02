import sys
import os
from typing import Any, AsyncGenerator
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
import json

# Set encoding for proper character handling
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Initialize FastAPI server
app = FastAPI(title="Weather API Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str

class ForecastRequest(BaseModel):
    latitude: float
    longitude: float

class AlertsRequest(BaseModel):
    state: str

class WeatherResponse(BaseModel):
    success: bool
    data: str
    error: str = None

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
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
    
    # 프롬프트 길이 제한 (Ollama 모델 제한 고려)
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
            headers = {
                "Content-Type": "application/json"
            }
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Weather API Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """Process a query using Ollama and weather tools"""
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # 1. 초기 응답 전송
            yield f"data: {json.dumps({'type': 'status', 'message': '쿼리를 처리하고 있습니다...'})}\n\n"
            
            # 2. 시스템 메시지 생성
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
                    "content": request.query
                }
            ]

            # 3. 초기 Ollama 호출
            yield f"data: {json.dumps({'type': 'status', 'message': 'AI 모델을 호출하고 있습니다...'})}\n\n"
            
            response = await call_ollama(messages)
            
            if "response" not in response:
                yield f"data: {json.dumps({'type': 'error', 'message': 'AI 모델 응답을 받을 수 없습니다.'})}\n\n"
                return

            response_text = response["response"]
            
            # 4. 날씨 관련 키워드 감지
            weather_keywords = ["weather", "forecast", "temperature", "날씨", "예보", "기온"]
            query_lower = request.query.lower()
            
            if any(keyword in query_lower for keyword in weather_keywords):
                yield f"data: {json.dumps({'type': 'status', 'message': '날씨 정보를 가져오고 있습니다...'})}\n\n"
                
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
                
                # 5. 날씨 API 호출
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
                
                # 6. 한국어 번역 요청
                yield f"data: {json.dumps({'type': 'status', 'message': '한국어로 번역하고 있습니다...'})}\n\n"
                
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

                # 7. 최종 번역 응답
                try:
                    final_response = await call_ollama(translation_messages)
                    if "response" in final_response:
                        yield f"data: {json.dumps({'type': 'result', 'content': final_response['response']})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'result', 'content': weather_data})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'result', 'content': weather_data})}\n\n"
            else:
                # 날씨 관련이 아닌 경우 기본 응답
                yield f"data: {json.dumps({'type': 'result', 'content': response_text})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'오류가 발생했습니다: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/get_forecast", response_model=WeatherResponse)
async def get_forecast(request: ForecastRequest):
    """Get weather forecast for a location.

    Args:
        request: ForecastRequest with latitude and longitude
    """
    try:
        # First get the forecast grid endpoint
        points_url = f"{NWS_API_BASE}/points/{request.latitude},{request.longitude}"
        points_data = await make_nws_request(points_url)

        if not points_data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch forecast data for this location."
            )

        # Get the forecast URL from the points response
        forecast_url = points_data["properties"]["forecast"]
        forecast_data = await make_nws_request(forecast_url)

        if not forecast_data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch detailed forecast."
            )

        # Format the periods into a readable forecast
        periods = forecast_data["properties"]["periods"]
        forecasts = []
        for period in periods[:5]:  # Only show next 5 periods
            forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
            forecasts.append(forecast)

        result = "\n---\n".join(forecasts)
        
        return WeatherResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        return WeatherResponse(
            success=False,
            data="",
            error=f"Error processing forecast request: {str(e)}"
        )

@app.post("/api/get_alerts", response_model=WeatherResponse)
async def get_alerts(request: AlertsRequest):
    """Get weather alerts for a US state.

    Args:
        request: AlertsRequest with state code
    """
    try:
        url = f"{NWS_API_BASE}/alerts/active/area/{request.state}"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return WeatherResponse(
                success=False,
                data="",
                error="Unable to fetch alerts or no alerts found."
            )

        if not data["features"]:
            return WeatherResponse(
                success=True,
                data="No active alerts for this state."
            )

        alerts = [format_alert(feature) for feature in data["features"]]
        result = "\n---\n".join(alerts)
        
        return WeatherResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        return WeatherResponse(
            success=False,
            data="",
            error=f"Error processing alerts request: {str(e)}"
        )

@app.get("/api/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "get_forecast",
                "description": "Get weather forecast for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitude of the location"},
                        "longitude": {"type": "number", "description": "Longitude of the location"}
                    },
                    "required": ["latitude", "longitude"]
                }
            },
            {
                "name": "get_alerts",
                "description": "Get weather alerts for a US state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "Two-letter US state code (e.g. CA, NY)"}
                    },
                    "required": ["state"]
                }
            }
        ]
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "server_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 